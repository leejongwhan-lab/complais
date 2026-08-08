"""심사원 포털 — 대시보드/일정/보고서/NCR/자격 요약 API."""
from __future__ import annotations

import json
import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import inspect, or_, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.data.standards_catalog import format_standard_label, to_family_initial
from app.models.audit import AuditAssignments, AuditNcrs, AuditNotes, AuditReports
from app.models.auditor import (
    Auditor,
    AuditorCbMemberships,
    AuditorEducation,
    AuditorExternalCert,
    AuditorQualification,
    AuditorWorkExperience,
)
from app.models.backoffice import CompanyStaff
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.enums import (
    AuditorCbMembershipsStatus,
    AuditNcrsStatus,
    AuditNotesStatus,
    AuditReportsStatus,
    UsersRole,
)
from app.schemas.auditor_portal import (
    AuditorCareerItem,
    AuditorDashboardSummary,
    AuditorEducationItem,
    AuditorExternalCertItem,
    AuditorKpiBlock,
    AuditorMembershipItem,
    AuditorNcrItem,
    AuditorProfileSummary,
    AuditorQualItem,
    AuditorReportItem,
    AuditorScheduleItem,
)
from app.services.auditor_grade import to_ui_grade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["Auditor Portal"])

_ACTIVE_ASSIGNMENT = {
    "assigned",
    "confirmed",
    "accepted",
    "in_progress",
    "scheduled",
    "배정",
    "확정",
    "진행중",
}
_DRAFT_REPORT = {
    AuditReportsStatus.DRAFT.value,
    "draft",
    "in_progress",
    "작성중",
}
_DRAFT_NOTE = {
    AuditNotesStatus.DRAFT.value,
    AuditNotesStatus.IN_PROGRESS.value,
    "draft",
    "in_progress",
}
_NCR_PENDING = {
    AuditNcrsStatus.CA_SUBMITTED.value,
    "ca_submitted",
    "submitted",
    "under_review",
}


def _require_auditor(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.AUDITOR.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="심사원 포털은 심사원 계정만 이용할 수 있습니다.",
        )
    return current_user


def _get_auditor_for_user(db: Session, user_id: int) -> Auditor:
    auditor = db.query(Auditor).filter(Auditor.user_id == user_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 프로필이 없습니다. 심사원 가입을 먼저 완료하세요.",
        )
    return auditor


def _table_exists(db: Session, name: str) -> bool:
    try:
        return inspect(db.bind).has_table(name)
    except Exception:
        try:
            db.execute(text(f"SELECT 1 FROM `{name}` LIMIT 1"))
            return True
        except Exception:
            return False


def _safe(label: str, fn, default, warnings: List[str]):
    try:
        return fn()
    except Exception as exc:
        logger.warning("auditor portal %s failed: %s", label, exc)
        warnings.append(f"{label}: {exc.__class__.__name__}")
        return default


def _dday(expiry: Optional[date], today: Optional[date] = None) -> Optional[int]:
    if not expiry:
        return None
    base = today or date.today()
    return (expiry - base).days


def _audit_type_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower().replace(" ", "").replace("_", "")
    mapping = {
        "initial": "최초심사",
        "최초": "최초심사",
        "최초심사": "최초심사",
        "surveillance": "사후심사",
        "surveillance1": "사후1차",
        "surveillance2": "사후2차",
        "sa1": "사후1차",
        "sa2": "사후2차",
        "사후": "사후심사",
        "사후1": "사후1차",
        "사후1차": "사후1차",
        "사후2": "사후2차",
        "사후2차": "사후2차",
        "recertification": "갱신심사",
        "renewal": "갱신심사",
        "갱신": "갱신심사",
        "갱신심사": "갱신심사",
        "special": "특별심사",
        "transfer": "전환심사",
        "전환": "전환심사",
        "stage1": "1단계",
        "stage2": "2단계",
    }
    return mapping.get(key, str(raw))


def _audit_mode_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower()
    mapping = {
        "single": "단일",
        "integrated": "통합",
        "on_site": "현장",
        "onsite": "현장",
        "remote": "원격",
        "hybrid": "혼합",
        "단일": "단일",
        "통합": "통합",
    }
    return mapping.get(key, str(raw))


