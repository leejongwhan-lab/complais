"""기업(Client) 인증 심사 신청 / 설문 이력 / 제안서·교차검증 API."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.core.validators import normalize_biz_no
from app.models.auditor import Auditor, AuditorConsultingExperience
from app.models.cb import CertificationBodies
from app.models.client import AuditRequest
from app.models.company import Companies
from app.models.enterprise_audit_application import EnterpriseAuditApplication
from app.models.enums import UsersRole
from app.models.proposal_flow import ProposalFlow
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


# ─── Client-facing proposals (final M/D + totals only) ─────────────

_CLIENT_PROPOSAL_STATUSES = {"APPROVED", "DISPATCHED"}
_REJECT_NOTE_PREFIX = "[REJECTED]"


class ClientProposalOut(BaseModel):
    proposal_id: str
    source: str = Field(description="proposal_flow | enterprise_audit_application")
    standards_label: str
    final_md: float
    supply_price: float
    vat_amount: float
    grand_total: float
    status: str
    dispatched_at: Optional[str] = None
    created_at: Optional[str] = None


class ClientProposalAcceptOut(BaseModel):
    proposal_id: str
    status: str
    message: str


def _standards_from_auditors(raw: Any) -> str:
    if not isinstance(raw, list) or not raw:
        return "ISO 인증"
    labels: List[str] = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        code = (
            item.get("standardCode")
            or item.get("standard_code")
            or item.get("standard")
            or ""
        )
        label = str(code).strip()
        if not label:
            continue
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        labels.append(label)
    return ", ".join(labels) if labels else "ISO 인증"


def _proposal_from_flow(row: ProposalFlow) -> ClientProposalOut:
    return ClientProposalOut(
        proposal_id=str(row.proposal_id),
        source="proposal_flow",
        standards_label=_standards_from_auditors(row.assigned_auditors_json),
        final_md=float(row.final_md or 0),
        supply_price=float(row.total_amount or 0),
        vat_amount=float(row.vat or 0),
        grand_total=float(row.grand_total or 0),
        status=str(row.current_status or ""),
        dispatched_at=row.dispatched_at.isoformat() if row.dispatched_at else None,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


def _proposal_from_eaa(row: EnterpriseAuditApplication) -> ClientProposalOut:
    stds = row.applied_standards if isinstance(row.applied_standards, list) else []
    label = ", ".join(str(s) for s in stds if s) or "ISO 인증"
    final_md = float(row.final_audit_md) if row.final_audit_md is not None else 0.0
    return ClientProposalOut(
        proposal_id=f"EAA-{row.application_id}",
        source="enterprise_audit_application",
        standards_label=label,
        final_md=final_md,
        supply_price=0.0,
        vat_amount=0.0,
        grand_total=0.0,
        status=str(row.status or ""),
        dispatched_at=None,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/proposals", response_model=List[ClientProposalOut])
def list_client_proposals(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업에 발송된 제안서 — 최종 M/D·금액만 (가감 요인 비공개)."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)

    flows = (
        db.query(ProposalFlow)
        .filter(
            ProposalFlow.company_id == cid,
            ProposalFlow.current_status.in_(tuple(_CLIENT_PROPOSAL_STATUSES)),
        )
        .order_by(ProposalFlow.updated_at.desc(), ProposalFlow.created_at.desc())
        .limit(50)
        .all()
    )
    out = [_proposal_from_flow(r) for r in flows]

    # fallback: CB가 PROPOSED로 둔 enterprise MD 신청
    eaa_rows = (
        db.query(EnterpriseAuditApplication)
        .filter(
            EnterpriseAuditApplication.enterprise_id == cid,
            EnterpriseAuditApplication.status == "PROPOSED",
        )
        .order_by(EnterpriseAuditApplication.application_id.desc())
        .limit(50)
        .all()
    )
    seen = {p.proposal_id for p in out}
    for row in eaa_rows:
        pid = f"EAA-{row.application_id}"
        if pid not in seen:
            out.append(_proposal_from_eaa(row))
    return out


@router.get("/proposals/latest", response_model=Optional[ClientProposalOut])
def get_latest_client_proposal(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items = list_client_proposals(company_id=company_id, db=db, current_user=current_user)
    return items[0] if items else None


@router.post("/proposals/{proposal_id}/accept", response_model=ClientProposalAcceptOut)
def accept_client_proposal(
    proposal_id: str,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # DEPRECATED — System 2 EAA 경로. 진짜 경로는 certification_applications +
    # cb_cert_applications.py (enterprise_cert_applications). 삭제 예정(정리 후보). 오늘 작업에서 사용 금지.
    """제안 수락 — EAA는 CONTRACTED, proposal_flow는 수락 메모."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)
    now = datetime.utcnow()

    if proposal_id.upper().startswith("EAA-"):
        try:
            app_id = int(proposal_id.split("-", 1)[1])
        except (IndexError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="잘못된 제안서 ID입니다.") from exc
        row = (
            db.query(EnterpriseAuditApplication)
            .filter(
                EnterpriseAuditApplication.application_id == app_id,
                EnterpriseAuditApplication.enterprise_id == cid,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="제안서를 찾을 수 없습니다.")
        if row.status not in ("PROPOSED", "REVIEWING"):
            raise HTTPException(
                status_code=400,
                detail=f"수락 가능한 상태가 아닙니다: {row.status}",
            )
        row.status = "CONTRACTED"
        row.updated_at = now
        db.commit()
        return ClientProposalAcceptOut(
            proposal_id=proposal_id,
            status="CONTRACTED",
            message="제안이 수락되었습니다. 계약 절차를 진행합니다.",
        )

    flow = (
        db.query(ProposalFlow)
        .filter(ProposalFlow.proposal_id == proposal_id, ProposalFlow.company_id == cid)
        .first()
    )
    if not flow:
        raise HTTPException(status_code=404, detail="제안서를 찾을 수 없습니다.")
    note = (flow.note or "").strip()
    stamp = f"[CLIENT_ACCEPTED {now.isoformat()}]"
    flow.note = f"{note}\n{stamp}".strip() if note else stamp
    flow.updated_at = now
    db.commit()
    return ClientProposalAcceptOut(
        proposal_id=proposal_id,
        status=str(flow.current_status),
        message="제안 수락이 접수되었습니다. 계약 절차를 진행합니다.",
    )


# ─── Client-facing consulting verifications ────────────────────────

class ClientVerificationOut(BaseModel):
    id: int
    auditor_name: str
    consulting_type: str
    period: str
    ea_code: str
    company_name: str
    requested_at: Optional[str] = None
    status: str


class ClientVerificationDecision(BaseModel):
    action: Literal["confirm", "reject"]
    reason: Optional[str] = None


def _verification_status(row: AuditorConsultingExperience) -> str:
    if row.is_verified:
        return "VERIFIED"
    note = (row.note or "").strip()
    if note.startswith(_REJECT_NOTE_PREFIX):
        return "REJECTED"
    return "PENDING"


def _verification_out(row: AuditorConsultingExperience, auditor_name: str) -> ClientVerificationOut:
    start = row.start_date.isoformat() if row.start_date else ""
    end = row.end_date.isoformat() if row.end_date else "진행중"
    period = f"{start} ~ {end}" if start else end
    ea = (row.iaf_code or "").strip()
    ea_label = f"EA {ea}" if ea and not ea.upper().startswith("EA") else (ea or "-")
    return ClientVerificationOut(
        id=int(row.id),
        auditor_name=auditor_name or "심사원",
        consulting_type=(row.consulting_type or "ISO 컨설팅").strip() or "ISO 컨설팅",
        period=period,
        ea_code=ea_label,
        company_name=row.company_name,
        requested_at=row.created_at.isoformat() if row.created_at else None,
        status=_verification_status(row),
    )


def _company_biz_digits(company: Companies) -> Optional[str]:
    return normalize_biz_no(getattr(company, "biz_no", None))


@router.get("/verifications", response_model=List[ClientVerificationOut])
def list_client_verifications(
    status_filter: Optional[str] = Query(None, alias="status", description="PENDING|VERIFIED|REJECTED"),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """자사 대상 자문 교차 검증 요청 목록."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    biz = _company_biz_digits(company)

    filters = [AuditorConsultingExperience.company_id == cid]
    if biz:
        # 하이픈 유무 모두 매칭 시도
        filters.append(AuditorConsultingExperience.biz_no == biz)
        if company.biz_no:
            filters.append(AuditorConsultingExperience.biz_no == company.biz_no)

    rows = (
        db.query(AuditorConsultingExperience)
        .filter(or_(*filters))
        .order_by(AuditorConsultingExperience.id.desc())
        .limit(200)
        .all()
    )
    # 정규화 재확인 (저장 형식 편차)
    matched: List[AuditorConsultingExperience] = []
    for row in rows:
        if row.company_id == cid:
            matched.append(row)
            continue
        if biz and normalize_biz_no(row.biz_no) == biz:
            matched.append(row)

    auditor_ids = {int(r.auditor_id) for r in matched if r.auditor_id}
    name_map: Dict[int, str] = {}
    if auditor_ids:
        for a in db.query(Auditor).filter(Auditor.id.in_(auditor_ids)).all():
            name_map[int(a.id)] = a.name

    out = [
        _verification_out(r, name_map.get(int(r.auditor_id), "심사원"))
        for r in matched
    ]
    if status_filter:
        want = status_filter.strip().upper()
        out = [x for x in out if x.status == want]
    return out


@router.patch("/verifications/{verification_id}", response_model=ClientVerificationOut)
def decide_client_verification(
    verification_id: int,
    payload: ClientVerificationDecision,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """자문 수행 사실 확인(confirm) / 반려(reject)."""
    _require_client(current_user)
    cid = _resolve_company_id(current_user, company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    row = db.get(AuditorConsultingExperience, verification_id)
    if not row:
        raise HTTPException(status_code=404, detail="검증 요청을 찾을 수 없습니다.")

    biz = _company_biz_digits(company)
    owns = row.company_id == cid or (biz and normalize_biz_no(row.biz_no) == biz)
    if not owns:
        raise HTTPException(status_code=403, detail="자사 검증 요청만 처리할 수 있습니다.")

    if payload.action == "confirm":
        row.is_verified = True
        # 기존 반려 메모 제거
        note = (row.note or "").strip()
        if note.startswith(_REJECT_NOTE_PREFIX):
            row.note = None
    else:
        reason = (payload.reason or "").strip()
        if not reason:
            raise HTTPException(status_code=422, detail="반려 사유를 입력해 주세요.")
        row.is_verified = False
        row.note = f"{_REJECT_NOTE_PREFIX} {reason}"

    db.commit()
    db.refresh(row)
    auditor = db.get(Auditor, row.auditor_id)
    return _verification_out(row, auditor.name if auditor else "심사원")
