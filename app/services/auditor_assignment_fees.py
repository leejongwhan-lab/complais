"""System1 심사원 배정 — 관리기업 판단·수수료 스냅샷·문서 생성."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit import AuditAssignments, AuditDocuments
from app.models.auditor import Auditor, AuditorCbMemberships, AuditorConductSigns, AuditorManagedCompanies
from app.models.cb import CbAuditorRoleRates
from app.services.settlement_calculator import (
    calculate_assignment_fee,
    resolve_fee_type_for_auditor,
)

DOC_AUDITOR_CONTRACT = "AUDITOR_CONTRACT"
DOC_NDA = "NDA"


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


def ensure_auditor_assignment_docs(
    db: Session,
    *,
    contract_id: int,
    assignment: AuditAssignments,
    created_by: Optional[int],
    now: Optional[datetime] = None,
) -> List[int]:
    """CONFIRMED 배정 시 AUDITOR_CONTRACT / NDA 문서 초안 생성(중복 방지)."""
    now = now or datetime.now()
    created_ids: List[int] = []
    specs = (
        (DOC_AUDITOR_CONTRACT, "심사원 위촉계약서", "auditor"),
        (DOC_NDA, "비밀유지서약서(NDA)", "nda"),
    )
    auditor_id = assignment.auditor_id
    for doc_type, title, subtype in specs:
        exists = (
            db.query(AuditDocuments.id)
            .filter(
                AuditDocuments.contract_id == contract_id,
                AuditDocuments.doc_type == doc_type,
                AuditDocuments.doc_subtype == f"{subtype}:{auditor_id}",
            )
            .first()
        )
        if exists:
            continue
        payload = {
            "assignment_id": assignment.id,
            "auditor_id": auditor_id,
            "auditor_user_id": assignment.auditor_user_id,
            "role": assignment.role,
            "fee_type": assignment.fee_type,
            "fee_ratio": float(assignment.fee_ratio) if assignment.fee_ratio is not None else None,
            "daily_rate": assignment.daily_rate,
            "assigned_days": float(assignment.assigned_days)
            if assignment.assigned_days is not None
            else None,
            "calculated_fee": float(assignment.calculated_fee)
            if assignment.calculated_fee is not None
            else None,
        }
        doc = AuditDocuments(
            contract_id=contract_id,
            doc_type=doc_type,
            doc_subtype=f"{subtype}:{auditor_id}",
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
            file_path=None,
            file_size=None,
            mime_type=None,
            uploaded_by=None,
            uploaded_at=None,
            is_visible_to_client=False,
            created_at=now,
        )
        db.add(doc)
        db.flush()
        created_ids.append(int(doc.id))
    return created_ids


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