def _parse_id_list(raw: Any) -> List[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        out: List[int] = []
        for item in raw:
            try:
                out.append(int(item))
            except (TypeError, ValueError):
                continue
        return out
    text_val = str(raw).strip()
    if not text_val:
        return []
    if text_val.startswith("["):
        try:
            parsed = json.loads(text_val)
            if isinstance(parsed, list):
                return _parse_id_list(parsed)
        except Exception:
            pass
    ids: List[int] = []
    for part in text_val.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


def _company_address(company: Optional[Companies]) -> Optional[str]:
    if not company:
        return None
    parts = [p for p in [company.address, company.detail_address] if p]
    return " ".join(parts) if parts else None


def _auditor_name_map(db: Session, auditor_ids: Iterable[int]) -> Dict[int, str]:
    ids = sorted({int(i) for i in auditor_ids if i})
    if not ids or not _table_exists(db, "auditors"):
        return {}
    rows = db.query(Auditor.id, Auditor.name).filter(Auditor.id.in_(ids)).all()
    return {int(r.id): (r.name or f"#{r.id}") for r in rows}


def _team_for_contract(
    db: Session,
    contract: Contracts,
    *,
    name_cache: Optional[Dict[int, str]] = None,
) -> Tuple[List[str], str]:
    ids: List[int] = []
    if getattr(contract, "lead_auditor_id", None):
        ids.append(int(contract.lead_auditor_id))
    ids.extend(_parse_id_list(getattr(contract, "member_auditor_ids", None)))
    # Deduplicate preserving order
    seen: Set[int] = set()
    ordered: List[int] = []
    for i in ids:
        if i in seen:
            continue
        seen.add(i)
        ordered.append(i)
    cache = name_cache if name_cache is not None else _auditor_name_map(db, ordered)
    names: List[str] = []
    for i, aid in enumerate(ordered):
        nm = cache.get(aid) or f"#{aid}"
        if i == 0 and getattr(contract, "lead_auditor_id", None) == aid:
            names.append(f"{nm}(팀장)")
        else:
            names.append(nm)
    return names, ", ".join(names)


def _company_contact(
    db: Session, company: Optional[Companies]
) -> Tuple[Optional[str], Optional[str]]:
    if not company:
        return None, None
    if _table_exists(db, "company_staff_members"):
        try:
            staff = (
                db.query(CompanyStaff)
                .filter(CompanyStaff.company_id == company.id)
                .order_by(CompanyStaff.id.asc())
                .limit(20)
                .all()
            )
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            staff = []
        preferred = None
        for s in staff:
            role = (s.role or "").lower()
            if any(k in role for k in ("인증", "품질", "담당", "cert", "quality", "contact")):
                preferred = s
                break
        pick = preferred or (staff[0] if staff else None)
        if pick:
            phone = pick.mobile or pick.phone or company.tel
            return pick.staff_name, phone
    # Fallback: tax contact / company tel
    name = company.tax_contact_name or company.ceo_name
    phone = company.tel
    return name, phone


def _assignment_status_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower()
    mapping = {
        "assigned": "배정",
        "confirmed": "확정",
        "accepted": "수락",
        "in_progress": "진행중",
        "scheduled": "예정",
        "completed": "완료",
        "cancelled": "취소",
        "rejected": "거절",
    }
    return mapping.get(key, str(raw))


def _ncr_status_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower()
    mapping = {
        "draft": "작성중",
        "issued": "발행",
        "ca_submitted": "시정조치 제출",
        "ca_approved": "시정조치 승인",
        "ca_rejected": "시정조치 반려",
        "closed": "종결",
        "under_review": "검토중",
    }
    return mapping.get(key, str(raw))


def _membership_status_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    key = str(raw).strip().lower()
    mapping = {
        "requested": "신청",
        "under_review": "검토중",
        "approved": "승인",
        "rejected": "거절",
        "terminated": "종료",
        "suspended": "정지",
        "expired": "만료",
    }
    return mapping.get(key, str(raw))


def _standard_auditor_label(raw: Optional[str]) -> str:
    """Auditor UI: prefer QMS/EMS initials, fall back to ISO label."""
    initial = to_family_initial(raw)
    if initial:
        return initial
    return format_standard_label(raw, mode="auditor") or str(raw or "")


def _parse_standards(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text_val = str(raw).strip()
    if not text_val:
        return []
    if text_val.startswith("["):
        try:
            parsed = json.loads(text_val)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    for sep in ("|", ";", ","):
        if sep in text_val:
            return [p.strip() for p in text_val.split(sep) if p.strip()]
    return [text_val]


def _month_bounds(today: Optional[date] = None) -> Tuple[date, date]:
    base = today or date.today()
    start = date(base.year, base.month, 1)
    end = date(base.year, base.month, monthrange(base.year, base.month)[1])
    return start, end


def _overlaps_month(
    start: Optional[date],
    end: Optional[date],
    month_start: date,
    month_end: date,
) -> bool:
    if start and end:
        return start <= month_end and end >= month_start
    if start:
        return month_start <= start <= month_end
    if end:
        return month_start <= end <= month_end
    return False


def _contract_ids_for_auditor(db: Session, auditor: Auditor, user_id: int) -> Set[int]:
    ids: Set[int] = set()
    if _table_exists(db, "audit_assignments"):
        rows = (
            db.query(AuditAssignments.contract_id)
            .filter(
                AuditAssignments.contract_id.isnot(None),
                or_(
                    AuditAssignments.auditor_id == auditor.id,
                    AuditAssignments.auditor_user_id == user_id,
                ),
            )
            .all()
        )
        ids.update(int(r[0]) for r in rows if r[0])
    if _table_exists(db, "contracts"):
        lead_rows = (
            db.query(Contracts.id)
            .filter(Contracts.lead_auditor_id == auditor.id)
            .all()
        )
        ids.update(int(r[0]) for r in lead_rows if r[0])
        # member_auditor_ids may be CSV/JSON of auditor ids
        member_rows = (
            db.query(Contracts.id, Contracts.member_auditor_ids)
            .filter(Contracts.member_auditor_ids.isnot(None))
            .all()
        )
        for cid, members in member_rows:
            tokens = _parse_standards(members)
            if str(auditor.id) in tokens or str(user_id) in tokens:
                ids.add(int(cid))
    return ids


def _company_name_map(db: Session, company_ids: Iterable[int]) -> dict:
    ids = [int(i) for i in company_ids if i]
    if not ids or not _table_exists(db, "companies"):
        return {}
    rows = db.query(Companies.id, Companies.name).filter(Companies.id.in_(ids)).all()
    return {int(r.id): r.name for r in rows}


def _schedule_item_from_contract(
    db: Session,
    contract: Contracts,
    company: Optional[Companies],
    *,
    assignment_id: Optional[int] = None,
    status: Optional[str] = None,
    status_label: Optional[str] = None,
    role: Optional[str] = None,
    name_cache: Optional[Dict[int, str]] = None,
) -> AuditorScheduleItem:
    standards = _parse_standards(contract.standards or contract.applied_standards)
    labels = [_standard_auditor_label(s) for s in standards]
    team, team_label = _team_for_contract(db, contract, name_cache=name_cache)
    contact_name, contact_phone = _company_contact(db, company)
    mode = getattr(contract, "audit_mode", None)
    return AuditorScheduleItem(
        assignment_id=assignment_id,
        contract_id=contract.id,
        company_id=contract.company_id,
        company_name=company.name if company else None,
        standards=standards,
        standards_label=", ".join(labels) if labels else "",
        audit_type=contract.audit_type,
        audit_type_label=_audit_type_label(contract.audit_type),
        audit_mode=mode,
        audit_mode_label=_audit_mode_label(mode),
        audit_date=contract.audit_period_start,
        audit_period_end=contract.audit_period_end,
        status=status,
        status_label=status_label,
        role=role,
        team_members=team,
        team_label=team_label,
        company_address=_company_address(company),
        contact_name=contact_name,
        contact_phone=contact_phone,
    )


def _build_schedules(
    db: Session,
    auditor: Auditor,
    user_id: int,
    *,
    month_only: bool = False,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 50,
) -> List[AuditorScheduleItem]:
    if not _table_exists(db, "contracts"):
        return []

    if year and month:
        month_start = date(year, month, 1)
        month_end = date(year, month, monthrange(year, month)[1])
        filter_month = True
    elif month_only:
        month_start, month_end = _month_bounds()
        filter_month = True
    else:
        month_start = month_end = date.today()
        filter_month = False

    items: List[AuditorScheduleItem] = []
    seen_contracts: Set[int] = set()
    team_id_candidates: Set[int] = set()

    raw_rows: List[Tuple[Optional[AuditAssignments], Contracts, Optional[Companies]]] = []

    if _table_exists(db, "audit_assignments"):
        q = (
            db.query(AuditAssignments, Contracts, Companies)
            .outerjoin(Contracts, Contracts.id == AuditAssignments.contract_id)
            .outerjoin(Companies, Companies.id == Contracts.company_id)
            .filter(
                or_(
                    AuditAssignments.auditor_id == auditor.id,
                    AuditAssignments.auditor_user_id == user_id,
                )
            )
            .order_by(AuditAssignments.id.desc())
            .limit(300)
        )
        for aa, contract, company in q.all():
            if not contract:
                continue
            if str(aa.status or "").lower() in {"cancelled", "canceled", "rejected"}:
                continue
            start = contract.audit_period_start
            end = contract.audit_period_end
            if filter_month and not _overlaps_month(start, end, month_start, month_end):
                continue
            raw_rows.append((aa, contract, company))
            seen_contracts.add(int(contract.id))
            if contract.lead_auditor_id:
                team_id_candidates.add(int(contract.lead_auditor_id))
            team_id_candidates.update(_parse_id_list(contract.member_auditor_ids))

    # Fallback: lead auditor contracts without assignment rows
    lead_q = (
        db.query(Contracts, Companies)
        .outerjoin(Companies, Companies.id == Contracts.company_id)
        .filter(Contracts.lead_auditor_id == auditor.id)
        .order_by(Contracts.audit_period_start.desc())
        .limit(200)
    )
    for contract, company in lead_q.all():
        if int(contract.id) in seen_contracts:
            continue
        if str(contract.status or "").lower() in {"cancelled", "canceled"}:
            continue
        start = contract.audit_period_start
        end = contract.audit_period_end
        if filter_month and not _overlaps_month(start, end, month_start, month_end):
            continue
        raw_rows.append((None, contract, company))
        seen_contracts.add(int(contract.id))
        if contract.lead_auditor_id:
            team_id_candidates.add(int(contract.lead_auditor_id))
        team_id_candidates.update(_parse_id_list(contract.member_auditor_ids))

    name_cache = _auditor_name_map(db, team_id_candidates)

    for aa, contract, company in raw_rows:
        if aa is not None:
            items.append(
                _schedule_item_from_contract(
                    db,
                    contract,
                    company,
                    assignment_id=aa.id,
                    status=aa.status,
                    status_label=_assignment_status_label(aa.status)
                    or _assignment_status_label(contract.status),
                    role=aa.assignment_role or aa.role,
                    name_cache=name_cache,
                )
            )
        else:
            items.append(
                _schedule_item_from_contract(
                    db,
                    contract,
                    company,
                    assignment_id=None,
                    status=contract.status,
                    status_label=_assignment_status_label(contract.status)
                    or contract.status,
                    role="lead",
                    name_cache=name_cache,
                )
            )

    def _sort_key(it: AuditorScheduleItem):
        return it.audit_date or date.max

    items.sort(key=_sort_key)
    return items[:limit]


def _build_draft_reports(
    db: Session,
    auditor: Auditor,
    user_id: int,
    limit: int = 50,
) -> List[AuditorReportItem]:
    out: List[AuditorReportItem] = []
    contract_ids = _contract_ids_for_auditor(db, auditor, user_id)

    if _table_exists(db, "audit_reports"):
        q = db.query(AuditReports).filter(AuditReports.status.in_(list(_DRAFT_REPORT)))
        if contract_ids:
            q = q.filter(
                or_(
                    AuditReports.issued_by == user_id,
                    AuditReports.contract_id.in_(list(contract_ids)),
                )
            )
        else:
            q = q.filter(AuditReports.issued_by == user_id)
        rows = q.order_by(AuditReports.updated_at.desc()).limit(limit).all()
        company_ids = []
        contracts = {}
        if rows and _table_exists(db, "contracts"):
            cids = [r.contract_id for r in rows if r.contract_id]
            for c in db.query(Contracts).filter(Contracts.id.in_(cids)).all():
                contracts[c.id] = c
                company_ids.append(c.company_id)
        names = _company_name_map(db, company_ids)
        for r in rows:
            c = contracts.get(r.contract_id)
            out.append(
                AuditorReportItem(
                    id=r.id,
                    contract_id=r.contract_id,
                    company_id=c.company_id if c else None,
                    company_name=names.get(c.company_id) if c else None,
                    report_no=r.report_no,
                    report_type=r.report_type,
                    status=r.status,
                    status_label="작성중",
                    updated_at=r.updated_at,
                )
            )

    # Also surface in-progress audit notes as "draft report work"
    if len(out) < limit and _table_exists(db, "audit_notes"):
        note_q = (
            db.query(AuditNotes)
            .filter(
                AuditNotes.auditor_id == auditor.id,
                AuditNotes.status.in_(list(_DRAFT_NOTE)),
            )
            .order_by(AuditNotes.updated_at.desc())
            .limit(limit)
        )
        notes = note_q.all()
        cids = [n.contract_id for n in notes if n.contract_id]
        contracts = {}
        if cids and _table_exists(db, "contracts"):
            for c in db.query(Contracts).filter(Contracts.id.in_(cids)).all():
                contracts[c.id] = c
        names = _company_name_map(
            db, [c.company_id for c in contracts.values()]
        )
        existing = {(r.contract_id, "note") for r in out}
        for n in notes:
            key = (n.contract_id, "note")
            if key in existing:
                continue
            c = contracts.get(n.contract_id)
            out.append(
                AuditorReportItem(
                    id=n.id,
                    contract_id=n.contract_id,
                    company_id=c.company_id if c else None,
                    company_name=names.get(c.company_id) if c else None,
                    report_no=n.note_no,
                    report_type="audit_note",
                    status=n.status,
                    status_label="작성중(노트)",
                    updated_at=n.updated_at,
                )
            )
            if len(out) >= limit:
                break
    return out[:limit]


def _build_ncrs_pending(
    db: Session,
    auditor: Auditor,
    user_id: int,
    limit: int = 50,
) -> List[AuditorNcrItem]:
    if not _table_exists(db, "audit_ncrs"):
        return []
    contract_ids = _contract_ids_for_auditor(db, auditor, user_id)
    q = db.query(AuditNcrs).filter(AuditNcrs.status.in_(list(_NCR_PENDING)))
    if contract_ids:
        q = q.filter(
            or_(
                AuditNcrs.contract_id.in_(list(contract_ids)),
                AuditNcrs.issued_by == user_id,
                AuditNcrs.reviewed_by == user_id,
            )
        )
    else:
        q = q.filter(
            or_(
                AuditNcrs.issued_by == user_id,
                AuditNcrs.reviewed_by == user_id,
            )
        )
    rows = q.order_by(AuditNcrs.ca_submitted_at.desc(), AuditNcrs.id.desc()).limit(limit).all()
    cids = [r.contract_id for r in rows if r.contract_id]
    contracts = {}
    if cids and _table_exists(db, "contracts"):
        for c in db.query(Contracts).filter(Contracts.id.in_(cids)).all():
            contracts[c.id] = c
    names = _company_name_map(db, [c.company_id for c in contracts.values()])
    out: List[AuditorNcrItem] = []
    for r in rows:
        c = contracts.get(r.contract_id)
        out.append(
            AuditorNcrItem(
                id=r.id,
                contract_id=r.contract_id,
                company_id=c.company_id if c else None,
                company_name=names.get(c.company_id) if c else None,
                clause_id=r.clause_id,
                std_code=r.std_code,
                std_label=_standard_auditor_label(r.std_code),
                grade=r.grade,
                status=r.status,
                status_label=_ncr_status_label(r.status),
                due_date=r.due_date,
                ca_submitted_at=r.ca_submitted_at,
                finding=(r.finding or "")[:180] or None,
            )
        )
    return out


def _build_memberships(db: Session, auditor: Auditor) -> List[AuditorMembershipItem]:
    if not _table_exists(db, "auditor_cb_memberships"):
        return []
    today = date.today()
    rows = (
        db.query(AuditorCbMemberships, CertificationBodies)
        .outerjoin(
            CertificationBodies,
            CertificationBodies.id == AuditorCbMemberships.cb_id,
        )
        .filter(AuditorCbMemberships.auditor_id == auditor.id)
        .order_by(AuditorCbMemberships.is_primary.desc(), AuditorCbMemberships.id.desc())
        .all()
    )
    out: List[AuditorMembershipItem] = []
    for m, cb in rows:
        iaf = getattr(m, "approved_iaf_codes", None)
        out.append(
            AuditorMembershipItem(
                id=m.id,
                cb_id=m.cb_id,
                cb_name=cb.name if cb else None,
                cb_code=cb.code if cb else None,
                status=m.status,
                status_label=_membership_status_label(m.status),
                apply_grade=to_ui_grade(m.apply_grade),
                approved_grade=to_ui_grade(m.approved_grade),
                cert_standards=m.cert_standards,
                approved_iaf_codes=iaf,
                employment_type=getattr(m, "employment_type", None),
                kar_no=getattr(m, "kar_no", None),
                qualification_expires_at=m.qualification_expires_at,
                qual_dday=_dday(m.qualification_expires_at, today),
                is_primary=bool(m.is_primary),
            )
        )
    return out


def _build_qualifications(db: Session, auditor: Auditor) -> List[AuditorQualItem]:
    if not _table_exists(db, "auditor_qualifications"):
        return []
    today = date.today()
    rows = (
        db.query(AuditorQualification)
        .filter(AuditorQualification.auditor_id == auditor.id)
        .order_by(AuditorQualification.id.desc())
        .all()
    )
    out: List[AuditorQualItem] = []
    for q in rows:
        iaf_raw = q.iaf_codes
        if isinstance(iaf_raw, list):
            iaf_str = ", ".join(str(x) for x in iaf_raw if x is not None)
        elif iaf_raw is None:
            iaf_str = None
        else:
            iaf_str = str(iaf_raw)
        out.append(
            AuditorQualItem(
                id=q.id,
                standard_code=q.standard_code,
                standard_label=_standard_auditor_label(q.standard_code),
                grade=to_ui_grade(q.grade),
                cert_body_name=q.cert_body_name,
                cert_no=q.cert_no,
                expires_at=q.expires_at,
                dday=_dday(q.expires_at, today),
                is_active=bool(q.is_active),
                iaf_codes=iaf_str,
                major_name=q.major_name,
            )
        )
    return out


def _build_educations(db: Session, auditor: Auditor) -> List[AuditorEducationItem]:
    if not _table_exists(db, "auditor_educations"):
        return []
    try:
        rows = (
            db.query(AuditorEducation)
            .filter(AuditorEducation.auditor_id == auditor.id)
            .order_by(AuditorEducation.id.desc())
            .all()
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return []
    return [
        AuditorEducationItem(
            id=e.id,
            school_name=e.school_name,
            degree=e.degree,
            major=e.major,
            entered_at=e.entered_at,
            graduated_at=e.graduated_at,
        )
        for e in rows
    ]


def _build_careers(db: Session, auditor: Auditor) -> List[AuditorCareerItem]:
    if not _table_exists(db, "auditor_work_experiences"):
        return []
    try:
        rows = (
            db.query(AuditorWorkExperience)
            .filter(AuditorWorkExperience.auditor_id == auditor.id)
            .order_by(AuditorWorkExperience.id.desc())
            .all()
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return []
    return [
        AuditorCareerItem(
            id=c.id,
            company_name=c.company_name,
            position=c.position,
            department=c.department,
            iaf_code=c.iaf_code,
            ksic_code=c.ksic_code,
            start_date=c.start_date,
            end_date=c.end_date,
            is_current=bool(c.is_current),
            duties=getattr(c, "duties", None) or c.note,
        )
        for c in rows
    ]


def _build_external_certs(db: Session, auditor: Auditor) -> List[AuditorExternalCertItem]:
    if not _table_exists(db, "auditor_external_certs"):
        return []
    try:
        rows = (
            db.query(AuditorExternalCert)
            .filter(AuditorExternalCert.auditor_id == auditor.id)
            .order_by(AuditorExternalCert.id.desc())
            .all()
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return []
    return [
        AuditorExternalCertItem(
            id=x.id,
            cert_name=x.cert_name,
            issuer=x.issuer,
            cert_no=x.cert_no,
            grade=x.grade,
            issued_date=x.issued_date,
            expiry_date=x.expiry_date,
        )
        for x in rows
    ]


def _affiliation_kpi(
    memberships: Sequence[AuditorMembershipItem],
    qualifications: Sequence[AuditorQualItem],
) -> Tuple[str, Optional[str], int, Optional[date], Optional[int]]:
    approved = [m for m in memberships if m.status == AuditorCbMembershipsStatus.APPROVED.value]
    pending = [
        m
        for m in memberships
        if m.status
        in {
            AuditorCbMembershipsStatus.REQUESTED.value,
            AuditorCbMembershipsStatus.UNDER_REVIEW.value,
        }
    ]
    # nearest expiry among approved memberships + active quals
    candidates: List[Tuple[date, int]] = []
    for m in approved:
        if m.qualification_expires_at is not None and m.qual_dday is not None:
            candidates.append((m.qualification_expires_at, m.qual_dday))
    for q in qualifications:
        if q.expires_at is not None and q.dday is not None and (q.is_active or True):
            candidates.append((q.expires_at, q.dday))
    nearest_date = None
    nearest_dday = None
    if candidates:
        candidates.sort(key=lambda x: x[0])
        nearest_date, nearest_dday = candidates[0]

    if approved:
        status = "승인"
        detail = f"소속 CB {len(approved)}곳"
        if nearest_dday is not None:
            if nearest_dday < 0:
                detail = f"{detail} · 자격 만료 D+{abs(nearest_dday)}"
            else:
                detail = f"{detail} · 자격 D-{nearest_dday}"
        return status, detail, len(approved), nearest_date, nearest_dday
    if pending:
        return "승인 대기", f"신청 {len(pending)}건", 0, nearest_date, nearest_dday
    if memberships:
        return "미승인", f"소속 {len(memberships)}건", 0, nearest_date, nearest_dday
    return "미등록", "소속 CB 없음", 0, nearest_date, nearest_dday


@router.get("/dashboard-summary", response_model=AuditorDashboardSummary)
def get_auditor_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditorDashboardSummary:
    """심사원 본인 스코프 대시보드 요약 (일정/보고서/NCR/소속)."""
    _require_auditor(current_user)
    warnings: List[str] = []
    try:
        auditor = _get_auditor_for_user(db, current_user.id)
    except HTTPException:
        return AuditorDashboardSummary(
            warnings=["심사원 프로필이 없습니다."],
        )

    schedules_month = _safe(
        "schedules_month",
        lambda: _build_schedules(
            db, auditor, current_user.id, month_only=True, limit=100
        ),
        [],
        warnings,
    )
    schedules_all = _safe(
        "schedules",
        lambda: _build_schedules(
            db, auditor, current_user.id, month_only=False, limit=30
        ),
        [],
        warnings,
    )
    drafts = _safe(
        "draft_reports",
        lambda: _build_draft_reports(db, auditor, current_user.id, limit=30),
        [],
        warnings,
    )
    ncrs = _safe(
        "ncrs_pending",
        lambda: _build_ncrs_pending(db, auditor, current_user.id, limit=30),
        [],
        warnings,
    )
    memberships = _safe(
        "memberships",
        lambda: _build_memberships(db, auditor),
        [],
        warnings,
    )
    quals = _safe(
        "qualifications",
        lambda: _build_qualifications(db, auditor),
        [],
        warnings,
    )
    aff_status, aff_detail, approved_cnt, nearest_exp, nearest_dday = _affiliation_kpi(
        memberships, quals
    )

    kpis = AuditorKpiBlock(
        scheduled_this_month=len(schedules_month),
        draft_reports=len(drafts),
        ncr_review_pending=len(ncrs),
        affiliation_status=aff_status,
        affiliation_detail=aff_detail,
        approved_cb_count=approved_cnt,
        nearest_qual_expiry=nearest_exp,
        nearest_qual_dday=nearest_dday,
    )
    return AuditorDashboardSummary(
        auditor_id=auditor.id,
        auditor_name=auditor.name,
        kpis=kpis,
        schedules=schedules_all,
        ncrs_pending=ncrs,
        draft_reports=drafts,
        memberships=memberships,
        warnings=warnings,
    )


@router.get("/schedules", response_model=List[AuditorScheduleItem])
def list_auditor_schedules(
    year: Optional[int] = Query(None, description="캘린더 연도 (지정 시 해당 월 교집합)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="캘린더 월"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[AuditorScheduleItem]:
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    if year and month:
        return _build_schedules(
            db, auditor, current_user.id, year=year, month=month, limit=200
        )
    return _build_schedules(db, auditor, current_user.id, month_only=False, limit=200)


@router.get("/reports", response_model=List[AuditorReportItem])
def list_auditor_reports(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[AuditorReportItem]:
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    return _build_draft_reports(db, auditor, current_user.id, limit=100)


@router.get("/ncrs", response_model=List[AuditorNcrItem])
def list_auditor_ncrs(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[AuditorNcrItem]:
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    return _build_ncrs_pending(db, auditor, current_user.id, limit=100)


def _build_profile_summary(db: Session, auditor: Auditor) -> AuditorProfileSummary:
    primary_cb_name = None
    if auditor.primary_cb_id and _table_exists(db, "certification_bodies"):
        cb = (
            db.query(CertificationBodies)
            .filter(CertificationBodies.id == auditor.primary_cb_id)
            .first()
        )
        if cb:
            primary_cb_name = cb.name
    return AuditorProfileSummary(
        auditor_id=auditor.id,
        name=auditor.name,
        name_en=auditor.name_en,
        email=auditor.email,
        phone=auditor.phone,
        birth_date=auditor.birth_date,
        gender=auditor.gender,
        address=auditor.address,
        detail_address=auditor.detail_address,
        complais_no=auditor.complais_no,
        registration_no=auditor.registration_no,
        grade=to_ui_grade(auditor.grade),
        employment_type=auditor.employment_type,
        is_freelance=auditor.is_freelance,
        status=auditor.status,
        profile_status=auditor.profile_status,
        iaf_codes=auditor.iaf_codes,
        education_level=auditor.education_level,
        school_name=auditor.school_name,
        major=auditor.major,
        career_summary=auditor.career_summary,
        cb_affiliation=auditor.cb_affiliation,
        primary_cb_id=auditor.primary_cb_id,
        primary_cb_name=primary_cb_name,
        has_ci=bool(auditor.ci_key),
        memberships=_build_memberships(db, auditor),
        qualifications=_build_qualifications(db, auditor),
        educations=_build_educations(db, auditor),
        careers=_build_careers(db, auditor),
        external_certs=_build_external_certs(db, auditor),
    )


@router.get("/profile-summary", response_model=AuditorProfileSummary)
def get_auditor_profile_summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditorProfileSummary:
    """마이페이지·자격/소속 — 본인 심사원 프로필 (DB 실데이터)."""
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    return _build_profile_summary(db, auditor)


@router.get("/mypage", response_model=AuditorProfileSummary)
def get_auditor_mypage(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AuditorProfileSummary:
    """마이페이지 전용 alias — profile-summary 와 동일 페이로드."""
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    return _build_profile_summary(db, auditor)


# ---------------------------------------------------------------------------
# 배정 동의 / 불가일정 (브리핑 v4) — /auditor 와 /auditor-portal 동시 노출
# ---------------------------------------------------------------------------
from fastapi import Request
from pydantic import BaseModel, Field

from app.models.auth import Notifications, Users
from app.models.auditor import AuditorUnavailability
from app.services.auditor_assignment_fees import (
    mark_assignment_docs_signed,
    serialize_assignment,
    sync_contract_scheduled_if_all_confirmed,
)

portal_router = APIRouter(prefix="/auditor-portal", tags=["Auditor Portal"])


class AssignmentRevisionIn(BaseModel):
    comment: str = Field(..., min_length=1)


class UnavailabilityIn(BaseModel):
    start_date: date
    end_date: date
    note: Optional[str] = None


class UnavailabilityOut(BaseModel):
    id: int
    auditor_id: int
    start_date: date
    end_date: date
    note: Optional[str] = None


def _client_ip(request: Request) -> Optional[str]:
    xff = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if xff:
        return xff
    return request.client.host if request.client else None


def _notify_user_ids(
    db: Session,
    user_ids: List[int],
    *,
    ntype: str,
    title: str,
    body: str,
    link: str,
    sent_at: datetime,
) -> None:
    for uid in user_ids:
        if not uid:
            continue
        db.add(
            Notifications(
                user_id=int(uid),
                type=ntype,
                title=title,
                body=body,
                link=link,
                channel="in_app",
                is_read=False,
                sent_at=sent_at,
            )
        )


def _cb_user_ids(db: Session, cb_id: Optional[int]) -> List[int]:
    if not cb_id:
        return []
    try:
        rows = (
            db.query(Users.id)
            .filter(Users.cb_id == int(cb_id), Users.is_active == True)  # noqa: E712
            .all()
        )
        return [int(uid) for (uid,) in rows if uid]
    except Exception:
        logger.exception("cb notify lookup soft-fail")
        return []


def _get_own_assignment(
    db: Session, assignment_id: int, auditor: Auditor
) -> AuditAssignments:
    row = db.get(AuditAssignments, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="배정을 찾을 수 없습니다.")
    if int(row.auditor_id or 0) != int(auditor.id) and int(row.auditor_user_id or 0) != int(
        auditor.user_id or 0
    ):
        raise HTTPException(status_code=403, detail="본인 배정건만 처리할 수 있습니다.")
    return row


def _accept_assignment_impl(
    *,
    assignment_id: int,
    request: Request,
    db: Session,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    row = _get_own_assignment(db, assignment_id, auditor)
    before = (row.status or "").lower()
    if before not in {"assigned", "revision_requested"}:
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({row.status})에서는 동의할 수 없습니다.",
        )
    if not row.contract_id:
        raise HTTPException(status_code=400, detail="계약이 연결되지 않은 배정입니다.")
    contract = db.get(Contracts, int(row.contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    now = datetime.now()
    row.status = "confirmed"
    row.updated_at = now
    doc_ids = mark_assignment_docs_signed(
        db,
        contract_id=int(row.contract_id),
        auditor_id=int(row.auditor_id),
        signed_by_user_id=current_user.id,
        signed_ip=_client_ip(request),
        now=now,
    )
    scheduled = sync_contract_scheduled_if_all_confirmed(db, contract)
    contract.updated_at = now
    _notify_user_ids(
        db,
        _cb_user_ids(db, contract.cb_id),
        ntype="assignment_accepted",
        title="심사원이 배정에 동의했습니다",
        body=f"배정 #{row.id} (auditor_id={row.auditor_id}) 동의 완료.",
        link="/cb-portal",
        sent_at=now,
    )
    db.commit()
    db.refresh(row)
    return {
        "ok": True,
        "assignment": serialize_assignment(row),
        "document_ids": doc_ids,
        "contract_status": contract.status,
        "all_confirmed_scheduled": scheduled,
    }


def _revision_assignment_impl(
    *,
    assignment_id: int,
    comment: str,
    db: Session,
    current_user: CurrentUser,
) -> Dict[str, Any]:
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)
    row = _get_own_assignment(db, assignment_id, auditor)
    before = (row.status or "").lower()
    if before not in {"assigned", "revision_requested"}:
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({row.status})에서는 조율 요청할 수 없습니다.",
        )
    note = (comment or "").strip()
    if not note:
        raise HTTPException(status_code=400, detail="조율 요청 사유를 입력해 주세요.")
    if not row.contract_id:
        raise HTTPException(status_code=400, detail="계약이 연결되지 않은 배정입니다.")
    contract = db.get(Contracts, int(row.contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    now = datetime.now()
    row.status = "revision_requested"
    row.assignment_note = note
    row.updated_at = now
    sync_contract_scheduled_if_all_confirmed(db, contract)
    contract.updated_at = now
    _notify_user_ids(
        db,
        _cb_user_ids(db, contract.cb_id),
        ntype="assignment_revision_requested",
        title="심사원이 배정 조율을 요청했습니다",
        body=f"배정 #{row.id} (auditor_id={row.auditor_id}): {note}",
        link="/cb-portal",
        sent_at=now,
    )
    db.commit()
    db.refresh(row)
    return {"ok": True, "assignment": serialize_assignment(row), "contract_status": contract.status}


def _register_assignment_routes(r: APIRouter) -> None:
    @r.post("/assignments/{assignment_id}/accept")
    def accept_assignment(
        assignment_id: int,
        request: Request,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        """배정 동의: assigned → confirmed + 문서 signed/completed."""
        return _accept_assignment_impl(
            assignment_id=assignment_id,
            request=request,
            db=db,
            current_user=current_user,
        )

    @r.post("/assignments/{assignment_id}/revision")
    def revision_assignment(
        assignment_id: int,
        payload: AssignmentRevisionIn,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        """배정 조율 요청: → revision_requested + CB 알림."""
        return _revision_assignment_impl(
            assignment_id=assignment_id,
            comment=payload.comment,
            db=db,
            current_user=current_user,
        )

    @r.post("/assignments/{assignment_id}/decline")
    def decline_assignment_alias(
        assignment_id: int,
        payload: AssignmentRevisionIn,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        """decline 별칭 → revision_requested."""
        return _revision_assignment_impl(
            assignment_id=assignment_id,
            comment=payload.comment,
            db=db,
            current_user=current_user,
        )

    @r.get("/unavailability", response_model=List[UnavailabilityOut])
    def list_unavailability(
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        _require_auditor(current_user)
        auditor = _get_auditor_for_user(db, current_user.id)
        rows = (
            db.query(AuditorUnavailability)
            .filter(AuditorUnavailability.auditor_id == auditor.id)
            .order_by(AuditorUnavailability.start_date.desc())
            .all()
        )
        return [
            UnavailabilityOut(
                id=r.id,
                auditor_id=r.auditor_id,
                start_date=r.start_date,
                end_date=r.end_date,
                note=r.note,
            )
            for r in rows
        ]

    @r.post("/unavailability", response_model=UnavailabilityOut)
    def create_unavailability(
        payload: UnavailabilityIn,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        _require_auditor(current_user)
        auditor = _get_auditor_for_user(db, current_user.id)
        if payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date 는 start_date 이후여야 합니다.")
        now = datetime.now()
        row = AuditorUnavailability(
            auditor_id=auditor.id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            note=payload.note,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return UnavailabilityOut(
            id=row.id,
            auditor_id=row.auditor_id,
            start_date=row.start_date,
            end_date=row.end_date,
            note=row.note,
        )

    @r.delete("/unavailability/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_unavailability(
        row_id: int,
        db: Session = Depends(get_db),
        current_user: CurrentUser = Depends(get_current_user),
    ):
        _require_auditor(current_user)
        auditor = _get_auditor_for_user(db, current_user.id)
        row = db.get(AuditorUnavailability, row_id)
        if row is None or int(row.auditor_id) != int(auditor.id):
            raise HTTPException(status_code=404, detail="불가일정을 찾을 수 없습니다.")
        db.delete(row)
        db.commit()
        return None


_register_assignment_routes(router)
_register_assignment_routes(portal_router)
