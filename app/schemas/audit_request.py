"""인증 신청(audit_requests) 설문/심사주기 Pydantic 스키마."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SurveyResponses(BaseModel):
    """공통 + 표준별 설문 응답. 추가 키 허용."""

    model_config = ConfigDict(extra="allow")

    common: Dict[str, Any] = Field(default_factory=dict)


class AuditRequestCreate(BaseModel):
    cb_id: int
    iso_standards: List[str] = Field(..., min_length=1)
    audit_type: str = Field(default="surveillance", description="initial|surveillance|recertification|special")
    audit_cycle_months: int = Field(default=12, description="6 또는 12")
    previous_request_id: Optional[int] = None
    survey_responses: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = None
    preferred_start_date: Optional[date] = None

    @field_validator("audit_cycle_months")
    @classmethod
    def validate_cycle(cls, v: int) -> int:
        if v not in (6, 12):
            raise ValueError("audit_cycle_months는 6 또는 12만 가능합니다.")
        return v

    @field_validator("iso_standards")
    @classmethod
    def validate_standards(cls, v: List[str]) -> List[str]:
        cleaned = [s.strip() for s in v if s and str(s).strip()]
        if not cleaned:
            raise ValueError("iso_standards는 1개 이상 필요합니다.")
        return cleaned


class AuditRequestOut(BaseModel):
    id: int
    company_id: int
    cb_id: int
    applicant_user_id: Optional[int] = None
    iso_standards: List[str] = Field(default_factory=list)
    audit_type: str
    audit_cycle_months: int
    survey_responses: Optional[Dict[str, Any]] = None
    previous_request_id: Optional[int] = None
    status: str
    application_no: Optional[str] = None
    preferred_start_date: Optional[date] = None
    process_step: int = 1
    note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LatestSurveyOut(BaseModel):
    """직전 차수 설문 Prefill용."""

    has_previous: bool = False
    request_id: Optional[int] = None
    previous_request_id: Optional[int] = None
    audit_cycle_months: int = 12
    audit_type: Optional[str] = None
    iso_standards: List[str] = Field(default_factory=list)
    survey_responses: Dict[str, Any] = Field(default_factory=dict)
    cb_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    message: Optional[str] = None
