"""기업(Client) 인증 심사 신청 / 설문 이력 API."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.cb import CertificationBodies
from app.models.client import AuditRequest
from app.models.company import Companies
from app.models.enums import UsersRole
from app.schemas.audit_request import AuditRequestCreate, AuditRequestOut, LatestSurveyOut

router = APIRouter(prefix="/client", tags=["Client Audit Requests"])

_CLIENT_ROLES = {
    UsersRole.CLIENT_ADMIN.value,
    UsersRole.CLIENT_STAFF.value,
    "client_admin",
    "client_staff",
}


def _require_client(current_user: CurrentUser) -> CurrentUser:
    if current_user.role in _CLIENT_ROLES or current_user.role == UsersRole.PLATFORM_ADMIN.value:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="기업 계정만 인증 신청을 할 수 있습니다.",
    )


def _resolve_company_id(current_user: CurrentUser, company_id: Optional[int] = None) -> int:
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        if not company_id:
            raise HTTPException(status_code=400, detail="platform_admin은 company_id가 필요합니다.")
        return company_id
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 기업(company_id) 정보가 없습니다.",
        )
    if company_id and company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="다른 기업 데이터에는 접근할 수 없습니다.")
    return current_user.company_id


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def _as_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _to_out(row: AuditRequest) -> AuditRequestOut:
    return AuditRequestOut(
        id=row.id,
        company_id=row.company_id,
        cb_id=row.cb_id,
        applicant_user_id=row.applicant_user_id,
        iso_standards=_as_list(row.iso_standards),
        audit_type=row.audit_type,
        audit_cycle_months=int(row.audit_cycle_months or 12),
        survey_responses=_as_dict(row.survey_responses) if row.survey_responses is not None else None,
        previous_request_id=row.previous_request_id,
        status=row.status,
        application_no=getattr(row, "application_no", None),
        preferred_start_date=getattr(row, "preferred_start_date", None),
        process_step=int(getattr(row, "process_step", None) or 1),
        note=row.note,
        submitted_at=row.submitted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/audit-requests/latest-survey", response_model=LatestSurveyOut)
def get_latest_survey(
    company_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업의 가장 최근 신청/완료 설문 및 심사주기 — 신규 신청 Prefill용."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)

    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    latest = (
        db.query(AuditRequest)
        .filter(
            AuditRequest.company_id == cid,
            AuditRequest.survey_responses.isnot(None),
            AuditRequest.status.in_(["submitted", "under_review", "completed", "approved"]),
        )
        .order_by(AuditRequest.id.desc())
        .first()
    )

    # 신청 이력이 없으면 기업 스냅샷/기본 주기 반환
    if not latest:
        snapshot = _as_dict(company.latest_survey_snapshot)
        cycle = int(getattr(company, "audit_cycle_months", None) or 12)
        if cycle not in (6, 12):
            cycle = 12
        return LatestSurveyOut(
            has_previous=bool(snapshot),
            request_id=None,
            audit_cycle_months=cycle,
            survey_responses=snapshot,
            message=None
            if snapshot
            else "이전 차수 설문 데이터가 없습니다. 새로 입력해 주세요.",
        )

    return LatestSurveyOut(
        has_previous=True,
        request_id=latest.id,
        previous_request_id=latest.previous_request_id,
        audit_cycle_months=int(latest.audit_cycle_months or getattr(company, "audit_cycle_months", 12) or 12),
        audit_type=latest.audit_type,
        iso_standards=_as_list(latest.iso_standards),
        survey_responses=_as_dict(latest.survey_responses),
        cb_id=latest.cb_id,
        submitted_at=latest.submitted_at,
        message="이전 차수 설문 데이터를 불러왔습니다.",
    )


@router.get("/audit-requests", response_model=List[AuditRequestOut])
def list_audit_requests(
    skip: int = 0,
    limit: int = 50,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """자사 인증 신청 이력 목록."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)
    rows = (
        db.query(AuditRequest)
        .filter(AuditRequest.company_id == cid)
        .order_by(AuditRequest.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [_to_out(r) for r in rows]


@router.post("/audit-requests", response_model=AuditRequestOut, status_code=status.HTTP_201_CREATED)
def create_audit_request(
    payload: AuditRequestCreate,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """인증 심사 신청 등록 + 설문 저장 + 기업 스냅샷 갱신."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)

    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == payload.cb_id).first()
    if not cb:
        raise HTTPException(status_code=404, detail="선택한 인증기관을 찾을 수 없습니다.")

    prev_id = payload.previous_request_id
    if prev_id is not None:
        prev = (
            db.query(AuditRequest)
            .filter(AuditRequest.id == prev_id, AuditRequest.company_id == cid)
            .first()
        )
        if not prev:
            raise HTTPException(
                status_code=400,
                detail="previous_request_id가 자사 신청 이력이 아니거나 존재하지 않습니다.",
            )

    now = datetime.utcnow()
    row = AuditRequest(
        company_id=cid,
        cb_id=payload.cb_id,
        applicant_user_id=current_user.id,
        iso_standards=payload.iso_standards,
        audit_type=(payload.audit_type or "surveillance").strip().lower(),
        audit_cycle_months=payload.audit_cycle_months,
        survey_responses=payload.survey_responses or {},
        previous_request_id=prev_id,
        status="submitted",
        preferred_start_date=getattr(payload, "preferred_start_date", None),
        process_step=1,
        note=payload.note,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    row.application_no = f"APP-{now.strftime('%Y%m%d')}-{int(row.id):04d}"

    # 기업 기본 주기 + 최신 설문 스냅샷 동기화
    company.audit_cycle_months = payload.audit_cycle_months
    company.latest_survey_snapshot = payload.survey_responses or {}
    company.updated_at = now

    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("/audit-requests/{request_id}", response_model=AuditRequestOut)
def get_audit_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_client(current_user)
    cid = _resolve_company_id(current_user, None)
    row = (
        db.query(AuditRequest)
        .filter(AuditRequest.id == request_id, AuditRequest.company_id == cid)
        .first()
    )
    if not row and current_user.role == UsersRole.PLATFORM_ADMIN.value:
        row = db.get(AuditRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="신청 내역을 찾을 수 없습니다.")
    return _to_out(row)
