"""CB Admin Dashboard — MD 검토 / 신청 승인 / 심사원 배정."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.cb_scope import assert_auditor_in_cb_scope
from app.core.security import CurrentUser, require_cb_scope
from app.db.session import get_db
from app.models.audit_md import AuditMdReview, AuditMdReviewLog
from app.models.auditor import AuditApplication, Auditor, AuditorConductSigns
from app.models.certification_body import CbStandardAccreditation
from app.models.company import Companies, Company
from app.models.contract import AuditAssignment, Contract
from app.models.enterprise_audit_application import Application, EnterpriseAuditApplication
from app.schemas.audit_md import MdReviewResponse, MdReviewUpdateRequest
from app.schemas.cb_admin import (
    ApplicationApproveRequest,
    ApplicationDetailResponse,
    ApplicationResponse,
    AuditorAssignmentRequest,
    AuditorScopeResponse,
    ContractCreate,
    ContractResponse,
)
from app.schemas.company import CompanyCreate, CompanyResponse
from app.services.cb_admin import CBAdminService
from app.services.md_calculator import MDCalculatorService
from app.services.scope_expiry import enforce_scope_not_expired

router = APIRouter(prefix="/cb-admin", tags=["CB Admin Dashboard"])


_STATUS_UI = {
    "SUBMITTED": "submitted",
    "REVIEWING": "reviewed",
    "PROPOSED": "approved",
    "CONTRACTED": "assigned",
}


def _standards_label(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, list):
        return ", ".join(str(x) for x in raw)
    return str(raw)


def _ui_status(eapp: EnterpriseAuditApplication, contract: Optional[Contract]) -> str:
    if contract is not None and str(contract.status or "").upper() in {"SCHEDULED", "SIGNED", "SENT"}:
        return "assigned"
    return _STATUS_UI.get(str(eapp.status or "").upper(), str(eapp.status or "").lower())


@router.get("/applications", response_model=List[ApplicationResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """인증 접수 목록 조회 (CB Admin 대시보드용)."""
    q = db.query(Application, Companies.name).outerjoin(
        Companies, Companies.id == Application.enterprise_id
    )
    if current_user.role != "platform_admin":
        if not current_user.cb_id:
            raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")
        q = q.filter(Application.cb_id == current_user.cb_id)

    rows = (
        q.order_by(Application.application_id.desc())
        .offset(skip)
        .limit(min(limit, 200))
        .all()
    )
    items: List[ApplicationResponse] = []
    for eapp, company_name in rows:
        contract = (
            db.query(Contract)
            .filter(Contract.application_id == eapp.application_id)
            .order_by(Contract.id.desc())
            .first()
        )
        items.append(
            ApplicationResponse.from_enterprise(
                eapp,
                company_name=company_name,
                ui_status=_ui_status(eapp, contract),
            )
        )
    return items


@router.post("/clients", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """신규 고객사 등록 (CB Admin)."""
    payload = client_in.to_companies_create()
    if payload.biz_no:
        existing = db.query(Company).filter(Company.biz_no == payload.biz_no).first()
        if existing:
            raise HTTPException(status_code=400, detail="이미 등록된 사업자등록번호입니다.")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_company = Company(
        name=payload.name,
        biz_no=payload.biz_no,
        ceo_name=payload.ceo_name,
        employee_count=payload.employee_count or 1,
        is_active=True,
        created_at=now,
        updated_at=now,
        audit_cycle_months=12,
        status="정상",
    )
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return CompanyResponse.from_orm_company(db_company)


@router.get("/clients", response_model=List[CompanyResponse])
def list_clients(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """전체 고객사 목록 조회."""
    clients = (
        db.query(Company)
        .order_by(Company.id.desc())
        .offset(skip)
        .limit(min(limit, 200))
        .all()
    )
    return [CompanyResponse.from_orm_company(c) for c in clients]


@router.get("/applications/{app_id}", response_model=ApplicationDetailResponse)
def get_application_detail(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB Admin 전용: 특정 신청서 상세 데이터 조회."""
    app_data = CBAdminService.get_application_detail(
        db,
        app_id=app_id,
        cb_id=current_user.cb_id,
        is_platform_admin=(current_user.role == "platform_admin"),
    )
    if not app_data:
        raise HTTPException(status_code=404, detail="해당 신청서를 찾을 수 없습니다.")
    return app_data


