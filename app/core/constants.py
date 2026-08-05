"""앱 공통 상수."""
from enum import Enum
from typing import Optional, Union


class MembershipStatus(str, Enum):
    """users.membership_status — 소속(CB/기업) 승인 상태."""

    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


class AuditorGrade(str, Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"


AUDITOR_GRADE_MAP = {
    AuditorGrade.TRAINEE: "심사원보",
    AuditorGrade.AUDITOR: "심사원",
    AuditorGrade.LEAD_AUDITOR: "선임심사원",
    AuditorGrade.VERIFIED_AUDITOR: "검증심사원",
}

# 레거시 코드 표시용 (DB 마이그레이션 이전 값 호환)
_LEGACY_GRADE_LABELS = {
    "senior": AUDITOR_GRADE_MAP[AuditorGrade.LEAD_AUDITOR],
    "verifier": AUDITOR_GRADE_MAP[AuditorGrade.VERIFIED_AUDITOR],
    "검증원": AUDITOR_GRADE_MAP[AuditorGrade.VERIFIED_AUDITOR],
    "검증심사원": AUDITOR_GRADE_MAP[AuditorGrade.VERIFIED_AUDITOR],
    "선임심사원": AUDITOR_GRADE_MAP[AuditorGrade.LEAD_AUDITOR],
}


def auditor_grade_label(grade: Optional[Union[str, AuditorGrade]]) -> str:
    """등급 코드를 한글 표기로 변환."""
    if grade is None or grade == "":
        return "-"
    if isinstance(grade, AuditorGrade):
        return AUDITOR_GRADE_MAP.get(grade, grade.value)
    if grade in _LEGACY_GRADE_LABELS:
        return _LEGACY_GRADE_LABELS[grade]
    try:
        return AUDITOR_GRADE_MAP[AuditorGrade(grade)]
    except ValueError:
        return str(grade)
