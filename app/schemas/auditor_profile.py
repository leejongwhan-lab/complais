"""Auditor profile / detail DTO schemas (학력·경력·자격 포함)."""
from datetime import date, datetime
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


class AuditorProfileBase(BaseModel):
    """실제 라이브 `auditors` 테이블 컬럼과 1:1로 맞춘 심사원 마스터 CRUD 스키마."""
    name: str
    name_en: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    primary_cb_id: Optional[int] = None
    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    registration_no: Optional[str] = None
    iaf_codes: Optional[str] = None
    is_active: Optional[bool] = True
    status: Optional[str] = Field(default="활성", description="활성/휴면/정지")
    profile_status: Optional[str] = None
    contract_type: Optional[str] = None
    daily_rate: Optional[float] = None
    fee_ratio: Optional[float] = None
    monthly_fee: Optional[float] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    intro: Optional[str] = None
    rrn_hash: Optional[str] = Field(default=None, description="주민등록번호 암호화 Hash")
    income_type: Optional[str] = Field(default=None, description="3.3% 사업소득/기타소득/법인사업자")
    education_level: Optional[str] = None
    school_name: Optional[str] = None
    major: Optional[str] = None
    career_summary: Optional[str] = None
    total_working_days: Optional[int] = None
    cb_affiliation: Optional[str] = None
    commission_type: Optional[str] = Field(default=None, description="퍼센트/건별")
    security_pledge_agreed: Optional[bool] = False
    subcontract_agreed: Optional[bool] = False


class AuditorProfileCreate(AuditorProfileBase):
    pass


class AuditorProfileUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    primary_cb_id: Optional[int] = None
    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    registration_no: Optional[str] = None
    iaf_codes: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    profile_status: Optional[str] = None
    contract_type: Optional[str] = None
    daily_rate: Optional[float] = None
    fee_ratio: Optional[float] = None
    monthly_fee: Optional[float] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    intro: Optional[str] = None
    rrn_hash: Optional[str] = None
    income_type: Optional[str] = None
    education_level: Optional[str] = None
    school_name: Optional[str] = None
    major: Optional[str] = None
    career_summary: Optional[str] = None
    total_working_days: Optional[int] = None
    cb_affiliation: Optional[str] = None
    commission_type: Optional[str] = None
    security_pledge_agreed: Optional[bool] = None
    subcontract_agreed: Optional[bool] = None


class AuditorProfileResponse(AuditorProfileBase):
    id: int
    complais_no: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
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