@router.get("/auditors", response_model=List[AuditorScopeResponse])
def get_cb_auditors(
    status: Optional[str] = "approved",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB Admin 전용: 배정 가능한 심사원 목록 및 서약서/자격 정보 조회."""
    if current_user.role != "platform_admin" and not current_user.cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")
    return CBAdminService.list_cb_auditors(
        db,
        cb_id=current_user.cb_id,
        status=status,
    )


@router.get("/contracts", response_model=List[ContractResponse])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """계약 목록 조회 (CB 스코프)."""
    if current_user.role != "platform_admin" and not current_user.cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")
    return CBAdminService.list_contracts(
        db,
        cb_id=current_user.cb_id,
        is_platform_admin=(current_user.role == "platform_admin"),
        skip=skip,
        limit=limit,
    )


@router.post(
    "/applications/{app_id}/contract",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contract_from_application(
    app_id: int,
    contract_in: ContractCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """신청건 기반 계약(안) 작성/생성."""
    if current_user.role != "platform_admin" and not current_user.cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")
    try:
        return CBAdminService.create_contract(
            db,
            payload=contract_in,
            cb_id=current_user.cb_id,
            is_platform_admin=(current_user.role == "platform_admin"),
            app_id=app_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/contracts", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_cb_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """계약 Draft 생성 (body.application_id 기준) — /applications/{id}/contract 별칭."""
    if current_user.role != "platform_admin" and not current_user.cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")
    try:
        return CBAdminService.create_contract(
            db,
            payload=payload,
            cb_id=current_user.cb_id,
            is_platform_admin=(current_user.role == "platform_admin"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


def _get_audit_application_or_404(db: Session, app_id: int) -> AuditApplication:
    application = db.query(AuditApplication).filter(AuditApplication.id == app_id).first()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"심사 신청서(application_id={app_id})를 찾을 수 없습니다.",
        )
    return application


def _get_or_create_md_review(db: Session, app_id: int) -> AuditMdReview:
    review = db.query(AuditMdReview).filter(AuditMdReview.application_id == app_id).first()
    if review is None:
        review = AuditMdReview(application_id=app_id, base_md=0.0)
        db.add(review)
        db.flush()
    return review


def _enterprise_app(db: Session, app_id: int) -> Optional[EnterpriseAuditApplication]:
    return (
        db.query(EnterpriseAuditApplication)
        .filter(EnterpriseAuditApplication.application_id == app_id)
        .first()
    )


def _resolve_base_md(db: Session, app_id: int, review: AuditMdReview) -> tuple[float, bool]:
    """base_md 와 통합심사 여부를 해석한다. Enterprise 스냅샷 우선, 없으면 MD 리뷰 저장값."""
    eapp = _enterprise_app(db, app_id)
    if eapp is not None:
        stage_sum = float(eapp.base_stage1_md or 0) + float(eapp.base_stage2_md or 0)
        base = float(eapp.final_audit_md or stage_sum or 0)
        standards = eapp.applied_standards or []
        is_integrated = isinstance(standards, list) and len(standards) >= 2
        if base > 0:
            return base, is_integrated
    if review.base_md and float(review.base_md) > 0:
        return float(review.base_md), False
    return 0.0, False


def _assert_conduct_signs(db: Session, auditor_ids: Sequence[int]) -> None:
    today = date.today()
    for auditor_id in auditor_ids:
        row = (
            db.query(AuditorConductSigns)
            .filter(
                AuditorConductSigns.auditor_id == auditor_id,
                AuditorConductSigns.is_valid.is_(True),
            )
            .order_by(AuditorConductSigns.signed_at.desc())
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"심사원(auditor_id={auditor_id})의 유효한 비밀유지·공평성 서약서가 없습니다.",
            )
        if row.expires_at is not None and row.expires_at < today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"심사원(auditor_id={auditor_id})의 서약서가 만료되었습니다 (expires_at={row.expires_at}).",
            )


def _assert_auditors_exist(db: Session, auditor_ids: Sequence[int]) -> None:
    for auditor_id in auditor_ids:
        exists = db.query(Auditor.id).filter(Auditor.id == auditor_id).first()
        if exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"심사원(auditor_id={auditor_id})을 찾을 수 없습니다.",
            )


ACTION_STATUS_MAP = {
    "save_md": "MD_SAVED",
    "under_review": "UNDER_REVIEW",
    "approved": "APPROVED",
    "need_fix": "NEED_FIX",
    "rejected": "REJECTED",
}


def _assert_cb_access_for_app(
    db: Session,
    app_id: int,
    current_user: CurrentUser,
) -> tuple[Optional[AuditApplication], Optional[EnterpriseAuditApplication]]:
    """AuditApplication 또는 EnterpriseAuditApplication 중 하나로 접근 허용."""
    application = db.query(AuditApplication).filter(AuditApplication.id == app_id).first()
    eapp = _enterprise_app(db, app_id)
    if application is None and eapp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"신청서(application_id={app_id})를 찾을 수 없습니다.",
        )
    if application is not None:
        assert_auditor_in_cb_scope(db, application.auditor_id, current_user)
    elif eapp is not None and current_user.role != "platform_admin":
        if not current_user.cb_id or int(current_user.cb_id) != int(eapp.cb_id):
            raise HTTPException(status_code=403, detail="해당 CB 신청건에 접근할 수 없습니다.")
    return application, eapp


@router.post("/applications/{app_id}/md-review", response_model=MdReviewResponse)
def review_application_md(
    app_id: int,
    payload: MdReviewUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """
    1. 신청건 정보 조회 (직원수, 통합심사 여부 등)
    2. Base MD 산출 및 IAF MD5 순가감 한도 검증
    3. 0.5 M/D 단위 최종 MD 계산 및 저장

    요청/응답은 기존 `MdReviewUpdateRequest` / `MdReviewResponse` 사용.
    레거시 `plus_pct` / `minus_pct` 는 Field Alias 로 수용.
    """
    if payload.action not in ACTION_STATUS_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바르지 않은 action입니다. 허용값: {list(ACTION_STATUS_MAP.keys())}",
        )

    application, eapp = _assert_cb_access_for_app(db, app_id, current_user)

    # Enterprise 전용 신청: AuditMdReview FK(audit_applications) 없이 스냅샷만 갱신
    if application is None and eapp is not None:
        stage_sum = float(eapp.base_stage1_md or 0) + float(eapp.base_stage2_md or 0)
        base_md = stage_sum if stage_sum > 0 else float(eapp.final_audit_md or 0)
        standards = eapp.applied_standards or []
        is_integrated = isinstance(standards, list) and len(standards) >= 2
        if base_md <= 0:
            raise HTTPException(status_code=400, detail="Base MD가 없습니다.")
        add_md, subtract_md, final_md = MDCalculatorService.calculate_review_md(
            base_md=base_md,
            add_pct=payload.add_pct,
            subtract_pct=payload.subtract_pct,
            is_integrated=is_integrated,
        )
        net_pct = payload.add_pct - payload.subtract_pct
        eapp.cb_adjustment_ratio = Decimal(str(net_pct))
        eapp.cb_adjustment_reason = payload.calculation_note or payload.memo
        eapp.final_audit_md = Decimal(str(final_md))
        if eapp.status == "SUBMITTED":
            eapp.status = "REVIEWING"
        db.commit()
        now = datetime.now(timezone.utc)
        return MdReviewResponse(
            id=0,
            application_id=app_id,
            base_md=base_md,
            add_pct=payload.add_pct,
            subtract_pct=payload.subtract_pct,
            add_md=add_md,
            subtract_md=subtract_md,
            final_md=final_md,
            calculation_note=payload.calculation_note,
            base_md_detail_json=eapp.base_md_detail_json,
            updated_at=now,
            reviewed_at=now if payload.action == "approved" else None,
        )

    review = _get_or_create_md_review(db, app_id)
    base_md, is_integrated = _resolve_base_md(db, app_id, review)
    if base_md <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base MD가 없습니다. 먼저 MD 계산기 기본 산출을 저장해 주세요.",
        )

    add_md, subtract_md, final_md = MDCalculatorService.calculate_review_md(
        base_md=base_md,
        add_pct=payload.add_pct,
        subtract_pct=payload.subtract_pct,
        is_integrated=is_integrated,
    )

    before_status = "MD_SAVED"
    if review.review_logs:
        latest = max(review.review_logs, key=lambda log: log.created_at or datetime.min)
        before_status = latest.after_status or before_status

    now = datetime.now(timezone.utc)
    after_status = ACTION_STATUS_MAP[payload.action]

    review.base_md = base_md
    review.add_pct = payload.add_pct
    review.subtract_pct = payload.subtract_pct
    review.add_md = add_md
    review.subtract_md = subtract_md
    review.final_md = final_md
    if payload.calculation_note is not None:
        review.calculation_note = payload.calculation_note
    if payload.action == "approved":
        review.reviewed_at = now
        review.reviewer_role = "cb_admin"
        review.reviewer_user_id = current_user.id

    if eapp is not None:
        net_pct = payload.add_pct - payload.subtract_pct
        eapp.cb_adjustment_ratio = Decimal(str(net_pct))
        eapp.cb_adjustment_reason = payload.calculation_note
        eapp.final_audit_md = Decimal(str(final_md))
        if eapp.status == "SUBMITTED":
            eapp.status = "REVIEWING"

    db.add(
        AuditMdReviewLog(
            md_review_id=review.id,
            actor_user_id=current_user.id,
            actor_role="cb_admin",
            action=payload.action,
            before_status=before_status,
            after_status=after_status,
            memo=payload.memo or payload.calculation_note,
        )
    )
    db.commit()
    db.refresh(review)
    return review


@router.post("/applications/{app_id}/approve")
def approve_application(
    app_id: int,
    payload: ApplicationApproveRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """
    1. Base/Final MD 확정 여부 검증
    2. CB 인정범위(cb_accreditation_scopes) 미포함 표준 여부 차단 검증
    3. 신청 상태 -> approved 변경 및 계약(contracts) draft 객체 자동 생성
    """
    application, eapp = _assert_cb_access_for_app(db, app_id, current_user)

    review = db.query(AuditMdReview).filter(AuditMdReview.application_id == app_id).first()
    final_md = None
    if review is not None and review.final_md and float(review.final_md) > 0:
        final_md = float(review.final_md)
    elif eapp is not None and eapp.final_audit_md is not None and float(eapp.final_audit_md) > 0:
        final_md = float(eapp.final_audit_md)
    if final_md is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Final MD가 확정되지 않았습니다. /md-review 를 먼저 수행해 주세요.",
        )

    if eapp is not None and not payload.skip_scope_check:
        standards = eapp.applied_standards or []
        if isinstance(standards, str):
            standards = [standards]
        missing: List[str] = []
        for raw in standards:
            code = str(raw).strip()
            if not code:
                continue
            digits = "".join(ch for ch in code if ch.isdigit())
            scoped = (
                db.query(CbStandardAccreditation.id)
                .filter(
                    CbStandardAccreditation.cb_id == eapp.cb_id,
                    CbStandardAccreditation.is_active.is_(True),
                    CbStandardAccreditation.standard_code.in_([code, digits, f"ISO {digits}"]),
                )
                .first()
            )
            if scoped is None:
                missing.append(code)
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CB 인정범위에 포함되지 않은 표준: {', '.join(missing)}",
            )
        # Domain 3: 인정만료 경과 시 제안(승인→PROPOSED) 차단
        enforce_scope_not_expired(db, int(eapp.cb_id), [str(s) for s in standards])

    now = datetime.now(timezone.utc)
    if application is not None:
        application.status = "APPROVED"
        application.reviewed_at = now
        application.review_note = payload.memo
        application.reviewed_by = str(current_user.id)

    contract_id = None
    if application is not None:
        contract = None
        if not payload.force_new_contract:
            contract = (
                db.query(Contract)
                .filter(Contract.application_id == app_id, Contract.status == "DRAFT")
                .order_by(Contract.id.desc())
                .first()
            )
        if contract is None:
            contract = Contract(
                application_id=app_id,
                audit_type=(eapp.audit_type if eapp else "INITIAL"),
                standards=(
                    ",".join(eapp.applied_standards)
                    if eapp and isinstance(eapp.applied_standards, list)
                    else (str(eapp.applied_standards) if eapp else None)
                ),
                total_md=final_md,
                status="DRAFT",
                created_at=now.replace(tzinfo=None),
                updated_at=now.replace(tzinfo=None),
            )
            db.add(contract)
        else:
            contract.total_md = final_md
            contract.updated_at = now.replace(tzinfo=None)
        db.flush()
        contract_id = contract.id

        if review is not None:
            db.add(
                AuditMdReviewLog(
                    md_review_id=review.id,
                    actor_user_id=current_user.id,
                    actor_role="cb_admin",
                    action="approved",
                    before_status="UNDER_REVIEW",
                    after_status="APPROVED",
                    memo=payload.memo,
                )
            )
            review.reviewed_at = now
            review.reviewer_role = "cb_admin"
            review.reviewer_user_id = current_user.id

    if eapp is not None:
        eapp.status = "PROPOSED"
        eapp.final_audit_md = Decimal(str(final_md))

    db.commit()

    return {
        "status": "success",
        "message": (
            "신청서 승인 및 계약(Draft) 생성이 완료되었습니다."
            if contract_id
            else "신청서가 승인되었습니다. (기업 신청 스냅샷 — Draft 계약은 audit_applications 연동 시 생성)"
        ),
        "application_id": app_id,
        "contract_id": contract_id,
        "final_md": final_md,
    }


@router.post("/applications/{app_id}/assign-auditors")
def assign_auditors(
    app_id: int,
    payload: AuditorAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """
    1. 심사팀장/팀원 비밀유지·공평성 서약서(auditor_conduct_signs) 유효성 검증
    2. 심사원별 IAF 코드 / ISO 13485 기술영역 매칭 교차 검증
    3. audit_assignments 저장 및 계약 상태 -> scheduled 변경
    """
    application, eapp = _assert_cb_access_for_app(db, app_id, current_user)
    if application is None:
        raise HTTPException(
            status_code=400,
            detail="심사원 배정은 audit_applications 연동 계약이 필요합니다. 승인(Draft 계약) 후 다시 시도하세요.",
        )

    if payload.audit_end < payload.audit_start:
        raise HTTPException(status_code=400, detail="audit_end 는 audit_start 이후여야 합니다.")
    if payload.surveillance_cycle not in (6, 12):
        raise HTTPException(status_code=400, detail="surveillance_cycle 은 6 또는 12만 허용됩니다.")

    all_ids = [payload.lead_auditor_id, *payload.member_auditor_ids]
    if len(set(all_ids)) != len(all_ids):
        raise HTTPException(status_code=400, detail="동일 심사원을 중복 배정할 수 없습니다.")

    _assert_auditors_exist(db, all_ids)
    _assert_conduct_signs(db, all_ids)

    contract = (
        db.query(Contract)
        .filter(Contract.application_id == app_id)
        .order_by(Contract.id.desc())
        .first()
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="계약(Draft)이 없습니다. /approve 를 먼저 수행해 주세요.",
        )

    # 기존 배정 삭제 후, 래퍼 → 단건 AuditAssignmentCreate 목록으로 재배정
    db.query(AuditAssignment).filter(AuditAssignment.application_id == app_id).delete()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    creates = payload.to_assignment_creates(application_id=app_id, contract_id=contract.id)
    db.add_all(
        [
            AuditAssignment(
                application_id=row.application_id,
                auditor_id=row.auditor_id,
                contract_id=row.contract_id,
                role=row.role,
                status=row.status,
                assigned_at=now,
                note=row.note,
                created_at=now,
            )
            for row in creates
        ]
    )

    contract.audit_period_start = payload.audit_start
    contract.audit_period_end = payload.audit_end
    contract.total_md = float(payload.total_md)
    if payload.scope_kr is not None:
        contract.scope_kr = payload.scope_kr
    contract.audit_type = payload.audit_type.upper()
    contract.status = "SCHEDULED"
    contract.updated_at = now

    if eapp is not None:
        eapp.status = "CONTRACTED"

    db.commit()

    return {
        "status": "success",
        "message": f"배정 완료 (팀장 1명 + 팀원 {len(payload.member_auditor_ids)}명)",
        "application_id": app_id,
        "contract_id": contract.id,
        "lead_auditor_id": payload.lead_auditor_id,
        "member_auditor_ids": payload.member_auditor_ids,
    }
