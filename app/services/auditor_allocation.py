"""규격/EA/COI/일정 종합 검증 — FE filterCandidateAuditors 1:1."""
from __future__ import annotations

from typing import List, Sequence

from app.schemas.ea_auditor import (
    AllocationRequirement,
    AssignmentAuditorProfile,
    AuditorScheduleBlock,
    CandidateAuditorResult,
)


def _dates_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    return not (end_a < start_b or start_a > end_b)


def filter_candidate_auditors(
    req: AllocationRequirement,
    all_auditors: Sequence[AssignmentAuditorProfile],
    existing_schedules: Sequence[AuditorScheduleBlock],
) -> List[CandidateAuditorResult]:
    results: List[CandidateAuditorResult] = []
    for auditor in all_auditors:
        qual = next(
            (
                q
                for q in auditor.qualifications
                if q.standard_code == req.standard_code
                and req.company_ea_code in q.authorized_ea_codes
            ),
            None,
        )
        if qual is None:
            results.append(
                CandidateAuditorResult(
                    auditor=auditor,
                    isQualified=False,
                    coiPassed=False,
                    schedulePassed=False,
                    rejectionReason=(
                        f"규격({req.standard_code}) 또는 "
                        f"EA코드({req.company_ea_code}) 심사 자격 미보유"
                    ),
                )
            )
            continue

        if req.company_id in auditor.restricted_company_ids:
            results.append(
                CandidateAuditorResult(
                    auditor=auditor,
                    isQualified=True,
                    qualificationGrade=qual.grade,
                    coiPassed=False,
                    schedulePassed=False,
                    rejectionReason=(
                        "해당 기업에 대한 이해상충(COI) 제약 존재 "
                        "(최근 컨설팅 이력 등)"
                    ),
                )
            )
            continue

        has_conflict = any(
            sch.auditor_id == auditor.id
            and _dates_overlap(
                req.audit_start_date,
                req.audit_end_date,
                sch.start_date,
                sch.end_date,
            )
            for sch in existing_schedules
        )
        if has_conflict:
            results.append(
                CandidateAuditorResult(
                    auditor=auditor,
                    isQualified=True,
                    qualificationGrade=qual.grade,
                    coiPassed=True,
                    schedulePassed=False,
                    rejectionReason="해당 심사 기간 내 타 심사 일정 중복",
                )
            )
            continue

        results.append(
            CandidateAuditorResult(
                auditor=auditor,
                isQualified=True,
                qualificationGrade=qual.grade,
                coiPassed=True,
                schedulePassed=True,
            )
        )
    return results


def eligible_candidates(
    req: AllocationRequirement,
    all_auditors: Sequence[AssignmentAuditorProfile],
    existing_schedules: Sequence[AuditorScheduleBlock],
) -> List[CandidateAuditorResult]:
    return [
        r
        for r in filter_candidate_auditors(req, all_auditors, existing_schedules)
        if r.is_qualified and r.coi_passed and r.schedule_passed
    ]
