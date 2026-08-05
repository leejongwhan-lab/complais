"""플랫폼 관리자(Platform Admin) API.

CB 인정서/인정 범위 승인·반려, 플랫폼 동적 계산식(MD/탄소배출량/ESG 지수 등) 수정 등
플랫폼 운영자만 접근 가능한 전역 관리 기능을 다룬다.

CB(인증원) 단위 데이터 격리 대상이 아니므로 `require_cb_scope` 대신 `require_platform_admin`으로
role == "platform_admin" 사용자만 접근을 허용한다.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, require_platform_admin
from app.models.admin import (
    CBAccreditation,
    CBAccreditationStatus,
    CBAccreditedScope,
    CBContract,
    PlatformCalculationRule,
)
from app.models.cb import CertificationBodies
from app.models.standard import StandardMaster
from app.schemas.admin import (
    AccreditationActionResponse,
    AccreditationRejectRequest,
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


# 1. CB 인정서 및 인정 범위 승인/반려 API
@router.patch("/accreditations/{acc_id}/approve", response_model=AccreditationActionResponse)
def approve_cb_accreditation(
    acc_id: int,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_platform_admin),
) -> AccreditationActionResponse:
    """CB 인정서를 승인하고, 하위 인정 범위(scopes)를 모두 승인 처리합니다."""
    accreditation = _get_accreditation_or_404(db, acc_id)

    accreditation.status = CBAccreditationStatus.APPROVED.value
    accreditation.reject_reason = None
    db.query(CBAccreditedScope).filter(CBAccreditedScope.cb_accreditation_id == acc_id).update({"is_approved": True})
    db.commit()
    db.refresh(accreditation)

    return AccreditationActionResponse(message="CB 인정서 및 인정 범위가 승인되었습니다.", accreditation=accreditation)


@router.patch("/accreditations/{acc_id}/reject", response_model=AccreditationActionResponse)
def reject_cb_accreditation(
    acc_id: int,
    payload: AccreditationRejectRequest,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_platform_admin),
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
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_platform_admin),
) -> List[CBContractListResponse]:
    """CB 연간 계약 목록을 인증기관명과 함께 조회합니다."""
    query = db.query(CBContract, CertificationBodies.name).join(
        CertificationBodies, CBContract.cb_id == CertificationBodies.id
    )
    if cb_id is not None:
        query = query.filter(CBContract.cb_id == cb_id)
    if contract_year is not None:
        query = query.filter(CBContract.contract_year == contract_year)
    rows = query.order_by(CBContract.id.desc()).offset(skip).limit(limit).all()

    return [
        CBContractListResponse(**CBContractResponse.model_validate(contract).model_dump(), cb_name=cb_name)
        for contract, cb_name in rows
    ]


@router.post("/cb-contracts", response_model=CBContractResponse, status_code=status.HTTP_201_CREATED)
def create_cb_contract(
    payload: CBContractCreate,
    db: Session = Depends(get_db),
    admin: CurrentUser = Depends(require_platform_admin),
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
    admin: CurrentUser = Depends(require_platform_admin),
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
    admin: CurrentUser = Depends(require_platform_admin),
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
    admin: CurrentUser = Depends(require_platform_admin),
) -> CalculationRuleUpdateResponse:
    """플랫폼 계산식(수식 표현/변수 테이블)을 동적으로 수정합니다."""
    rule = _get_rule_or_404(db, rule_code)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)

    return CalculationRuleUpdateResponse(message=f"계산식({rule_code})이 수정되었습니다.", rule=rule)
