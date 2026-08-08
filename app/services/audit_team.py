"""심사팀 규모·팀 검토 확인 — AuditAssignments / Contracts SoT."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Set

from sqlalchemy.orm import Session

from app.models.audit import AuditAssignments
from app.models.contract import Contracts

# accept 이후 확정 이상 (assigned / revision_requested 제외)
CONFIRMED_OR_ABOVE: Set[str] = {
    "confirmed",
    "accepted",
    "in_progress",
    "scheduled",
    "completed",
    "확정",
    "진행중",
    "완료",
}


def count_confirmed_auditors(db: Session, contract_id: int) -> int:
    """계약에 confirmed-or-above 배정된 심사원 수 (AuditAssignments SoT)."""
    if not contract_id:
        return 0
    rows = (
        db.query(AuditAssignments.status)
        .filter(AuditAssignments.contract_id == int(contract_id))
        .all()
    )
    n = 0
    for (st,) in rows:
        raw = (st or "").strip()
        if raw.lower() in CONFIRMED_OR_ABOVE or raw in CONFIRMED_OR_ABOVE:
            n += 1
    return n


def team_size_requires_review(db: Session, contract_id: int) -> bool:
    """2명 이상이면 NCR 적합 전환 시 팀장 팀검토 게이트 적용."""
    return count_confirmed_auditors(db, contract_id) >= 2


def is_team_review_confirmed(db: Session, contract_id: int) -> bool:
    contract = db.get(Contracts, int(contract_id))
    if contract is None:
        return False
    return getattr(contract, "team_review_confirmed_at", None) is not None


def get_team_review_state(db: Session, contract_id: int) -> Dict[str, Any]:
    contract = db.get(Contracts, int(contract_id))
    size = count_confirmed_auditors(db, contract_id)
    confirmed_at = getattr(contract, "team_review_confirmed_at", None) if contract else None
    confirmed_by = getattr(contract, "team_review_confirmed_by", None) if contract else None
    return {
        "team_size": size,
        "requires_team_review": size >= 2,
        "team_review_confirmed": confirmed_at is not None,
        "team_review_confirmed_at": confirmed_at.isoformat(timespec="seconds")
        if confirmed_at
        else None,
        "team_review_confirmed_by": int(confirmed_by) if confirmed_by else None,
    }


def confirm_team_review(
    db: Session,
    *,
    contract_id: int,
    confirmed_by_user_id: int,
    now: Optional[datetime] = None,
) -> Contracts:
    """팀장 팀검토 확인 — contracts.team_review_confirmed_* 기록."""
    now = now or datetime.now()
    contract = db.get(Contracts, int(contract_id))
    if contract is None:
        raise ValueError("contract_not_found")
    contract.team_review_confirmed_at = now
    contract.team_review_confirmed_by = int(confirmed_by_user_id)
    contract.updated_at = now
    return contract
