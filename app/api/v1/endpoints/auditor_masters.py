"""EA 코드 · 심사원 프로필 조회 API (마스터 DTO)."""
from __future__ import annotations

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
def post_filter_candidates(payload: FilterCandidatesRequest):
    """규격/EA/COI/일정 종합 검증 — 후보 평가 목록 반환."""
    return filter_candidate_auditors(
        payload.requirement,
        payload.auditors,
        payload.existing_schedules,
    )
