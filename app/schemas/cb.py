"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CbAccreditationsStatus, CbApprovalLinesApprovalType, CbApprovalLinesConditionType, CbFeePolicyAuditType, CbFeePolicyFeeMethod, CbNoticesPriority, CbNoticesTarget, CbProposalApprovalsApprovalType, CbProposalApprovalsStatus, CbProposalNegotiationsSenderType, CbProposalTeamRole, CbProposalsApprovalStatus, CertificationBodiesCbType


class CbAccreditationChangeRequestsBase(BaseModel):
    cb_id: int
    request_kind: str
    target_scope_id: Optional[int] = None
    accreditation: Optional[str] = None
    reg_no: Optional[str] = None
    standard_code: Optional[str] = None
    standard_name: Optional[str] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = Field(default=None, description="ISO 13485 기술영역")
    nace_code: Optional[str] = None
    use_nace: int
    is_active: bool
    cert_file_path: Optional[str] = None
    cert_file_name: Optional[str] = None
    note: Optional[str] = None
    status: str
    requested_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CbAccreditationChangeRequestsCreate(CbAccreditationChangeRequestsBase):
    pass


class CbAccreditationChangeRequestsUpdate(BaseModel):
    cb_id: Optional[int] = None
    request_kind: Optional[str] = None
    target_scope_id: Optional[int] = None
    accreditation: Optional[str] = None
    reg_no: Optional[str] = None
    standard_code: Optional[str] = None
    standard_name: Optional[str] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = None
    nace_code: Optional[str] = None
    use_nace: Optional[int] = None
    is_active: Optional[bool] = None
    cert_file_path: Optional[str] = None
    cert_file_name: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None
    requested_by: Optional[int] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CbAccreditationChangeRequestsResponse(CbAccreditationChangeRequestsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbAccreditationScopesBase(BaseModel):
    cb_id: int
    standard_code: str
    standard_name: Optional[str] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = Field(default=None, description="ISO 13485 기술영역 코드 (A.1.1,A.1.2 등)")
    nace_code: Optional[str] = None
    use_nace: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CbAccreditationScopesCreate(CbAccreditationScopesBase):
    pass


class CbAccreditationScopesUpdate(BaseModel):
    cb_id: Optional[int] = None
    standard_code: Optional[str] = None
    standard_name: Optional[str] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = None
    nace_code: Optional[str] = None
    use_nace: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CbAccreditationScopesResponse(CbAccreditationScopesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbAccreditationsBase(BaseModel):
    cb_id: int
    body_id: int
    accred_no: Optional[str] = None
    standards: Optional[str] = None
    status: Optional[CbAccreditationsStatus] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    created_at: Optional[datetime] = None


class CbAccreditationsCreate(CbAccreditationsBase):
    pass


class CbAccreditationsUpdate(BaseModel):
    cb_id: Optional[int] = None
    body_id: Optional[int] = None
    accred_no: Optional[str] = None
    standards: Optional[str] = None
    status: Optional[CbAccreditationsStatus] = None
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    created_at: Optional[datetime] = None


class CbAccreditationsResponse(CbAccreditationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbApprovalLinesBase(BaseModel):
    cb_id: int
    step: int
    role: str
    approver_user_id: Optional[int] = None
    is_required: bool
    condition_type: CbApprovalLinesConditionType
    condition_value: Optional[Decimal] = None
    approval_type: CbApprovalLinesApprovalType
    created_at: datetime


class CbApprovalLinesCreate(CbApprovalLinesBase):
    pass


class CbApprovalLinesUpdate(BaseModel):
    cb_id: Optional[int] = None
    step: Optional[int] = None
    role: Optional[str] = None
    approver_user_id: Optional[int] = None
    is_required: Optional[bool] = None
    condition_type: Optional[CbApprovalLinesConditionType] = None
    condition_value: Optional[Decimal] = None
    approval_type: Optional[CbApprovalLinesApprovalType] = None
    created_at: Optional[datetime] = None


class CbApprovalLinesResponse(CbApprovalLinesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbFeePolicyBase(BaseModel):
    cb_id: int
    fee_method: CbFeePolicyFeeMethod
    audit_type: Optional[CbFeePolicyAuditType] = None
    standards_count: Optional[int] = None
    fee_amount: Optional[Decimal] = None
    marketing_pct: Optional[Decimal] = None
    auditor_pct: Optional[Decimal] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CbFeePolicyCreate(CbFeePolicyBase):
    pass


class CbFeePolicyUpdate(BaseModel):
    cb_id: Optional[int] = None
    fee_method: Optional[CbFeePolicyFeeMethod] = None
    audit_type: Optional[CbFeePolicyAuditType] = None
    standards_count: Optional[int] = None
    fee_amount: Optional[Decimal] = None
    marketing_pct: Optional[Decimal] = None
    auditor_pct: Optional[Decimal] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CbFeePolicyResponse(CbFeePolicyBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbNoticesBase(BaseModel):
    cb_id: int
    title: str
    content: Optional[str] = None
    target: CbNoticesTarget
    priority: CbNoticesPriority
    is_active: bool
    created_by: Optional[int] = None
    created_at: datetime


class CbNoticesCreate(CbNoticesBase):
    pass


class CbNoticesUpdate(BaseModel):
    cb_id: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    target: Optional[CbNoticesTarget] = None
    priority: Optional[CbNoticesPriority] = None
    is_active: Optional[bool] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None


class CbNoticesResponse(CbNoticesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbProposalApprovalsBase(BaseModel):
    proposal_id: int
    step: int
    approval_type: CbProposalApprovalsApprovalType
    approver_user_id: int
    status: CbProposalApprovalsStatus
    comment: Optional[str] = None
    acted_at: Optional[datetime] = None
    created_at: datetime


class CbProposalApprovalsCreate(CbProposalApprovalsBase):
    pass


class CbProposalApprovalsUpdate(BaseModel):
    proposal_id: Optional[int] = None
    step: Optional[int] = None
    approval_type: Optional[CbProposalApprovalsApprovalType] = None
    approver_user_id: Optional[int] = None
    status: Optional[CbProposalApprovalsStatus] = None
    comment: Optional[str] = None
    acted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class CbProposalApprovalsResponse(CbProposalApprovalsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbProposalNegotiationsBase(BaseModel):
    proposal_id: int
    sender_type: CbProposalNegotiationsSenderType
    sender_id: int
    comment: str
    created_at: datetime


class CbProposalNegotiationsCreate(CbProposalNegotiationsBase):
    pass


class CbProposalNegotiationsUpdate(BaseModel):
    proposal_id: Optional[int] = None
    sender_type: Optional[CbProposalNegotiationsSenderType] = None
    sender_id: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class CbProposalNegotiationsResponse(CbProposalNegotiationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbProposalTeamBase(BaseModel):
    proposal_id: int
    auditor_id: Optional[int] = None
    role: CbProposalTeamRole
    stage: int = Field(description="0=전체,1=1단계,2=2단계")
    note: Optional[str] = None


class CbProposalTeamCreate(CbProposalTeamBase):
    pass


class CbProposalTeamUpdate(BaseModel):
    proposal_id: Optional[int] = None
    auditor_id: Optional[int] = None
    role: Optional[CbProposalTeamRole] = None
    stage: Optional[int] = None
    note: Optional[str] = None


class CbProposalTeamResponse(CbProposalTeamBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CbProposalsBase(BaseModel):
    doc_no: Optional[str] = None
    application_id: Optional[int] = None
    cb_id: int
    company_id: int
    audit_type: str
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    stage1_start: Optional[date] = None
    stage1_end: Optional[date] = None
    stage1_days: Optional[Decimal] = None
    stage2_start: Optional[date] = None
    stage2_end: Optional[date] = None
    stage2_days: Optional[Decimal] = None
    audit_days: Decimal
    auditor_note: Optional[str] = None
    auditor_id: Optional[int] = None
    fee_audit: int
    fee_travel: int
    fee_other: int
    fee_total: int
    audit_location: Optional[str] = None
    note: Optional[str] = None
    status: str
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    approval_status: CbProposalsApprovalStatus
    current_step: int
    created_by: Optional[int] = None
    fee_report: Optional[int] = None
    fee_application: Optional[int] = None
    standards_json: Optional[str] = None


class CbProposalsCreate(CbProposalsBase):
    pass


class CbProposalsUpdate(BaseModel):
    doc_no: Optional[str] = None
    application_id: Optional[int] = None
    cb_id: Optional[int] = None
    company_id: Optional[int] = None
    audit_type: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    stage1_start: Optional[date] = None
    stage1_end: Optional[date] = None
    stage1_days: Optional[Decimal] = None
    stage2_start: Optional[date] = None
    stage2_end: Optional[date] = None
    stage2_days: Optional[Decimal] = None
    audit_days: Optional[Decimal] = None
    auditor_note: Optional[str] = None
    auditor_id: Optional[int] = None
    fee_audit: Optional[int] = None
    fee_travel: Optional[int] = None
    fee_other: Optional[int] = None
    fee_total: Optional[int] = None
    audit_location: Optional[str] = None
    note: Optional[str] = None
    status: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    approval_status: Optional[CbProposalsApprovalStatus] = None
    current_step: Optional[int] = None
    created_by: Optional[int] = None
    fee_report: Optional[int] = None
    fee_application: Optional[int] = None
    standards_json: Optional[str] = None


class CbProposalsResponse(CbProposalsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbStdMdRatesBase(BaseModel):
    cb_id: int
    standard_code: str
    md_rate: int
    travel_rate: int
    updated_at: datetime


class CbStdMdRatesCreate(CbStdMdRatesBase):
    pass


class CbStdMdRatesUpdate(BaseModel):
    cb_id: Optional[int] = None
    standard_code: Optional[str] = None
    md_rate: Optional[int] = None
    travel_rate: Optional[int] = None
    updated_at: Optional[datetime] = None


class CbStdMdRatesResponse(CbStdMdRatesBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CbTravelPolicyBase(BaseModel):
    cb_id: int
    zone_name: str
    distance_km: Optional[int] = None
    transport_fee: Optional[int] = None
    accommodation_fee: Optional[int] = None
    sort_order: Optional[int] = None
    created_at: datetime


class CbTravelPolicyCreate(CbTravelPolicyBase):
    pass


class CbTravelPolicyUpdate(BaseModel):
    cb_id: Optional[int] = None
    zone_name: Optional[str] = None
    distance_km: Optional[int] = None
    transport_fee: Optional[int] = None
    accommodation_fee: Optional[int] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None


class CbTravelPolicyResponse(CbTravelPolicyBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CertificationBodiesBase(BaseModel):
    code: str
    name: str
    cb_initial: Optional[str] = None
    cb_type: CertificationBodiesCbType
    name_en: Optional[str] = None
    accreditation: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    is_active: bool
    activated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = Field(default=None, description="법인번호")
    personal_no: Optional[str] = Field(default=None, description="개인사업자번호")
    fax: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    doc_rule_contract: Optional[str] = None
    doc_rule_report: Optional[str] = None
    doc_rule_ncr: Optional[str] = None
    fee_per_md: Decimal
    fee_travel: Decimal
    fee_cert: Decimal
    max_consecutive: int
    impartiality_cycle_months: int
    reg_no: Optional[str] = None
    accreditation_region: Optional[str] = None
    accreditation_country: Optional[str] = None
    accreditation_body: Optional[str] = Field(default=None, description="KAB 등 인정기구")
    stamp_url: Optional[str] = None
    accreditation_no: Optional[str] = None
    accredited_standards: Optional[str] = None
    iaf_scopes: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = Field(default="정상", description="정상/정지/취소")
    evaluation_score: Optional[Decimal] = None
    tax_email: Optional[str] = None


class CertificationBodiesCreate(CertificationBodiesBase):
    pass


class CertificationBodiesUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    cb_initial: Optional[str] = None
    cb_type: Optional[CertificationBodiesCbType] = None
    name_en: Optional[str] = None
    accreditation: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    is_active: Optional[bool] = None
    activated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    personal_no: Optional[str] = None
    fax: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    doc_rule_contract: Optional[str] = None
    doc_rule_report: Optional[str] = None
    doc_rule_ncr: Optional[str] = None
    fee_per_md: Optional[Decimal] = None
    fee_travel: Optional[Decimal] = None
    fee_cert: Optional[Decimal] = None
    max_consecutive: Optional[int] = None
    impartiality_cycle_months: Optional[int] = None
    reg_no: Optional[str] = None
    accreditation_region: Optional[str] = None
    accreditation_country: Optional[str] = None
    accreditation_body: Optional[str] = None
    stamp_url: Optional[str] = None
    accreditation_no: Optional[str] = None
    accredited_standards: Optional[str] = None
    iaf_scopes: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = None
    evaluation_score: Optional[Decimal] = None
    tax_email: Optional[str] = None


class CertificationBodiesResponse(CertificationBodiesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CBStaffBase(BaseModel):
    cb_id: int
    emp_no: Optional[str] = None
    name: str
    position: Optional[str] = None
    department: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    task_type: Optional[str] = None
    role_level: Optional[str] = None


class CBStaffCreate(CBStaffBase):
    pass


class CBStaffUpdate(BaseModel):
    cb_id: Optional[int] = None
    emp_no: Optional[str] = None
    name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    task_type: Optional[str] = None
    role_level: Optional[str] = None


class CBStaffResponse(CBStaffBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
