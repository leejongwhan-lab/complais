"""기업 인증신청 MD 스냅샷 + CB 제안검토 API.

파이프라인:
  ① POST /enterprise-audit-applications          — 기업 신청(MD 산출·저장)
  ② POST /enterprise-audit-applications/yearly   — 연차 인원 갱신 스냅샷
  ③ PATCH /enterprise-audit-applications/{id}/cb-review — CB 가감/입회/상태
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, require_cb_scope, require_platform_admin
from app.models.company import Companies
from app.models.enterprise_audit_application import EnterpriseAuditApplication
from app.models.cb import CertificationBodies
from app.schemas.enterprise_audit_application import (
    CbApplicationReviewUpdate,
    EnterpriseApplicationCreate,
    EnterpriseApplicationOut,
    EnterpriseApplicationYearly,
    MdPreviewRequest,
    MdPreviewResponse,
)
from app.services.md_calculator import (
    CalcInput,
    apply_cb_adjustment_ratio,
    base_md_for_audit_type,
    calculate_base_md,
    map_api_audit_type_to_engine,
    map_engine_atype_to_api,
    normalize_standard_code,
)

router = APIRouter(prefix="/enterprise-audit-applications", tags=["Enterprise Audit Applications (MD)"])

_STATUS_TRANSITIONS = {
    "SUBMITTED": {"REVIEWING", "PROPOSED"},
    "REVIEWING": {"PROPOSED", "SUBMITTED"},
    "PROPOSED": {"CONTRACTED", "REVIEWING"},
    "CONTRACTED": set(),
}


def _to_out(row: EnterpriseAuditApplication) -> EnterpriseApplicationOut:
    return EnterpriseApplicationOut.model_validate(row)


def _build_calc_input(
    *,
    standards: List[str],
    employees: int,
    ksic_code: str,
    audit_type: str,
    mode: str = "single",
    site_total: int = 1,
    site_factor: float = 0.5,
    **extras,
) -> CalcInput:
    return CalcInput(
        standards=[normalize_standard_code(s) for s in standards],
        employees=employees,
        ksic_code=ksic_code or "",
        audit_type=map_api_audit_type_to_engine(audit_type),
        mode=mode,
        site_total=site_total,
        site_factor=site_factor,
        fsms_cat=extras.get("fsms_cat", "CI"),
        haccp=int(extras.get("haccp", 1)),
        en_tj=float(extras.get("en_tj", 50)),
        seu=int(extras.get("seu", 3)),
        it_users=int(extras.get("it_users", 100)),
        md_risk=int(extras.get("md_risk", 1)),
        intg_level=float(extras.get("intg_level", 40)),
        intg_team_z=int(extras.get("intg_team_z", 1)),
        intg_team_sumx=int(extras.get("intg_team_sumx", 0)),
        pii_role=extras.get("pii_role", "controller"),
    )


def _persist_from_calc(
    db: Session,
    *,
    enterprise_id: int,
    cb_id: int,
    audit_type: str,
    standards_display: List[str],
    audit_request_id: Optional[int],
    result,
) -> EnterpriseAuditApplication:
    iaf = result.iaf_main or result.iaf_sub or ""
    if not iaf:
        iaf = "00"
    row = EnterpriseAuditApplication(
        enterprise_id=enterprise_id,
        cb_id=cb_id,
        audit_request_id=audit_request_id,
        audit_type=audit_type.upper(),
        applied_standards=standards_display,
        ksic_code=result.ksic_code or "",
        iaf_scope_code=str(iaf),
        active_employee_count=int(result.employees),
        complexity_level=result.complexity_level,
        base_stage1_md=Decimal(str(result.stage1_md)),
        base_stage2_md=Decimal(str(result.stage2_md)),
        base_surveillance_md=Decimal(str(result.surveillance_md)),
        base_recertification_md=Decimal(str(result.recertification_md)),
        base_md_detail_json=result.detail_log,
        cb_adjustment_ratio=Decimal("0.00"),
        final_audit_md=None,
        is_witness_audit=False,
        witness_type="NONE",
        status="SUBMITTED",
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/preview", response_model=MdPreviewResponse)
def preview_md(payload: MdPreviewRequest, current_user: CurrentUser = Depends(get_current_user)):
    """MD 엔진 미리보기 (저장 없음)."""
    _ = current_user
    inp = _build_calc_input(
        standards=payload.standards,
        employees=payload.employees,
        ksic_code=payload.ksic_code,
        audit_type=payload.audit_type,
        mode=payload.mode,
        site_total=payload.site_total,
        site_factor=payload.site_factor,
        fsms_cat=payload.fsms_cat,
        haccp=payload.haccp,
        en_tj=payload.en_tj,
        seu=payload.seu,
        it_users=payload.it_users,
        md_risk=payload.md_risk,
        intg_level=payload.intg_level,
        intg_team_z=payload.intg_team_z,
        intg_team_sumx=payload.intg_team_sumx,
        pii_role=payload.pii_role,
    )
    try:
        result = calculate_base_md(inp)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"MD 산출 실패: {exc}") from exc
    return MdPreviewResponse(
        complexity_level=result.complexity_level,
        iaf_scope_code=result.iaf_main,
        iaf_sub=result.iaf_sub,
        ksic_code=result.ksic_code,
        employees=result.employees,
        audit_type=map_engine_atype_to_api(result.audit_type),
        standards=result.standards,
        base_stage1_md=result.stage1_md,
        base_stage2_md=result.stage2_md,
        base_surveillance_md=result.surveillance_md,
        base_recertification_md=result.recertification_md,
        final_days=result.final_days,
        detail_log=result.detail_log,
    )


@router.post("", response_model=EnterpriseApplicationOut, status_code=201)
def create_application(
    payload: EnterpriseApplicationCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """① 기업 인증신청 — KSIC→IAF→복잡도→MD 산출 후 스냅샷 저장."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, payload.company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")
    if not db.get(CertificationBodies, payload.cb_id):
        raise HTTPException(status_code=404, detail="인증기관(CB)을 찾을 수 없습니다.")

    employees = payload.employees
    if employees is None:
        employees = int(getattr(company, "employee_count", 0) or getattr(company, "headcount_certified", 0) or 1)
    ksic = (payload.ksic_code or getattr(company, "ksic_code", None) or "").strip()
    if not ksic:
        raise HTTPException(status_code=400, detail="KSIC 코드가 필요합니다 (기업정보 또는 요청 body).")

    inp = _build_calc_input(
        standards=payload.standards,
        employees=employees,
        ksic_code=ksic,
        audit_type=payload.audit_type,
        mode=payload.mode,
        site_total=payload.site_total,
        site_factor=payload.site_factor,
        fsms_cat=payload.fsms_cat,
        haccp=payload.haccp,
        en_tj=payload.en_tj,
        seu=payload.seu,
        it_users=payload.it_users,
        md_risk=payload.md_risk,
        intg_level=payload.intg_level,
        intg_team_z=payload.intg_team_z,
        intg_team_sumx=payload.intg_team_sumx,
    )
    try:
        result = calculate_base_md(inp)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"MD 산출 실패: {exc}") from exc

    row = _persist_from_calc(
        db,
        enterprise_id=cid,
        cb_id=payload.cb_id,
        audit_type=payload.audit_type or map_engine_atype_to_api(result.audit_type),
        standards_display=list(payload.standards),
        audit_request_id=payload.audit_request_id,
        result=result,
    )
    return _to_out(row)


