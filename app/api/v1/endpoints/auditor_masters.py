"""EA 코드 · 심사원 프로필 조회 API (마스터 DTO)."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.data.ea_codes_catalog import DEFAULT_EA_CODE_MASTERS
from app.schemas.ea_auditor import (
    CandidateAuditorResult,
    EACodeMaster,
    FilterCandidatesRequest,
)
from app.services.auditor_allocation import filter_candidate_auditors
from app.services.auditor_unavailability import load_unavailability_schedules

router = APIRouter(prefix="/auditor-masters", tags=["Auditor Masters"])


@router.get("/ea-codes", response_model=List[EACodeMaster])
def list_ea_codes(
    risk: Optional[str] = Query(None, description="HIGH|MEDIUM|LOW"),
    db: Session = Depends(get_db),
):
    """대표 EA 코드 목록. DB iaf_codes 가 있으면 병합 확장 가능(현재 카탈로그)."""
    _ = db
    rows = DEFAULT_EA_CODE_MASTERS
    if risk:
        rows = [r for r in rows if r.risk_category == risk.upper()]
    return [
        EACodeMaster.model_validate(
            {
                "code": r.code,
                "nameKo": r.name_ko,
                "riskCategory": r.risk_category,
            }
        )
        for r in rows
    ]


@router.post("/filter-candidates", response_model=List[CandidateAuditorResult])
def post_filter_candidates(
    payload: FilterCandidatesRequest,
    db: Session = Depends(get_db),
):
    """규격/EA/COI/일정 종합 검증 — 후보 평가 목록 반환.

    payload.existing_schedules 에 더해 DB auditor_unavailability 를 자동 병합한다.
    """
    auditor_ids: List[int] = []
    for a in payload.auditors or []:
        try:
            auditor_ids.append(int(a.id))
        except (TypeError, ValueError):
            continue
    range_start = range_end = None
    try:
        range_start = date.fromisoformat(payload.requirement.audit_start_date)
        range_end = date.fromisoformat(payload.requirement.audit_end_date)
    except Exception:
        pass
    db_schedules = load_unavailability_schedules(
        db, auditor_ids, range_start=range_start, range_end=range_end
    )
    # client 제공 스케줄 + DB 불가일정 병합 (auditorId는 str)
    seen = {
        (s.auditor_id, s.start_date, s.end_date) for s in (payload.existing_schedules or [])
    }
    merged = list(payload.existing_schedules or [])
    for s in db_schedules:
        key = (s.auditor_id, s.start_date, s.end_date)
        if key not in seen:
            merged.append(s)
            seen.add(key)
    return filter_candidate_auditors(
        payload.requirement,
        payload.auditors,
        merged,
    )
