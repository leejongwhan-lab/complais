"""Auditor profile / detail DTO schemas (학력·경력·자격 포함)."""
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EducationSchema(BaseModel):
    id: Optional[int] = None
    school_name: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    entered_at: Optional[date] = None
    graduated_at: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


class WorkExperienceSchema(BaseModel):
    id: Optional[int] = None
    company_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = False
    work_years: Optional[float] = 0.0
    note: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ConsultingExperienceSchema(BaseModel):
    id: Optional[int] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    standard_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    note: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class ExternalCertSchema(BaseModel):
    id: Optional[int] = None
    cert_name: Optional[str] = None
    issuer: Optional[str] = None
    cert_no: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorDetailResponse(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None

    complais_no: Optional[str] = None
    registration_no: Optional[str] = None
    auditor_no: Optional[str] = None

    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    status: Optional[str] = None
    profile_status: Optional[str] = None

    daily_rate: Optional[float] = None
    fee_ratio: Optional[float] = None
    monthly_fee: Optional[float] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None

    educations: List[EducationSchema] = Field(default_factory=list)
    careers: List[WorkExperienceSchema] = Field(default_factory=list)
    consultings: List[ConsultingExperienceSchema] = Field(default_factory=list)
    external_certs: List[ExternalCertSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