@router.post("/yearly", response_model=EnterpriseApplicationOut, status_code=201)
def create_yearly_snapshot(
    payload: EnterpriseApplicationYearly,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """② 연차/사후/재인증 — 현재 인원으로 MD 재계산 후 새 history 행."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, payload.company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    # defaults from latest application
    latest = (
        db.query(EnterpriseAuditApplication)
        .filter(EnterpriseAuditApplication.enterprise_id == cid)
        .order_by(EnterpriseAuditApplication.application_id.desc())
        .first()
    )
    standards = payload.standards or (latest.applied_standards if latest else None)
    if not standards:
        raise HTTPException(status_code=400, detail="standards 가 필요합니다 (이전 신청이 없을 때).")
    cb_id = payload.cb_id or (latest.cb_id if latest else None)
    if not cb_id:
        raise HTTPException(status_code=400, detail="cb_id 가 필요합니다.")
    ksic = (payload.ksic_code or (latest.ksic_code if latest else None) or getattr(company, "ksic_code", "") or "").strip()

    # update company cache headcount
    company.employee_count = payload.employees
    company.updated_at = datetime.utcnow()

    inp = _build_calc_input(
        standards=list(standards),
        employees=payload.employees,
        ksic_code=ksic,
        audit_type=payload.audit_type,
    )
    try:
        result = calculate_base_md(inp)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"MD 산출 실패: {exc}") from exc

    row = _persist_from_calc(
        db,
        enterprise_id=cid,
        cb_id=int(cb_id),
        audit_type=payload.audit_type,
        standards_display=list(standards),
        audit_request_id=payload.audit_request_id,
        result=result,
    )
    return _to_out(row)


@router.get("", response_model=List[EnterpriseApplicationOut])
def list_applications(
    company_id: Optional[int] = Query(None),
    cb_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업 또는 CB 관점 목록."""
    q = db.query(EnterpriseAuditApplication)
    role = (getattr(current_user, "role", None) or "").lower()

    if role in ("enterprise", "company", "client"):
        require_enterprise_user(current_user)
        cid = resolve_company_id(current_user, company_id)
        q = q.filter(EnterpriseAuditApplication.enterprise_id == cid)
    elif role in ("cb", "cb_admin", "cb_staff", "cb_manager", "cb_reviewer") or "cb" in role:
        # require_cb_scope already used elsewhere; soft-filter by user's cb
        user_cb = getattr(current_user, "cb_id", None) or getattr(current_user, "primary_cb_id", None)
        if cb_id:
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)
        elif user_cb:
            q = q.filter(EnterpriseAuditApplication.cb_id == int(user_cb))
    else:
        # admin / platform
        if company_id:
            q = q.filter(EnterpriseAuditApplication.enterprise_id == company_id)
        if cb_id:
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)

    if status:
        q = q.filter(EnterpriseAuditApplication.status == status.upper())
    rows = q.order_by(EnterpriseAuditApplication.application_id.desc()).limit(100).all()
    return [_to_out(r) for r in rows]


