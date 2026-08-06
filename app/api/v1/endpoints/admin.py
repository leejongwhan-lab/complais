"""플랫폼 관리자(Platform Admin) API.

CB 인정서/인정 범위 승인·반려, 플랫폼 동적 계산식(MD/탄소배출량/ESG 지수 등) 수정 등
플랫폼 운영자만 접근 가능한 전역 관리 기능을 다룬다.

CB(인증원) 단위 데이터 격리 대상이 아니므로 `get_current_admin_user`(JWT + platform_admin)
로 접근을 제한한다.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_admin_user
from app.models.admin import (
    CBAccreditation,
    CBAccreditationStatus,
    CBAccreditedScope,
    CBContract,
    CBTier,
    PlatformCalculationRule,
)
from app.models.auditor import Auditor
from app.models.cb import CertificationBodies, CbAccreditationScopes
from app.models.company import Companies
from app.models.certification_body import CbAccreditationScope, CbStandardAccreditation
from app.models.standard import StandardMaster
from app.data.standards_catalog import held_standards_as_initials
from app.schemas.admin import (
    AccreditationActionResponse,
    AccreditationRejectRequest,
    AdminDashboardStats,
    CalculationRuleUpdateResponse,
    CBAccreditationRecordCreate,
    CBAccreditationRecordListResponse,
    CBAccreditationResponse,
    CBAccreditedScopeResponse,
    CBContractCreate,
    CBContractListResponse,
    CBContractResponse,
    PlatformCalculationRuleUpdate,
)
from app.services.cb_billing import ensure_default_cb_contract

router = APIRouter(prefix="/admin", tags=["Platform Admin"])


def _get_accreditation_or_404(db: Session, acc_id: int) -> CBAccreditation:
    accreditation = db.get(CBAccreditation, acc_id)
    if accreditation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"인정서(id={acc_id})를 찾을 수 없습니다.")
    return accreditation


def _get_rule_or_404(db: Session, rule_code: str) -> PlatformCalculationRule:
    rule = db.query(PlatformCalculationRule).filter(PlatformCalculationRule.rule_code == rule_code).first()
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"계산식(rule_code={rule_code})을 찾을 수 없습니다.")
    return rule


def _assert_cb_exists(db: Session, cb_id: int) -> None:
    exists = db.query(CertificationBodies.id).filter(CertificationBodies.id == cb_id).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"인증기관(cb_id={cb_id})을 찾을 수 없습니다.")


def _assert_standard_master_exists(db: Session, standard_master_id: int) -> None:
    exists = db.query(StandardMaster.id).filter(StandardMaster.id == standard_master_id).first()
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ISO 표준 마스터(standard_master_id={standard_master_id})를 찾을 수 없습니다.",
        )


def _scope_count_for_cb(db: Session, cb_id: int) -> int:
    """활성 Scope 수 — cb_scope_matrix 행 수 우선, 없으면 레거시 iaf_codes 토큰 합."""
    matrix_count = (
        db.query(func.count(CbAccreditationScope.id))
        .filter(
            CbAccreditationScope.cb_id == cb_id,
            CbAccreditationScope.is_active.is_(True),
        )
        .scalar()
        or 0
    )
    if matrix_count:
        return int(matrix_count)

    legacy_rows = (
        db.query(CbAccreditationScopes.iaf_codes)
        .filter(
            CbAccreditationScopes.cb_id == cb_id,
            CbAccreditationScopes.is_active.is_(True),
        )
        .all()
    )
    total = 0
    for (iaf_codes,) in legacy_rows:
        tokens = [x for x in (iaf_codes or "").split(",") if x.strip()]
        total += len(tokens) if tokens else 1
    return total


def _held_summary_for_cb(db: Session, cb_id: int) -> tuple[int, list[str], str]:
    """표준별 인정 보유 요약.

    우선순위:
      1) cb_standard_accreditations
      2) cb_scope_matrix DISTINCT standard_code
      3) cb_accreditation_scopes DISTINCT standard_code
    """
    rows = (
        db.query(CbStandardAccreditation.standard_code, CbStandardAccreditation.ab_code)
        .filter(
            CbStandardAccreditation.cb_id == cb_id,
            CbStandardAccreditation.is_active.is_(True),
        )
        .all()
    )
    standards: list[str] = []
    abs_: set[str] = set()
    for std, ab in rows:
        if std and std not in standards:
            standards.append(std)
        if ab:
            abs_.add(ab)
    if standards:
        return len(standards), standards, ", ".join(sorted(abs_))

    matrix_stds = (
        db.query(CbAccreditationScope.standard_code)
        .filter(
            CbAccreditationScope.cb_id == cb_id,
            CbAccreditationScope.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    standards = [s for (s,) in matrix_stds if s]
    if standards:
        return len(standards), standards, ""

    legacy_stds = (
        db.query(CbAccreditationScopes.standard_code)
        .filter(
            CbAccreditationScopes.cb_id == cb_id,
            CbAccreditationScopes.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    standards = [s for (s,) in legacy_stds if s]
    return len(standards), standards, ""


def _batch_scope_and_held(
    db: Session, cb_ids: List[int]
) -> dict[int, tuple[int, int, list[str], str]]:
    """cb_id → (scope_count, held_standard_count, held_standards, ab_summary)."""
    out: dict[int, tuple[int, int, list[str], str]] = {
        cid: (0, 0, [], "") for cid in cb_ids
    }
    if not cb_ids:
        return out

    matrix_rows = (
        db.query(
            CbAccreditationScope.cb_id,
            func.count(CbAccreditationScope.id),
            func.count(func.distinct(CbAccreditationScope.standard_code)),
        )
        .filter(
            CbAccreditationScope.cb_id.in_(cb_ids),
            CbAccreditationScope.is_active.is_(True),
        )
        .group_by(CbAccreditationScope.cb_id)
        .all()
    )
    matrix_scope = {cid: int(cnt) for cid, cnt, _ in matrix_rows}
    matrix_std_cnt = {cid: int(std_cnt) for cid, _, std_cnt in matrix_rows}

    matrix_std_names: dict[int, list[str]] = {cid: [] for cid in cb_ids}
    for cid, std in (
        db.query(CbAccreditationScope.cb_id, CbAccreditationScope.standard_code)
        .filter(
            CbAccreditationScope.cb_id.in_(cb_ids),
            CbAccreditationScope.is_active.is_(True),
        )
        .distinct()
        .all()
    ):
        if std and std not in matrix_std_names[cid]:
            matrix_std_names[cid].append(std)

    held_rows = (
        db.query(
            CbStandardAccreditation.cb_id,
            CbStandardAccreditation.standard_code,
            CbStandardAccreditation.ab_code,
        )
        .filter(
            CbStandardAccreditation.cb_id.in_(cb_ids),
            CbStandardAccreditation.is_active.is_(True),
        )
        .all()
    )
    held_map: dict[int, list[str]] = {cid: [] for cid in cb_ids}
    ab_map: dict[int, set[str]] = {cid: set() for cid in cb_ids}
    for cid, std, ab in held_rows:
        if std and std not in held_map[cid]:
            held_map[cid].append(std)
        if ab:
            ab_map[cid].add(ab)

    # legacy fallback for CBs without matrix
    need_legacy = [cid for cid in cb_ids if matrix_scope.get(cid, 0) == 0]
    legacy_scope: dict[int, int] = {}
    legacy_stds: dict[int, list[str]] = {cid: [] for cid in need_legacy}
    if need_legacy:
        for cid, std, iaf in (
            db.query(
                CbAccreditationScopes.cb_id,
                CbAccreditationScopes.standard_code,
                CbAccreditationScopes.iaf_codes,
            )
            .filter(
                CbAccreditationScopes.cb_id.in_(need_legacy),
                CbAccreditationScopes.is_active.is_(True),
            )
            .all()
        ):
            tokens = [x for x in (iaf or "").split(",") if x.strip()]
            legacy_scope[cid] = legacy_scope.get(cid, 0) + (len(tokens) if tokens else 1)
            if std and std not in legacy_stds[cid]:
                legacy_stds[cid].append(std)

    for cid in cb_ids:
        scope_cnt = matrix_scope.get(cid, 0) or legacy_scope.get(cid, 0)
        held_raw = held_map[cid] or matrix_std_names[cid] or legacy_stds.get(cid, [])
        # 보유 표준: 지정 KAB 이니셜만 (QMS/EMS/…); 한글 junk·장문 표기 제외
        held = held_standards_as_initials(held_raw)
        # 인정기관: AB 코드만 (한글/잡문자 제외) — 표준 이니셜과 섞지 않음
        abs_clean = sorted(
            a for a in ab_map[cid] if a and not any("\uac00" <= ch <= "\ud7a3" or "\u3131" <= ch <= "\u318e" for ch in a)
        )
        ab_sum = ", ".join(abs_clean) if abs_clean else ""
        out[cid] = (scope_cnt, len(held), held, ab_sum)
    return out


# 0. 대시보드 통계
@router.get("/stats", response_model=AdminDashboardStats)
def get_admin_stats(
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> AdminDashboardStats:
    """플랫폼 현황 카드용 집계."""
    return AdminDashboardStats(
        cb_count=db.query(func.count(CertificationBodies.id)).scalar() or 0,
        company_count=db.query(func.count(Companies.id)).scalar() or 0,
        auditor_count=db.query(func.count(Auditor.id)).scalar() or 0,
        pending_accreditation_count=(
            db.query(func.count(CBAccreditation.id))
            .filter(CBAccreditation.status == CBAccreditationStatus.PENDING.value)
            .scalar()
            or 0
        ),
    )


# 1. CB 인정서 및 인정 범위 승인/반려 API
@router.patch("/accreditations/{acc_id}/approve", response_model=AccreditationActionResponse)
def approve_cb_accreditation(
    acc_id: int,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> AccreditationActionResponse:
    """CB 인정서를 승인하고, 하위 인정 범위(scopes)를 모두 승인 처리합니다."""
    accreditation = _get_accreditation_or_404(db, acc_id)

    accreditation.status = CBAccreditationStatus.APPROVED.value
    accreditation.reject_reason = None
    accreditation.approved_at = datetime.utcnow()
    db.query(CBAccreditedScope).filter(CBAccreditedScope.cb_accreditation_id == acc_id).update({"is_approved": True})
    db.commit()
    db.refresh(accreditation)

    return AccreditationActionResponse(message="CB 인정서 및 인정 범위가 승인되었습니다.", accreditation=accreditation)


@router.patch("/accreditations/{acc_id}/reject", response_model=AccreditationActionResponse)
def reject_cb_accreditation(
    acc_id: int,
    payload: AccreditationRejectRequest,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> AccreditationActionResponse:
    """CB 인정서를 반려하고, 하위 인정 범위(scopes)를 모두 미승인 처리합니다."""
    accreditation = _get_accreditation_or_404(db, acc_id)

    accreditation.status = CBAccreditationStatus.REJECTED.value
    accreditation.reject_reason = payload.reject_reason
    db.query(CBAccreditedScope).filter(CBAccreditedScope.cb_accreditation_id == acc_id).update({"is_approved": False})
    db.commit()
    db.refresh(accreditation)

    return AccreditationActionResponse(message="CB 인정서가 반려되었습니다.", accreditation=accreditation)


# 2. CB 연간 계약 및 과금 정책 목록/등록 API
@router.get("/cb-contracts", response_model=List[CBContractListResponse])
def list_cb_contracts(
    skip: int = 0,
    limit: int = 100,
    cb_id: Optional[int] = None,
    contract_year: Optional[int] = None,
    ensure_missing: bool = Query(True, description="계약 없는 CB에 당해 기본 계약 자동 생성"),
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> List[CBContractListResponse]:
    """인증기관 현황 + 연간 과금 계약을 함께 조회합니다.

    - certification_bodies 기준으로 목록을 구성하고
    - 누락된 당해 연도 계약은 기본값으로 자동 생성(ensure_missing=true)합니다.
    """
    year = contract_year or datetime.utcnow().year
    cb_query = db.query(CertificationBodies)
    if cb_id is not None:
        cb_query = cb_query.filter(CertificationBodies.id == cb_id)
    # 마스터 순서: institutionData.idx(=id) 오름차순 — 더미 고ID가 상단에 오지 않도록
    cbs = cb_query.order_by(CertificationBodies.id.asc()).offset(skip).limit(limit).all()

    created = False
    if ensure_missing:
        for cb in cbs:
            before = (
                db.query(CBContract.id)
                .filter(CBContract.cb_id == cb.id, CBContract.contract_year == year)
                .first()
            )
            ensure_default_cb_contract(db, cb, year=year)
            if before is None:
                created = True
        if created:
            db.commit()

    results: List[CBContractListResponse] = []
    metrics = _batch_scope_and_held(db, [cb.id for cb in cbs])
    for cb in cbs:
        contract = (
            db.query(CBContract)
            .filter(CBContract.cb_id == cb.id, CBContract.contract_year == year)
            .order_by(CBContract.id.desc())
            .first()
        )
        if contract is None:
            # ensure_missing=false 인 경우 최신 계약 폴백
            contract = (
                db.query(CBContract)
                .filter(CBContract.cb_id == cb.id)
                .order_by(CBContract.contract_year.desc(), CBContract.id.desc())
                .first()
            )
        if contract is None:
            continue

        scope_cnt, held_cnt, held_stds, ab_sum = metrics.get(cb.id, (0, 0, [], ""))
        results.append(
            CBContractListResponse(
                id=contract.id,
                cb_id=cb.id,
                cb_name=cb.name,
                cb_code=cb.code,
                cb_status=cb.status or ("정상" if cb.is_active else "정지"),
                scope_count=scope_cnt,
                held_standard_count=held_cnt,
                held_standards=held_stds,
                ab_summary=ab_sum,
                accreditation_body=cb.accreditation_body,
                contract_year=contract.contract_year,
                tier=contract.tier or CBTier.MEDIUM.value,
                annual_base_fee=contract.annual_base_fee,
                price_per_md=contract.price_per_md,
                contract_start_date=contract.contract_start_date,
                contract_end_date=contract.contract_end_date,
                is_active=bool(contract.is_active),
                created_at=contract.created_at,
            )
        )
    return results


@router.post("/cb-contracts", response_model=CBContractResponse, status_code=status.HTTP_201_CREATED)
def create_cb_contract(
    payload: CBContractCreate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> CBContract:
    """CB 연간 계약(과금 정책)을 등록합니다."""
    _assert_cb_exists(db, payload.cb_id)

    contract = CBContract(**payload.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


# 3. CB 인정서 + 인정 범위 목록/일괄 등록 API
@router.get("/accreditations", response_model=List[CBAccreditationRecordListResponse])
def list_cb_accreditations(
    skip: int = 0,
    limit: int = 100,
    cb_id: Optional[int] = None,
    # 파라미터 변수명은 fastapi.status 모듈과의 이름 충돌을 피하기 위해 status_filter로 두고,
    # 실제 쿼리 파라미터 키는 alias로 "status"를 그대로 사용한다 (?status=PENDING).
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> List[CBAccreditationRecordListResponse]:
    """CB 인정서 목록을 인증기관명 및 인정 범위(scopes)와 함께 조회합니다."""
    query = db.query(CBAccreditation, CertificationBodies.name).join(
        CertificationBodies, CBAccreditation.cb_id == CertificationBodies.id
    )
    if cb_id is not None:
        query = query.filter(CBAccreditation.cb_id == cb_id)
    if status_filter is not None:
        query = query.filter(CBAccreditation.status == status_filter)
    rows = query.order_by(CBAccreditation.id.desc()).offset(skip).limit(limit).all()

    return [
        CBAccreditationRecordListResponse(
            id=accreditation.id,
            cb_id=accreditation.cb_id,
            cb_name=cb_name,
            accreditation_body=accreditation.accreditation_body,
            certificate_number=accreditation.certificate_number,
            certificate_file_url=accreditation.certificate_file_url,
            status=accreditation.status,
            reject_reason=accreditation.reject_reason,
            approved_at=accreditation.approved_at,
            scopes=[CBAccreditedScopeResponse.model_validate(scope) for scope in accreditation.scopes],
        )
        for accreditation, cb_name in rows
    ]


@router.post("/accreditations", response_model=CBAccreditationResponse, status_code=status.HTTP_201_CREATED)
def create_cb_accreditation(
    payload: CBAccreditationRecordCreate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> CBAccreditation:
    """CB 인정서를 등록하고, 신청한 인정 범위(scopes)를 함께 생성합니다 (초기 상태 PENDING)."""
    _assert_cb_exists(db, payload.cb_id)
    for scope in payload.scopes:
        _assert_standard_master_exists(db, scope.standard_master_id)

    accreditation = CBAccreditation(
        cb_id=payload.cb_id,
        accreditation_body=payload.accreditation_body,
        certificate_number=payload.certificate_number,
        certificate_file_url=payload.certificate_file_url,
        status=CBAccreditationStatus.PENDING.value,
    )
    db.add(accreditation)
    db.flush()  # accreditation.id 확보

    for scope in payload.scopes:
        db.add(
            CBAccreditedScope(
                cb_accreditation_id=accreditation.id,
                iso_standard_id=scope.standard_master_id,
                iaf_code=scope.iaf_code,
            )
        )

    db.commit()
    db.refresh(accreditation)
    return accreditation


# 4. 산출 지침 및 계산식 동적 수정 API
@router.put("/calculation-rules/{rule_code}", response_model=CalculationRuleUpdateResponse)
def update_calculation_rule(
    rule_code: str,
    payload: PlatformCalculationRuleUpdate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(get_current_admin_user),
) -> CalculationRuleUpdateResponse:
    """플랫폼 계산식(수식 표현/변수 테이블)을 동적으로 수정합니다."""
    rule = _get_rule_or_404(db, rule_code)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)

    return CalculationRuleUpdateResponse(message=f"계산식({rule_code})이 수정되었습니다.", rule=rule)
