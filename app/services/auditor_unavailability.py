"""심사원 불가일정 → AuditorScheduleBlock / 배정 충돌 검사."""
from __future__ import annotations

from datetime import date
from typing import Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.auditor import AuditorUnavailability
from app.schemas.ea_auditor import AuditorScheduleBlock


def load_unavailability_schedules(
    db: Session,
    auditor_ids: Sequence[int],
    *,
    range_start: Optional[date] = None,
    range_end: Optional[date] = None,
) -> List[AuditorScheduleBlock]:
    """auditor_unavailability → filter_candidate_auditors용 스케줄 블록."""
    ids = sorted({int(i) for i in auditor_ids if i})
    if not ids:
        return []
    q = db.query(AuditorUnavailability).filter(AuditorUnavailability.auditor_id.in_(ids))
    if range_start is not None:
        q = q.filter(AuditorUnavailability.end_date >= range_start)
    if range_end is not None:
        q = q.filter(AuditorUnavailability.start_date <= range_end)
    rows = q.all()
    out: List[AuditorScheduleBlock] = []
    for r in rows:
        out.append(
            AuditorScheduleBlock(
                auditorId=str(r.auditor_id),
                startDate=r.start_date.isoformat(),
                endDate=r.end_date.isoformat(),
            )
        )
    return out


def find_unavailability_conflicts(
    db: Session,
    *,
    auditor_ids: Iterable[int],
    audit_start: date,
    audit_end: date,
) -> List[AuditorUnavailability]:
    """배정 기간과 겹치는 불가일정 행."""
    ids = sorted({int(i) for i in auditor_ids if i})
    if not ids:
        return []
    return (
        db.query(AuditorUnavailability)
        .filter(
            AuditorUnavailability.auditor_id.in_(ids),
            AuditorUnavailability.start_date <= audit_end,
            AuditorUnavailability.end_date >= audit_start,
        )
        .order_by(AuditorUnavailability.auditor_id.asc(), AuditorUnavailability.start_date.asc())
        .all()
    )
