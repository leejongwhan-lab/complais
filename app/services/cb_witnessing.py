"""Witness Assessment (KAB-AR-MD17 / IAF MD 17) business logic."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy.orm import Session

from app.data.standards_catalog import format_standard_label, to_family_initial
from app.models.certification_body import CbStandardAccreditation
from app.models.witnessing import (
    TechnicalCluster,
    WitnessingCode,
    WitnessingIafTemplate,
    WitnessingScheme,
)

STATUS_OK = "정상"
STATUS_DUE = "임박"
STATUS_EXPIRED = "만료"
STATUS_MISSING = "미입력"
DUE_SOON_DAYS = 90


def scheme_label(scheme: WitnessingScheme) -> str:
    """이니셜 · ISO ####:#### · ○○경영시스템"""
    raw = scheme.iso_ref or scheme.code
    try:
        return format_standard_label(raw) or format_standard_label(scheme.code) or (
            f"{scheme.code} · {scheme.iso_ref or ''} · {scheme.name_kr}".strip(" ·")
        )
    except Exception:
        return f"{scheme.code} · {scheme.iso_ref or ''} · {scheme.name_kr}".strip(" ·")


def compute_status(
    last_witness_date: Optional[date],
    next_due_date: Optional[date],
    today: Optional[date] = None,
) -> str:
    today = today or date.today()
    if last_witness_date is None:
        return STATUS_MISSING
    due = next_due_date
    if due is None:
        return STATUS_MISSING
    if due < today:
        return STATUS_EXPIRED
    if due <= today + timedelta(days=DUE_SOON_DAYS):
        return STATUS_DUE
    return STATUS_OK


def next_due_from(last: date, cycle_years: int) -> date:
    years = max(1, int(cycle_years or 5))
    try:
        return last.replace(year=last.year + years)
    except ValueError:
        # Feb 29 → Feb 28
        return last.replace(month=2, day=28, year=last.year + years)


def cb_accredited_scheme_codes(db: Session, cb_id: int) -> List[str]:
    rows = (
        db.query(CbStandardAccreditation)
        .filter(
            CbStandardAccreditation.cb_id == cb_id,
            CbStandardAccreditation.is_active.is_(True),
        )
        .all()
    )
    codes: List[str] = []
    seen: Set[str] = set()
    for r in rows:
        fam = to_family_initial(r.standard_code)
        if fam and fam not in seen:
            seen.add(fam)
            codes.append(fam)
    if not codes:
        # Fallback: all active schemes so empty CB still sees UI
        for s in (
            db.query(WitnessingScheme)
            .filter(WitnessingScheme.is_active.is_(True))
            .order_by(WitnessingScheme.sort_order)
            .all()
        ):
            codes.append(s.code)
    return codes


def ensure_cb_codes(db: Session, cb_id: int, scheme: WitnessingScheme) -> int:
    """Copy templates into witnessing_codes for this CB×scheme. Returns inserted count."""
    existing = {
        r.iaf_code
        for r in db.query(WitnessingCode.iaf_code)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.scheme_id == scheme.id,
        )
        .all()
    }
    templates = (
        db.query(WitnessingIafTemplate)
        .filter(WitnessingIafTemplate.scheme_id == scheme.id)
        .all()
    )
    inserted = 0
    for t in templates:
        if t.iaf_code in existing:
            continue
        is_crit = bool(t.is_critical)
        eligible = False if is_crit else bool(t.eligible_for_coverage)
        db.add(
            WitnessingCode(
                cb_id=cb_id,
                scheme_id=scheme.id,
                cluster_id=t.cluster_id if scheme.has_cluster_logic else None,
                iaf_code=t.iaf_code,
                description=t.description,
                is_critical=is_crit,
                eligible_for_coverage=eligible,
                cycle_years=t.cycle_years or scheme.cycle_years_default or 5,
                last_witness_date=None,
                next_due_date=None,
                is_auto=False,
                updated_at=datetime.utcnow(),
            )
        )
        inserted += 1
    if inserted:
        db.flush()
    return inserted


def cluster_name_map(db: Session, scheme_id: int) -> Dict[int, str]:
    rows = (
        db.query(TechnicalCluster)
        .filter(TechnicalCluster.scheme_id == scheme_id)
        .all()
    )
    return {r.id: r.name_kr for r in rows}


def criticals_ok_for_cluster(
    codes: Sequence[WitnessingCode],
    cluster_id: int,
    today: Optional[date] = None,
) -> bool:
    """ALL critical codes in cluster must be 정상 or 임박 (not 만료/미입력)."""
    crits = [
        c
        for c in codes
        if c.cluster_id == cluster_id and bool(c.is_critical)
    ]
    if not crits:
        return False
    for c in crits:
        st = compute_status(c.last_witness_date, c.next_due_date, today)
        if st in (STATUS_EXPIRED, STATUS_MISSING):
            return False
    return True


def apply_complete(
    row: WitnessingCode,
    witness_date: date,
    *,
    is_auto: bool = False,
) -> None:
    row.last_witness_date = witness_date
    row.next_due_date = next_due_from(witness_date, row.cycle_years or 5)
    row.is_auto = bool(is_auto)
    row.updated_at = datetime.utcnow()


def auto_propagate_cluster(
    db: Session,
    cb_id: int,
    scheme: WitnessingScheme,
    source: WitnessingCode,
    witness_date: date,
    today: Optional[date] = None,
) -> List[int]:
    """Propagate to non-critical eligible codes in same cluster when conditions met."""
    if not scheme.has_cluster_logic or not source.cluster_id:
        return []
    today = today or date.today()
    all_codes = (
        db.query(WitnessingCode)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.scheme_id == scheme.id,
            WitnessingCode.cluster_id == source.cluster_id,
        )
        .all()
    )
    # Re-evaluate after source update (caller should have flushed source)
    if not criticals_ok_for_cluster(all_codes, source.cluster_id, today):
        return []
    propagated: List[int] = []
    for c in all_codes:
        if c.id == source.id:
            continue
        if bool(c.is_critical):
            continue
        if not bool(c.eligible_for_coverage):
            continue
        apply_complete(c, witness_date, is_auto=True)
        propagated.append(c.id)
    return propagated


def find_same_iaf_other_schemes(
    db: Session,
    cb_id: int,
    iaf_code: str,
    exclude_scheme_id: int,
) -> List[WitnessingCode]:
    return (
        db.query(WitnessingCode)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.iaf_code == iaf_code,
            WitnessingCode.scheme_id != exclude_scheme_id,
        )
        .all()
    )
