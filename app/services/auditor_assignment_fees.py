"""System1 심사원 배정 — 관리기업 판단·수수료 스냅샷·문서 생성."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit import AuditAssignments, AuditDocuments
from app.models.auditor import Auditor, AuditorCbMemberships, AuditorConductSigns, AuditorManagedCompanies
from app.models.cb import CertificationBodies, CbAuditorRoleRates
from app.models.company import Companies
from app.models.contract import Contracts
from app.services.settlement_calculator import (
    calculate_assignment_fee,
    resolve_fee_type_for_auditor,
)

DOC_AUDITOR_CONTRACT = "AUDITOR_CONTRACT"
DOC_NDA = "NDA"

_ENGAGEMENT_HTML = "/audit-docs/auditor_engagement"


def assert_auditors_exist(db: Session, auditor_ids: Sequence[int]) -> None:
    for auditor_id in auditor_ids:
        exists = db.query(Auditor.id).filter(Auditor.id == auditor_id).first()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"심사원(auditor_id={auditor_id})을 찾을 수 없습니다.")


def assert_conduct_signs(db: Session, auditor_ids: Sequence[int]) -> None:
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
                status_code=400,
                detail=f"심사원(auditor_id={auditor_id})의 유효한 비밀유지·공평성 서약서가 없습니다.",
            )
        if row.expires_at is not None and row.expires_at < today:
            raise HTTPException(
                status_code=400,
                detail=f"심사원(auditor_id={auditor_id})의 서약서가 만료되었습니다 (expires_at={row.expires_at}).",
            )


def auditor_user_id_or_raise(db: Session, auditor_id: int) -> int:
    row = db.query(Auditor.id, Auditor.user_id).filter(Auditor.id == auditor_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"심사원(auditor_id={auditor_id})을 찾을 수 없습니다.")
    if not row.user_id:
        raise HTTPException(
            status_code=400,
            detail=f"심사원(auditor_id={auditor_id})에 user_id가 없어 audit_assignments에 배정할 수 없습니다.",
        )
    return int(row.user_id)


def is_managed_company_auditor(
    db: Session, *, auditor_id: int, company_id: int, cb_id: int
) -> bool:
    row = (
        db.query(AuditorManagedCompanies.id)
        .filter(
            AuditorManagedCompanies.auditor_id == auditor_id,
            AuditorManagedCompanies.company_id == company_id,
            AuditorManagedCompanies.cb_id == cb_id,
            AuditorManagedCompanies.status == "ACTIVE",
        )
        .first()
    )
    return row is not None


def _membership(db: Session, auditor_id: int, cb_id: int) -> Optional[AuditorCbMemberships]:
    return (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.auditor_id == auditor_id,
            AuditorCbMemberships.cb_id == cb_id,
        )
        .order_by(AuditorCbMemberships.is_primary.desc(), AuditorCbMemberships.id.desc())
        .first()
    )


def resolve_daily_rate(db: Session, *, cb_id: int, role: str, auditor_id: int) -> int:
    """CbAuditorRoleRates 우선 → auditor_cb_memberships.daily_rate 폴백."""
    role_key = (role or "auditor").strip().lower()
    rate_row = (
        db.query(CbAuditorRoleRates)
        .filter(
            CbAuditorRoleRates.cb_id == cb_id,
            CbAuditorRoleRates.role == role_key,
            CbAuditorRoleRates.is_active.is_(True),
        )
        .first()
    )
    if rate_row is not None and rate_row.daily_rate is not None and int(rate_row.daily_rate) > 0:
        return int(rate_row.daily_rate)

    mem = _membership(db, auditor_id, cb_id)
    if mem is not None and mem.daily_rate is not None and int(mem.daily_rate) > 0:
        return int(mem.daily_rate)

    raise HTTPException(
        status_code=400,
        detail=(
            f"CB(cb_id={cb_id}) role='{role_key}' 일당이 없습니다. "
            "cb_auditor_role_rates 를 설정하거나 membership.daily_rate 를 등록하세요."
        ),
    )


def resolve_fee_ratio(db: Session, *, auditor_id: int, cb_id: int) -> float:
    mem = _membership(db, auditor_id, cb_id)
    if mem is None or mem.fee_ratio is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"관리기업 심사원(auditor_id={auditor_id})의 fee_ratio 가 "
                f"auditor_cb_memberships 에 없습니다 (cb_id={cb_id})."
            ),
        )
    return float(mem.fee_ratio)


def default_assigned_days(
    *,
    audit_start: Optional[date],
    audit_end: Optional[date],
    total_md: Optional[float],
    assigned_days: Optional[float],
) -> float:
    if assigned_days is not None and float(assigned_days) > 0:
        return float(assigned_days)
    if audit_start and audit_end and audit_end >= audit_start:
        return float((audit_end - audit_start).days + 1)
    if total_md is not None and float(total_md) > 0:
        return float(total_md)
    return 0.0


def build_fee_snapshot(
    db: Session,
    *,
    auditor_id: int,
    company_id: int,
    cb_id: int,
    role: str,
    agreed_amount: float,
    assigned_days: float,
) -> Dict[str, Any]:
    managed = is_managed_company_auditor(
        db, auditor_id=auditor_id, company_id=company_id, cb_id=cb_id
    )
    fee_type = resolve_fee_type_for_auditor(is_managed_company=managed)
    fee_ratio = 0.0
    daily_rate = 0
    if fee_type == "PERCENTAGE":
        fee_ratio = resolve_fee_ratio(db, auditor_id=auditor_id, cb_id=cb_id)
    else:
        daily_rate = resolve_daily_rate(db, cb_id=cb_id, role=role, auditor_id=auditor_id)

    result = calculate_assignment_fee(
        fee_type,
        agreed_amount=agreed_amount,
        fee_ratio=fee_ratio,
        daily_rate=float(daily_rate),
        assigned_days=assigned_days,
    )
    result["is_managed_company"] = managed
    return result


def _role_label(role: Optional[str]) -> str:
    key = (role or "").strip().lower()
    return {
        "lead": "심사팀장",
        "lead_auditor": "심사팀장",
        "auditor": "심사원",
        "member": "심사원",
        "expert": "기술전문가",
        "observer": "참관인",
        "witness": "입회",
    }.get(key, role or "심사원")


def _ymd(d: Any) -> Optional[str]:
    if d is None:
        return None
    if hasattr(d, "isoformat"):
        return d.isoformat()
    s = str(d).strip()
    return s[:10] if s else None


def _fee_terms_text(assignment: AuditAssignments) -> str:
    ft = (assignment.fee_type or "").upper()
    if ft == "PERCENTAGE":
        ratio = float(assignment.fee_ratio or 0)
        pct = ratio * 100 if ratio <= 1 else ratio
        return (
            f"정률(PERCENTAGE) — 계약금 대비 {pct:.2f}% "
            f"(산출 수수료 {float(assignment.calculated_fee or 0):,.0f}원)"
        )
    days = float(assignment.assigned_days or 0)
    rate = int(assignment.daily_rate or 0)
    return (
        f"일당(DAILY_RATE) — 일당 {rate:,}원 × {days:g}일 "
        f"(산출 수수료 {float(assignment.calculated_fee or 0):,.0f}원)"
    )


def build_engagement_doc_payload(
    db: Session,
    *,
    contract: Contracts,
    assignment: AuditAssignments,
    doc_type: str,
) -> Dict[str, Any]:
    """Readable AUDITOR_CONTRACT / NDA structured content for AuditDocuments.data."""
    auditor = db.get(Auditor, int(assignment.auditor_id)) if assignment.auditor_id else None
    cb = db.get(CertificationBodies, int(contract.cb_id)) if contract.cb_id else None
    company = db.get(Companies, int(contract.company_id)) if contract.company_id else None

    role = assignment.role or assignment.assignment_role
    period_start = _ymd(getattr(contract, "audit_period_start", None))
    period_end = _ymd(getattr(contract, "audit_period_end", None))
    period = (
        f"{period_start or '—'} ~ {period_end or '—'}"
        if period_start or period_end
        else "—"
    )
    standards = (contract.standards or contract.applied_standards or "").strip() or "—"
    auditor_name = (auditor.name if auditor else None) or f"auditor_id={assignment.auditor_id}"
    grade = (auditor.grade if auditor else None) or ""
    qual = " / ".join([p for p in [auditor_name, _role_label(role), grade] if p])

    parties = {
        "cb_name": (cb.name if cb else None) or f"CB#{contract.cb_id}",
        "cb_ceo": (cb.ceo_name if cb else None),
        "cb_address": (cb.address if cb else None),
        "cb_biz_no": (cb.biz_no if cb else None),
        "auditor_name": auditor_name,
        "auditor_id": assignment.auditor_id,
        "auditor_grade": grade or None,
        "auditor_role": _role_label(role),
        "auditor_qual_label": qual,
        "company_name": (company.name if company else None),
    }
    engagement = {
        "contract_id": contract.id,
        "contract_no": getattr(contract, "contract_id", None),
        "audit_type": contract.audit_type,
        "standards": standards,
        "scope_kr": contract.scope_kr,
        "period_start": period_start,
        "period_end": period_end,
        "period_label": period,
        "role": role,
        "role_label": _role_label(role),
        "assignment_id": assignment.id,
    }
    fee_terms = {
        "fee_type": assignment.fee_type,
        "fee_ratio": float(assignment.fee_ratio) if assignment.fee_ratio is not None else None,
        "daily_rate": assignment.daily_rate,
        "assigned_days": float(assignment.assigned_days)
        if assignment.assigned_days is not None
        else None,
        "calculated_fee": float(assignment.calculated_fee)
        if assignment.calculated_fee is not None
        else None,
        "summary": _fee_terms_text(assignment),
    }

    is_nda = doc_type == DOC_NDA
    doc_kind = "nda" if is_nda else "contract"
    html_url = (
        f"{_ENGAGEMENT_HTML}?assignment_id={assignment.id}&doc={doc_kind}"
        f"&contract_id={contract.id}"
    )

    if is_nda:
        sections = [
            {
                "no": 1,
                "title": "당사자",
                "body": (
                    f"인증기관(갑): {parties['cb_name']}\n"
                    f"심사원(을): {parties['auditor_qual_label']}"
                ),
            },
            {
                "no": 2,
                "title": "비밀정보의 범위",
                "body": (
                    "심사 과정에서 취득한 고객·인증기관의 경영시스템·기술·상업 정보, "
                    "심사노트·NCR·보고서 초안, 인력·수수료 정보 일체를 포함한다."
                ),
            },
            {
                "no": 3,
                "title": "비밀유지 의무 (ISO/IEC 17021-1 §8.4)",
                "body": (
                    "을은 비밀정보를 심사 목적 외로 사용·복제·제3자 제공하지 않으며, "
                    "법령 또는 인정기구 요구에 따른 공개 시 갑에 사전 통지한다. "
                    "비밀유지 의무는 배정 종료 후에도 유효하다."
                ),
            },
            {
                "no": 4,
                "title": "대상 심사",
                "body": (
                    f"계약 #{engagement['contract_id']} / {engagement['contract_no'] or '—'}\n"
                    f"표준: {standards}\n기간: {period}\n역할: {engagement['role_label']}"
                ),
            },
            {
                "no": 5,
                "title": "동의·서명",
                "body": (
                    "본 서약서 열람 후 배정 동의(accept)는 비밀유지 의무에 대한 "
                    "전자적 동의·서명으로 간주한다."
                ),
            },
        ]
        title_base = "비밀유지서약서(NDA)"
    else:
        sections = [
            {
                "no": 1,
                "title": "계약 당사자",
                "body": (
                    f"인증기관(갑): {parties['cb_name']}"
                    + (f" / 대표 {parties['cb_ceo']}" if parties.get("cb_ceo") else "")
                    + (f"\n소재지: {parties['cb_address']}" if parties.get("cb_address") else "")
                    + f"\n심사원(을): {parties['auditor_qual_label']}"
                    + (
                        f"\n피심사조직: {parties['company_name']}"
                        if parties.get("company_name")
                        else ""
                    )
                ),
            },
            {
                "no": 2,
                "title": "위촉 범위·역할",
                "body": (
                    f"적용 표준: {standards}\n"
                    f"심사 기간: {period}\n"
                    f"역할: {engagement['role_label']}\n"
                    f"인증 범위: {(engagement.get('scope_kr') or '—')}"
                ),
            },
            {
                "no": 3,
                "title": "수수료 조건",
                "body": fee_terms["summary"],
            },
            {
                "no": 4,
                "title": "심사원 의무 (ISO/IEC 17021-1 §5.1.2 · §9)",
                "body": (
                    "을은 공평성·독립성을 유지하고, 배정된 심사 계획·노트·보고서를 "
                    "성실히 수행하며, 이해충돌이 있는 경우 즉시 갑에 고지한다. "
                    "인증 결정 권한은 갑(인증기관)에 있다."
                ),
            },
            {
                "no": 5,
                "title": "이의 제기 및 불만",
                "body": (
                    "본 위촉과 관련한 이의·불만은 인증기관의 ISO/IEC 17021-1 §9.7·§9.8 "
                    "절차에 따른다."
                ),
            },
            {
                "no": 6,
                "title": "동의·서명",
                "body": (
                    "본 계약서 열람 후 배정 동의(accept)는 위 조건에 대한 "
                    "전자적 동의·서명으로 간주한다."
                ),
            },
        ]
        title_base = "심사원 위촉계약서"

    return {
        "readable": True,
        "doc_type": doc_type,
        "doc_kind": doc_kind,
        "title": title_base,
        "iso_ref": "ISO/IEC 17021-1 §5.1.2 · §8.4",
        "assignment_id": assignment.id,
        "auditor_id": assignment.auditor_id,
        "auditor_user_id": assignment.auditor_user_id,
        "contract_id": contract.id,
        "role": role,
        "fee_type": assignment.fee_type,
        "fee_ratio": fee_terms["fee_ratio"],
        "daily_rate": assignment.daily_rate,
        "assigned_days": fee_terms["assigned_days"],
        "calculated_fee": fee_terms["calculated_fee"],
        "parties": parties,
        "engagement": engagement,
        "fee_terms": fee_terms,
        "sections": sections,
        "html_url": html_url,
        "accept_means_agreement": True,
    }


def _parse_doc_data(raw: Optional[str]) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"raw": raw}
    except Exception:
        return {"raw": raw}


def ensure_auditor_assignment_docs(
    db: Session,
    *,
    contract_id: int,
    assignment: AuditAssignments,
    created_by: Optional[int],
    now: Optional[datetime] = None,
) -> List[int]:
    """배정(assigned) 시 AUDITOR_CONTRACT / NDA 문서 생성·갱신(readable content)."""
    now = now or datetime.now()
    created_ids: List[int] = []
    specs: Tuple[Tuple[str, str, str], ...] = (
        (DOC_AUDITOR_CONTRACT, "심사원 위촉계약서", "auditor"),
        (DOC_NDA, "비밀유지서약서(NDA)", "nda"),
    )
    auditor_id = assignment.auditor_id
    contract = db.get(Contracts, int(contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    for doc_type, title, subtype in specs:
        subtype_key = f"{subtype}:{auditor_id}"
        existing = (
            db.query(AuditDocuments)
            .filter(
                AuditDocuments.contract_id == contract_id,
                AuditDocuments.doc_type == doc_type,
                AuditDocuments.doc_subtype == subtype_key,
            )
            .first()
        )
        payload = build_engagement_doc_payload(
            db, contract=contract, assignment=assignment, doc_type=doc_type
        )
        html_url = payload.get("html_url") or (
            f"{_ENGAGEMENT_HTML}?assignment_id={assignment.id}"
        )

        if existing:
            # signed/completed 는 보존, draft 만 가독 콘텐츠로 갱신
            st = (existing.status or "").lower()
            ds = (existing.doc_status or "").lower()
            if st in {"signed", "completed"} or ds == "completed":
                continue
            meta = _parse_doc_data(existing.data)
            # 서명 메타가 있으면 유지
            for k in ("signed_at", "signed_by_user_id", "signed_ip", "ip_address"):
                if k in meta and k not in payload:
                    payload[k] = meta[k]
            existing.data = json.dumps(payload, ensure_ascii=False)
            existing.title = f"{title} (auditor_id={auditor_id})"
            existing.file_path = html_url
            existing.mime_type = "text/html"
            existing.updated_by = created_by
            created_ids.append(int(existing.id))
            continue

        doc = AuditDocuments(
            contract_id=contract_id,
            doc_type=doc_type,
            doc_subtype=subtype_key,
            standard=None,
            stage=0,
            doc_status="pending",
            rule_id=None,
            doc_no=None,
            title=f"{title} (auditor_id={auditor_id})",
            data=json.dumps(payload, ensure_ascii=False),
            verdict=None,
            status="draft",
            updated_by=created_by,
            created_by=created_by,
            file_path=html_url,
            file_size=None,
            mime_type="text/html",
            uploaded_by=None,
            uploaded_at=None,
            is_visible_to_client=False,
            created_at=now,
        )
        db.add(doc)
        db.flush()
        created_ids.append(int(doc.id))
    return created_ids


def mark_assignment_docs_signed(
    db: Session,
    *,
    contract_id: int,
    auditor_id: int,
    signed_by_user_id: Optional[int],
    signed_ip: Optional[str] = None,
    now: Optional[datetime] = None,
) -> List[int]:
    """심사원 accept 시 AUDITOR_CONTRACT/NDA → signed/completed + 서명 메타(data JSON)."""
    now = now or datetime.now()
    updated: List[int] = []
    rows = (
        db.query(AuditDocuments)
        .filter(
            AuditDocuments.contract_id == contract_id,
            AuditDocuments.doc_type.in_([DOC_AUDITOR_CONTRACT, DOC_NDA]),
            AuditDocuments.doc_subtype.in_(
                [f"auditor:{auditor_id}", f"nda:{auditor_id}"]
            ),
        )
        .all()
    )
    for doc in rows:
        meta = _parse_doc_data(doc.data)
        meta["signed_at"] = now.isoformat(timespec="seconds")
        meta["signed_by_user_id"] = signed_by_user_id
        meta["agreed_by_accept"] = True
        if signed_ip:
            meta["signed_ip"] = signed_ip
            meta["ip_address"] = signed_ip
        doc.data = json.dumps(meta, ensure_ascii=False)
        doc.status = "signed"
        doc.doc_status = "completed"
        doc.updated_by = signed_by_user_id
        updated.append(int(doc.id))
    return updated


def get_assignment_engagement_docs(
    db: Session,
    *,
    assignment: AuditAssignments,
) -> Dict[str, Any]:
    """포털/HTML용 위촉계약·NDA 페이로드."""
    if not assignment.contract_id:
        raise HTTPException(status_code=400, detail="계약이 연결되지 않은 배정입니다.")
    contract = db.get(Contracts, int(assignment.contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    # draft enrichment (idempotent)
    ensure_auditor_assignment_docs(
        db,
        contract_id=int(assignment.contract_id),
        assignment=assignment,
        created_by=None,
    )
    db.flush()

    docs_out: List[Dict[str, Any]] = []
    rows = (
        db.query(AuditDocuments)
        .filter(
            AuditDocuments.contract_id == int(assignment.contract_id),
            AuditDocuments.doc_type.in_([DOC_AUDITOR_CONTRACT, DOC_NDA]),
            AuditDocuments.doc_subtype.in_(
                [
                    f"auditor:{assignment.auditor_id}",
                    f"nda:{assignment.auditor_id}",
                ]
            ),
        )
        .all()
    )
    by_type = {r.doc_type: r for r in rows}
    for dtype in (DOC_AUDITOR_CONTRACT, DOC_NDA):
        row = by_type.get(dtype)
        if row is None:
            payload = build_engagement_doc_payload(
                db, contract=contract, assignment=assignment, doc_type=dtype
            )
            docs_out.append(
                {
                    "id": None,
                    "doc_type": dtype,
                    "status": "draft",
                    "doc_status": "pending",
                    "title": payload.get("title"),
                    "html_url": payload.get("html_url"),
                    "data": payload,
                }
            )
            continue
        data = _parse_doc_data(row.data)
        if not data.get("readable"):
            data = build_engagement_doc_payload(
                db, contract=contract, assignment=assignment, doc_type=dtype
            )
            # preserve signature if any
            prev = _parse_doc_data(row.data)
            for k in ("signed_at", "signed_by_user_id", "signed_ip", "ip_address", "agreed_by_accept"):
                if k in prev:
                    data[k] = prev[k]
        docs_out.append(
            {
                "id": row.id,
                "doc_type": row.doc_type,
                "status": row.status,
                "doc_status": row.doc_status,
                "title": row.title,
                "html_url": data.get("html_url") or row.file_path,
                "data": data,
            }
        )

    return {
        "assignment": serialize_assignment(assignment),
        "contract_id": contract.id,
        "contract_no": getattr(contract, "contract_id", None),
        "can_accept": (assignment.status or "").lower()
        in {"assigned", "revision_requested"},
        "documents": docs_out,
        "accept_url": f"/api/v1/auditor/assignments/{assignment.id}/accept",
        "accept_means_agreement": True,
    }


def sync_contract_scheduled_if_all_confirmed(db: Session, contract: Contracts) -> bool:
    """전원 confirmed일 때만 contracts.status=scheduled. 아니면 scheduled→draft(서명후) 유지하지 않음.

    이미 signed 등 상위 상태는 건드리지 않고, scheduled만 조건부 설정/해제한다.
    """
    rows = (
        db.query(AuditAssignments.status)
        .filter(AuditAssignments.contract_id == contract.id)
        .all()
    )
    if not rows:
        return False
    statuses = [(r[0] or "").lower() for r in rows]
    all_confirmed = all(s == "confirmed" for s in statuses)
    cur = (contract.status or "").lower()
    if all_confirmed:
        if cur != "scheduled":
            contract.status = "scheduled"
        return True
    # 미전원 확정: scheduled 였으면 되돌림(재배정/조율 중)
    if cur == "scheduled":
        contract.status = "signed" if getattr(contract, "client_signed_at", None) else "draft"
    return False


def serialize_assignment(row: AuditAssignments) -> Dict[str, Any]:
    return {
        "id": row.id,
        "application_id": row.application_id,
        "contract_id": row.contract_id,
        "auditor_id": row.auditor_id,
        "auditor_user_id": row.auditor_user_id,
        "role": row.role,
        "assignment_role": row.assignment_role,
        "status": row.status,
        "fee_type": row.fee_type,
        "fee_ratio": float(row.fee_ratio) if row.fee_ratio is not None else None,
        "daily_rate": row.daily_rate,
        "assigned_days": float(row.assigned_days) if row.assigned_days is not None else None,
        "calculated_fee": float(row.calculated_fee) if row.calculated_fee is not None else None,
        "assigned_at": row.assigned_at.isoformat() if row.assigned_at else None,
    }
