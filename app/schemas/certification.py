"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CertificatesStatus, CertificationApplicationsApplicationType, CertificationApplicationsAuditMode, CertificationApplicationsStatus


class CertificatesBase(BaseModel):
    contract_id: int
    company_id: int
    cert_no: Optional[str] = None
    standards: str
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    issued_at: Optional[date] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    issued_by: int
    status: CertificatesStatus
    created_at: datetime
    updated_at: datetime


class CertificatesCreate(CertificatesBase):
    pass


class CertificatesUpdate(BaseModel):
    contract_id: Optional[int] = None
    company_id: Optional[int] = None
    cert_no: Optional[str] = None
    standards: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    issued_at: Optional[date] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    issued_by: Optional[int] = None
    status: Optional[CertificatesStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CertificatesResponse(CertificatesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CertificationApplicationAnswersBase(BaseModel):
    application_id: int
    standard_code: str
    question_key: str
    answer_value: Optional[str] = None
    answer_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CertificationApplicationAnswersCreate(CertificationApplicationAnswersBase):
    pass


class CertificationApplicationAnswersUpdate(BaseModel):
    application_id: Optional[int] = None
    standard_code: Optional[str] = None
    question_key: Optional[str] = None
    answer_value: Optional[str] = None
    answer_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CertificationApplicationAnswersResponse(CertificationApplicationAnswersBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CertificationApplicationReviewLogsBase(BaseModel):
    application_id: int
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: str
    before_status: Optional[str] = None
    after_status: Optional[str] = None
    memo: Optional[str] = None
    created_at: datetime


class CertificationApplicationReviewLogsCreate(CertificationApplicationReviewLogsBase):
    pass


class CertificationApplicationReviewLogsUpdate(BaseModel):
    application_id: Optional[int] = None
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    action: Optional[str] = None
    before_status: Optional[str] = None
    after_status: Optional[str] = None
    memo: Optional[str] = None
    created_at: Optional[datetime] = None


class CertificationApplicationReviewLogsResponse(CertificationApplicationReviewLogsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CertificationApplicationSitesBase(BaseModel):
    application_id: int
    site_no: int
    site_name: Optional[str] = None
    address_kr: Optional[str] = None
    address_en: Optional[str] = None
    work_type: Optional[str] = None
    regular_count: int
    irregular_count: int
    total_count: int
    checked: int
    created_at: datetime
    updated_at: datetime


class CertificationApplicationSitesCreate(CertificationApplicationSitesBase):
    pass


class CertificationApplicationSitesUpdate(BaseModel):
    application_id: Optional[int] = None
    site_no: Optional[int] = None
    site_name: Optional[str] = None
    address_kr: Optional[str] = None
    address_en: Optional[str] = None
    work_type: Optional[str] = None
    regular_count: Optional[int] = None
    irregular_count: Optional[int] = None
    total_count: Optional[int] = None
    checked: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CertificationApplicationSitesResponse(CertificationApplicationSitesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CertificationApplicationsBase(BaseModel):
    application_no: str
    company_id: int
    applicant_user_id: Optional[int] = None
    cb_id: Optional[int] = None
    contract_id: Optional[int] = None
    application_type: CertificationApplicationsApplicationType
    status: CertificationApplicationsStatus
    standards_json: Optional[str] = None
    standard_audit_types_json: Optional[str] = None
    iaf_codes_json: Optional[str] = None
    questionnaire_json: Optional[str] = None
    company_snapshot_json: Optional[str] = None
    integrated_check_json: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    ksic_code: Optional[str] = None
    employee_count: int
    regular_count: int
    irregular_count: int
    total_count: int
    work_type: Optional[str] = None
    desired_audit_start: Optional[date] = None
    desired_audit_end: Optional[date] = None
    site_count: int
    note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audit_mode: CertificationApplicationsAuditMode


class CertificationApplicationsCreate(CertificationApplicationsBase):
    pass


class CertificationApplicationsUpdate(BaseModel):
    application_no: Optional[str] = None
    company_id: Optional[int] = None
    applicant_user_id: Optional[int] = None
    cb_id: Optional[int] = None
    contract_id: Optional[int] = None
    application_type: Optional[CertificationApplicationsApplicationType] = None
    status: Optional[CertificationApplicationsStatus] = None
    standards_json: Optional[str] = None
    standard_audit_types_json: Optional[str] = None
    iaf_codes_json: Optional[str] = None
    questionnaire_json: Optional[str] = None
    company_snapshot_json: Optional[str] = None
    integrated_check_json: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    ksic_code: Optional[str] = None
    employee_count: Optional[int] = None
    regular_count: Optional[int] = None
    irregular_count: Optional[int] = None
    total_count: Optional[int] = None
    work_type: Optional[str] = None
    desired_audit_start: Optional[date] = None
    desired_audit_end: Optional[date] = None
    site_count: Optional[int] = None
    note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    audit_mode: Optional[CertificationApplicationsAuditMode] = None


class CertificationApplicationsResponse(CertificationApplicationsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
