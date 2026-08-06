"""EA 코드 · 배정용 심사원 자격 프로필 DTO (FE types/auditor.ts).

레거시 CRUD 스키마는 ``app.schemas.auditor_profile`` 에 유지한다.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

StandardCode = Literal[
    "COMMON",
    "IMS",
    "QMS",
    "EMS",
    "OHSMS",
    "ISMS",
    "ABMS",
    "CMS",
    "EnMS",
    "FSMS",
    "MDQMS",
    "NSMS",
    "PIMS",
    "AIMS",
]

AuditorGrade = Literal["LEAD_AUDITOR", "AUDITOR", "TECHNICAL_EXPERT"]
IndustryRiskCategory = Literal["HIGH", "MEDIUM", "LOW"]


class EACodeMaster(BaseModel):
    code: str = Field(..., description="e.g. EA_14")
    name_ko: str = Field(..., alias="nameKo")
    risk_category: IndustryRiskCategory = Field(..., alias="riskCategory")

    class Config:
        populate_by_name = True


class AuditorQualification(BaseModel):
    standard_code: StandardCode = Field(..., alias="standardCode")
    grade: AuditorGrade
    authorized_ea_codes: List[str] = Field(
        default_factory=list, alias="authorizedEACodes"
    )
    issue_date: str = Field(..., alias="issueDate")
    expiry_date: str = Field(..., alias="expiryDate")

    class Config:
        populate_by_name = True


class AssignmentAuditorProfile(BaseModel):
    """배정·COI 검증용 심사원 프로필 (FE AuditorProfile)."""

    id: str
    name: str
    email: str
    phone: str
    qualifications: List[AuditorQualification] = Field(default_factory=list)
    restricted_company_ids: List[str] = Field(
        default_factory=list, alias="restrictedCompanyIds"
    )
    max_daily_capacity_md: float = Field(..., alias="maxDailyCapacityMD")
    is_active: bool = Field(True, alias="isActive")

    class Config:
        populate_by_name = True


# FE 명칭 호환 alias
AuditorProfile = AssignmentAuditorProfile


class AllocationRequirement(BaseModel):
    company_id: str = Field(..., alias="companyId")
    standard_code: StandardCode = Field(..., alias="standardCode")
    company_ea_code: str = Field(..., alias="companyEACode")
    audit_start_date: str = Field(..., alias="auditStartDate")
    audit_end_date: str = Field(..., alias="auditEndDate")
    required_md: float = Field(..., alias="requiredMD")

    class Config:
        populate_by_name = True


class AuditorScheduleBlock(BaseModel):
    auditor_id: str = Field(..., alias="auditorId")
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")

    class Config:
        populate_by_name = True


class CandidateAuditorResult(BaseModel):
    auditor: AssignmentAuditorProfile
    is_qualified: bool = Field(..., alias="isQualified")
    qualification_grade: Optional[AuditorGrade] = Field(
        None, alias="qualificationGrade"
    )
    coi_passed: bool = Field(..., alias="coiPassed")
    schedule_passed: bool = Field(..., alias="schedulePassed")
    rejection_reason: Optional[str] = Field(None, alias="rejectionReason")

    class Config:
        populate_by_name = True


class FilterCandidatesRequest(BaseModel):
    requirement: AllocationRequirement
    auditors: List[AssignmentAuditorProfile]
    existing_schedules: List[AuditorScheduleBlock] = Field(
        default_factory=list, alias="existingSchedules"
    )

    class Config:
        populate_by_name = True