@router.get("/{application_id}", response_model=EnterpriseApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _ = current_user
    row = db.get(EnterpriseAuditApplication, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="신청건을 찾을 수 없습니다.")
    return _to_out(row)


@router.patch("/{application_id}/cb-review", response_model=EnterpriseApplicationOut)
def cb_review_application(
    application_id: int,
    payload: CbApplicationReviewUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """③ CB 제안검토 — 가감비율·입회·상태. final = base × (1 + ratio/100)."""
    row = db.get(EnterpriseAuditApplication, application_id)
    if not row:
        raise HTTPException(status_code=404, detail="신청건을 찾을 수 없습니다.")

    user_cb = getattr(current_user, "cb_id", None)
    role = (getattr(current_user, "role", None) or "").lower()
    if user_cb and int(user_cb) != int(row.cb_id) and "admin" not in role and "platform" not in role:
        raise HTTPException(status_code=403, detail="타 인증원 신청건은 검토할 수 없습니다.")

    base = base_md_for_audit_type(
        row.audit_type,
        float(row.base_stage1_md or 0),
        float(row.base_stage2_md or 0),
        float(row.base_surveillance_md or 0),
        float(row.base_recertification_md or 0),
    )
    row.cb_adjustment_ratio = Decimal(str(round(float(payload.cb_adjustment_ratio or 0), 2)))
    if payload.cb_adjustment_reason is not None:
        row.cb_adjustment_reason = payload.cb_adjustment_reason
    row.final_audit_md = Decimal(str(apply_cb_adjustment_ratio(base, float(row.cb_adjustment_ratio))))

    if payload.is_witness_audit is not None:
        row.is_witness_audit = bool(payload.is_witness_audit)
    if payload.witness_type is not None:
        wt = payload.witness_type.upper()
        if wt not in ("NONE", "KAB_WITNESS", "INTERNAL_WITNESS"):
            raise HTTPException(status_code=400, detail="invalid witness_type")
        row.witness_type = wt
        if wt != "NONE":
            row.is_witness_audit = True
    if payload.witness_auditor_name is not None:
        row.witness_auditor_name = payload.witness_auditor_name

    if payload.status is not None:
        new_status = payload.status.upper()
        if new_status not in ("SUBMITTED", "REVIEWING", "PROPOSED", "CONTRACTED"):
            raise HTTPException(status_code=400, detail="invalid status")
        allowed = _STATUS_TRANSITIONS.get(row.status, set())
        if new_status != row.status and new_status not in allowed and "admin" not in role:
            raise HTTPException(
                status_code=400,
                detail=f"상태 전이 불가: {row.status} → {new_status}",
            )
        row.status = new_status

    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _to_out(row)
