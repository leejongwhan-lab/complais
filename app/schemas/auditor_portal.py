"""Auditor portal dashboard / panel DTOs."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AuditorKpiBlock(BaseModel):
    scheduled_this_month: int = 0
    draft_reports: int = 0
    ncr_review_pending: int = 0
    affiliation_status: str = "미등록"
    affiliation_detail: Optional[str] = None
    approved_cb_count: int = 0
    nearest_qual_expiry: Optional[date] = None
    nearest_qual_dday: Optional[int] = None


class AuditorScheduleItem(BaseModel):
    assignment_id: Optional[int] = None
    contract_id: Optional[int] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    standards: List[str] = Field(default_factory=list)
    standards_label: str = ""
    audit_type: Optional[str] = None
    audit_type_label: Optional[str] = None
    audit_mode: Optional[str] = None
    audit_mode_label: Optional[str] = None
    audit_date: Optional[date] = None
    audit_period_end: Optional[date] = None
    status: Optional[str] = None
    status_label: Optional[str] = None
    role: Optional[str] = None
    team_members: List[str] = Field(default_factory=list)
    team_label: str = ""
    company_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None


class AuditorNcrItem(BaseModel):
    id: int
    contract_id: Optional[int] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    clause_id: Optional[str] = None
    std_code: Optional[str] = None
    std_label: Optional[str] = None
    grade: Optional[str] = None
    status: Optional[str] = None
    status_label: Optional[str] = None
    due_date: Optional[date] = None
    ca_submitted_at: Optional[datetime] = None
    finding: Optional[str] = None


class AuditorReportItem(BaseModel):
    id: int
    contract_id: Optional[int] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    report_no: Optional[str] = None
    report_type: Optional[str] = None
    status: Optional[str] = None
    status_label: Optional[str] = None
    updated_at: Optional[datetime] = None


class AuditorQualItem(BaseModel):
    id: int
    standard_code: Optional[str] = None
    standard_label: Optional[str] = None
    grade: Optional[str] = None
    cert_body_name: Optional[str] = None
    cert_no: Optional[str] = None
    expires_at: Optional[date] = None
    dday: Optional[int] = None
    is_active: bool = False
    iaf_codes: Optional[str] = None
    major_name: Optional[str] = None


class AuditorMembershipItem(BaseModel):
    id: int
    cb_id: int
    cb_name: Optional[str] = None
    cb_code: Optional[str] = None
    status: str
    status_label: Optional[str] = None
    apply_grade: Optional[str] = None
    approved_grade: Optional[str] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    employment_type: Optional[str] = None
    kar_no: Optional[str] = None
    qualification_expires_at: Optional[date] = None
    qual_dday: Optional[int] = None
    is_primary: bool = False


class AuditorEducationItem(BaseModel):
    id: int
    school_name: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    entered_at: Optional[date] = None
    graduated_at: Optional[date] = None


class AuditorCareerItem(BaseModel):
    id: int
    company_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    iaf_code: Optional[str] = None
    ksic_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    duties: Optional[str] = None


class AuditorExternalCertItem(BaseModel):
    id: int
    cert_name: Optional[str] = None
    issuer: Optional[str] = None
    cert_no: Optional[str] = None
    grade: Optional[str] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None


class AuditorProfileSummary(BaseModel):
    """마이페이지 / 자격·소속 — DB에 있는 본인 프로필만."""
    auditor_id: int
    name: Optional[str] = None
    name_en: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    complais_no: Optional[str] = None
    registration_no: Optional[str] = None
    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    status: Optional[str] = None
    profile_status: Optional[str] = None
    iaf_codes: Optional[str] = None
    education_level: Optional[str] = None
    school_name: Optional[str] = None
    major: Optional[str] = None
    career_summary: Optional[str] = None
    cb_affiliation: Optional[str] = None
    primary_cb_id: Optional[int] = None
    primary_cb_name: Optional[str] = None
    has_ci: bool = False
    memberships: List[AuditorMembershipItem] = Field(default_factory=list)
    qualifications: List[AuditorQualItem] = Field(default_factory=list)
    educations: List[AuditorEducationItem] = Field(default_factory=list)
    careers: List[AuditorCareerItem] = Field(default_factory=list)
    external_certs: List[AuditorExternalCertItem] = Field(default_factory=list)


class AuditorDashboardSummary(BaseModel):
    auditor_id: Optional[int] = None
    auditor_name: Optional[str] = None
    kpis: AuditorKpiBlock = Field(default_factory=AuditorKpiBlock)
    schedules: List[AuditorScheduleItem] = Field(default_factory=list)
    ncrs_pending: List[AuditorNcrItem] = Field(default_factory=list)
    draft_reports: List[AuditorReportItem] = Field(default_factory=list)
    memberships: List[AuditorMembershipItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
