"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuditAssignmentsRole, AuditClauseMatrixTargetAuditType, AuditDocumentRulesAuditType, AuditDocumentsDocStatus, AuditNcrsGrade, AuditNcrsStatus, AuditNoteClausesVerdict, AuditNoteNcrGrade, AuditNoteNcrStatus, AuditNotesFindingType, AuditNotesOverallVerdict, AuditNotesStatus, AuditPlansStatus, AuditProposalNegotiationsSenderType, AuditReportsReportType, AuditReportsStatus, AuditReportsVerdict


class AuditAssignmentsBase(BaseModel):
    application_id: Optional[int] = None
    contract_id: Optional[int] = None
    auditor_id: Optional[int] = None
    role: Optional[AuditAssignmentsRole] = None
    auditor_user_id: int
    assignment_role: str
    status: str
    iaf_match_status: str
    conflict_check_status: str
    client_confirmation_status: str
    assignment_note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    standards_json: Optional[str] = None
    iaf_codes_json: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    fee_type: Optional[str] = None
    fee_ratio: Optional[Decimal] = None
    daily_rate: Optional[int] = None
    assigned_days: Optional[Decimal] = None
    calculated_fee: Optional[Decimal] = None


class AuditAssignmentsCreate(AuditAssignmentsBase):
    pass


class AuditAssignmentsUpdate(BaseModel):
    application_id: Optional[int] = None
    contract_id: Optional[int] = None
    auditor_id: Optional[int] = None
    role: Optional[AuditAssignmentsRole] = None
    auditor_user_id: Optional[int] = None
    assignment_role: Optional[str] = None
    status: Optional[str] = None
    iaf_match_status: Optional[str] = None
    conflict_check_status: Optional[str] = None
    client_confirmation_status: Optional[str] = None
    assignment_note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    standards_json: Optional[str] = None
    iaf_codes_json: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    fee_type: Optional[str] = None
    fee_ratio: Optional[Decimal] = None
    daily_rate: Optional[int] = None
    assigned_days: Optional[Decimal] = None
    calculated_fee: Optional[Decimal] = None


class AuditAssignmentsResponse(AuditAssignmentsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditClauseMatrixBase(BaseModel):
    company_id: int
    standard: str
    clause_id: str
    contract_id: int = Field(description="계획 작성한 계약")
    target_audit_type: AuditClauseMatrixTargetAuditType = Field(description="다음에 볼 심사")
    target_sequence: Optional[int] = Field(default=None, description="SA1=1, SA2=2")
    created_by: Optional[int] = Field(default=None, description="팀장")
    created_at: Optional[datetime] = None


class AuditClauseMatrixCreate(AuditClauseMatrixBase):
    pass


class AuditClauseMatrixUpdate(BaseModel):
    company_id: Optional[int] = None
    standard: Optional[str] = None
    clause_id: Optional[str] = None
    contract_id: Optional[int] = None
    target_audit_type: Optional[AuditClauseMatrixTargetAuditType] = None
    target_sequence: Optional[int] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None


class AuditClauseMatrixResponse(AuditClauseMatrixBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditDayPlansBase(BaseModel):
    application_id: int
    audit_type: str
    current_stage: str
    audit_mode: str
    standards_json: Optional[str] = None
    employee_count: int
    site_count: int
    shift_type: str
    shift_count: int
    complexity_level: str
    stage1_days: Decimal
    stage2_days: Decimal
    total_days: Decimal
    auditor_count: int
    assignment_note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditDayPlansCreate(AuditDayPlansBase):
    pass


class AuditDayPlansUpdate(BaseModel):
    application_id: Optional[int] = None
    audit_type: Optional[str] = None
    current_stage: Optional[str] = None
    audit_mode: Optional[str] = None
    standards_json: Optional[str] = None
    employee_count: Optional[int] = None
    site_count: Optional[int] = None
    shift_type: Optional[str] = None
    shift_count: Optional[int] = None
    complexity_level: Optional[str] = None
    stage1_days: Optional[Decimal] = None
    stage2_days: Optional[Decimal] = None
    total_days: Optional[Decimal] = None
    auditor_count: Optional[int] = None
    assignment_note: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditDayPlansResponse(AuditDayPlansBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditDocDataBase(BaseModel):
    application_id: int
    doc_type: str
    doc_data: str
    saved_by: Optional[int] = None
    saved_at: Optional[datetime] = None


class AuditDocDataCreate(AuditDocDataBase):
    pass


class AuditDocDataUpdate(BaseModel):
    application_id: Optional[int] = None
    doc_type: Optional[str] = None
    doc_data: Optional[str] = None
    saved_by: Optional[int] = None
    saved_at: Optional[datetime] = None


class AuditDocDataResponse(AuditDocDataBase):
    id: int
    saved_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditDocumentRulesBase(BaseModel):
    audit_type: AuditDocumentRulesAuditType
    stage: int = Field(description="0=공통, 1=1단계, 2=2단계")
    doc_subtype: str = Field(description="proc_step key와 일치")
    doc_name_kr: str
    is_required: bool
    standard_specific: int = Field(description="1=표준별 1건씩 생성")
    sort_order: int


class AuditDocumentRulesCreate(AuditDocumentRulesBase):
    pass


class AuditDocumentRulesUpdate(BaseModel):
    audit_type: Optional[AuditDocumentRulesAuditType] = None
    stage: Optional[int] = None
    doc_subtype: Optional[str] = None
    doc_name_kr: Optional[str] = None
    is_required: Optional[bool] = None
    standard_specific: Optional[int] = None
    sort_order: Optional[int] = None


class AuditDocumentRulesResponse(AuditDocumentRulesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AuditDocumentsBase(BaseModel):
    contract_id: int
    doc_type: str
    doc_subtype: Optional[str] = None
    standard: Optional[str] = None
    stage: Optional[int] = None
    doc_status: AuditDocumentsDocStatus
    rule_id: Optional[int] = None
    doc_no: Optional[str] = None
    title: str
    data: Optional[str] = None
    verdict: Optional[str] = None
    status: str
    updated_by: Optional[int] = None
    created_by: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    is_visible_to_client: bool
    created_at: datetime


class AuditDocumentsCreate(AuditDocumentsBase):
    pass


class AuditDocumentsUpdate(BaseModel):
    contract_id: Optional[int] = None
    doc_type: Optional[str] = None
    doc_subtype: Optional[str] = None
    standard: Optional[str] = None
    stage: Optional[int] = None
    doc_status: Optional[AuditDocumentsDocStatus] = None
    rule_id: Optional[int] = None
    doc_no: Optional[str] = None
    title: Optional[str] = None
    data: Optional[str] = None
    verdict: Optional[str] = None
    status: Optional[str] = None
    updated_by: Optional[int] = None
    created_by: Optional[int] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploaded_at: Optional[datetime] = None
    is_visible_to_client: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuditDocumentsResponse(AuditDocumentsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNcrsBase(BaseModel):
    application_id: int
    contract_id: int
    clause_id: str = Field(description="조항 번호 (4.1 등)")
    std_code: str = Field(description="표준 코드 (c,e,s 등)")
    grade: AuditNcrsGrade
    finding: Optional[str] = Field(default=None, description="심사소견 (부적합 내용)")
    requirement: Optional[str] = Field(default=None, description="해당 요구사항 조항")
    cause: Optional[str] = Field(default=None, description="원인 분석")
    due_date: Optional[date] = Field(default=None, description="조치 기한")
    correction: Optional[str] = Field(default=None, description="즉각시정 (Correction)")
    corrective_action: Optional[str] = Field(default=None, description="시정조치 (Corrective Action)")
    ca_evidence: Optional[str] = Field(default=None, description="시정조치 증거/첨부 설명")
    ca_submitted_at: Optional[datetime] = Field(default=None, description="기업 제출일시")
    status: AuditNcrsStatus
    issued_at: Optional[datetime] = Field(default=None, description="NCR 발행일시")
    issued_by: Optional[int] = Field(default=None, description="발행자 (심사팀장) user_id")
    reviewed_at: Optional[datetime] = Field(default=None, description="심사팀장 검토일시")
    reviewed_by: Optional[int] = Field(default=None, description="검토자 user_id")
    review_comment: Optional[str] = Field(default=None, description="검토 의견 (승인/반려 사유)")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    obs_key: Optional[str] = None


class AuditNcrsCreate(AuditNcrsBase):
    pass


class AuditNcrsUpdate(BaseModel):
    application_id: Optional[int] = None
    contract_id: Optional[int] = None
    clause_id: Optional[str] = None
    std_code: Optional[str] = None
    grade: Optional[AuditNcrsGrade] = None
    finding: Optional[str] = None
    requirement: Optional[str] = None
    cause: Optional[str] = None
    due_date: Optional[date] = None
    correction: Optional[str] = None
    corrective_action: Optional[str] = None
    ca_evidence: Optional[str] = None
    ca_submitted_at: Optional[datetime] = None
    status: Optional[AuditNcrsStatus] = None
    issued_at: Optional[datetime] = None
    issued_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = None
    review_comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    obs_key: Optional[str] = None


class AuditNcrsResponse(AuditNcrsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNoteClausesBase(BaseModel):
    note_id: int
    standard: str
    clause_id: str
    clause_label: Optional[str] = None
    verdict: Optional[AuditNoteClausesVerdict] = None
    evidence: Optional[str] = None
    finding: Optional[str] = None
    auditor_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AuditNoteClausesCreate(AuditNoteClausesBase):
    pass


class AuditNoteClausesUpdate(BaseModel):
    note_id: Optional[int] = None
    standard: Optional[str] = None
    clause_id: Optional[str] = None
    clause_label: Optional[str] = None
    verdict: Optional[AuditNoteClausesVerdict] = None
    evidence: Optional[str] = None
    finding: Optional[str] = None
    auditor_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditNoteClausesResponse(AuditNoteClausesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNoteEntriesBase(BaseModel):
    company_id: int
    contract_id: Optional[str] = None
    kind: str
    clause_id: Optional[str] = None
    standard_code: Optional[str] = None
    payload_json: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditNoteEntriesCreate(AuditNoteEntriesBase):
    pass


class AuditNoteEntriesUpdate(BaseModel):
    company_id: Optional[int] = None
    contract_id: Optional[str] = None
    kind: Optional[str] = None
    clause_id: Optional[str] = None
    standard_code: Optional[str] = None
    payload_json: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditNoteEntriesResponse(AuditNoteEntriesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNoteKpiBase(BaseModel):
    note_id: int
    kpi_id: int
    measured_value: Optional[Decimal] = None
    measured_year: int
    data_source: Optional[str] = None
    evidence: Optional[str] = None
    is_verified: bool
    note_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AuditNoteKpiCreate(AuditNoteKpiBase):
    pass


class AuditNoteKpiUpdate(BaseModel):
    note_id: Optional[int] = None
    kpi_id: Optional[int] = None
    measured_value: Optional[Decimal] = None
    measured_year: Optional[int] = None
    data_source: Optional[str] = None
    evidence: Optional[str] = None
    is_verified: Optional[bool] = None
    note_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditNoteKpiResponse(AuditNoteKpiBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNoteNcrBase(BaseModel):
    note_id: int
    clause_id_ref: Optional[int] = None
    ncr_no: Optional[str] = None
    grade: AuditNoteNcrGrade
    standard: str
    clause: str
    title: str
    description: Optional[str] = None
    requirement: Optional[str] = None
    evidence: Optional[str] = None
    status: AuditNoteNcrStatus
    client_response: Optional[str] = None
    client_response_at: Optional[datetime] = None
    corrective_action: Optional[str] = None
    root_cause: Optional[str] = None
    due_date: Optional[date] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AuditNoteNcrCreate(AuditNoteNcrBase):
    pass


class AuditNoteNcrUpdate(BaseModel):
    note_id: Optional[int] = None
    clause_id_ref: Optional[int] = None
    ncr_no: Optional[str] = None
    grade: Optional[AuditNoteNcrGrade] = None
    standard: Optional[str] = None
    clause: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    requirement: Optional[str] = None
    evidence: Optional[str] = None
    status: Optional[AuditNoteNcrStatus] = None
    client_response: Optional[str] = None
    client_response_at: Optional[datetime] = None
    corrective_action: Optional[str] = None
    root_cause: Optional[str] = None
    due_date: Optional[date] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditNoteNcrResponse(AuditNoteNcrBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditNotesBase(BaseModel):
    contract_id: int
    auditor_id: int
    note_no: Optional[str] = None
    audit_date: Optional[date] = None
    status: AuditNotesStatus
    overall_verdict: Optional[AuditNotesOverallVerdict] = None
    summary: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    assignment_id: Optional[int] = None
    standard_code: str
    clause_no: str
    dept: str
    process: str
    content: Optional[str] = None
    finding_type: AuditNotesFindingType


class AuditNotesCreate(AuditNotesBase):
    pass


class AuditNotesUpdate(BaseModel):
    contract_id: Optional[int] = None
    auditor_id: Optional[int] = None
    note_no: Optional[str] = None
    audit_date: Optional[date] = None
    status: Optional[AuditNotesStatus] = None
    overall_verdict: Optional[AuditNotesOverallVerdict] = None
    summary: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    assignment_id: Optional[int] = None
    standard_code: Optional[str] = None
    clause_no: Optional[str] = None
    dept: Optional[str] = None
    process: Optional[str] = None
    content: Optional[str] = None
    finding_type: Optional[AuditNotesFindingType] = None


class AuditNotesResponse(AuditNotesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditPlanItemsBase(BaseModel):
    audit_plan_id: int
    time_slot: Optional[str] = None
    process_name: Optional[str] = None
    standard_clause: Optional[str] = None
    auditee_name: Optional[str] = None
    location_name: Optional[str] = None
    auditor_name: Optional[str] = None
    note: Optional[str] = None
    sort_order: Optional[int] = None
    auditor_id: Optional[int] = None
    process_group_id: Optional[str] = None
    clause_no: Optional[str] = None
    dept: Optional[str] = None
    standard_code: Optional[str] = None
    standard_key: Optional[str] = None


class AuditPlanItemsCreate(AuditPlanItemsBase):
    pass


class AuditPlanItemsUpdate(BaseModel):
    audit_plan_id: Optional[int] = None
    time_slot: Optional[str] = None
    process_name: Optional[str] = None
    standard_clause: Optional[str] = None
    auditee_name: Optional[str] = None
    location_name: Optional[str] = None
    auditor_name: Optional[str] = None
    note: Optional[str] = None
    sort_order: Optional[int] = None
    auditor_id: Optional[int] = None
    process_group_id: Optional[str] = None
    clause_no: Optional[str] = None
    dept: Optional[str] = None
    standard_code: Optional[str] = None
    standard_key: Optional[str] = None


class AuditPlanItemsResponse(AuditPlanItemsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AuditPlansBase(BaseModel):
    contract_id: int
    status: Optional[AuditPlansStatus] = None
    plan_date: Optional[date] = None
    audit_objective: Optional[str] = None
    audit_criteria: Optional[str] = None
    scope_summary: Optional[str] = None
    communication_note: Optional[str] = None
    sent_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AuditPlansCreate(AuditPlansBase):
    pass


class AuditPlansUpdate(BaseModel):
    contract_id: Optional[int] = None
    status: Optional[AuditPlansStatus] = None
    plan_date: Optional[date] = None
    audit_objective: Optional[str] = None
    audit_criteria: Optional[str] = None
    scope_summary: Optional[str] = None
    communication_note: Optional[str] = None
    sent_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditPlansResponse(AuditPlansBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditProposalNegotiationsBase(BaseModel):
    proposal_id: int
    sender_type: AuditProposalNegotiationsSenderType
    sender_id: int
    comment: str
    created_at: datetime


class AuditProposalNegotiationsCreate(AuditProposalNegotiationsBase):
    pass


class AuditProposalNegotiationsUpdate(BaseModel):
    proposal_id: Optional[int] = None
    sender_type: Optional[AuditProposalNegotiationsSenderType] = None
    sender_id: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditProposalNegotiationsResponse(AuditProposalNegotiationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditProposalsBase(BaseModel):
    project_id: int = Field(description="contracts.id")
    version: int
    content: Optional[str] = None
    status: str
    accepted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AuditProposalsCreate(AuditProposalsBase):
    pass


class AuditProposalsUpdate(BaseModel):
    project_id: Optional[int] = None
    version: Optional[int] = None
    content: Optional[str] = None
    status: Optional[str] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditProposalsResponse(AuditProposalsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditReportsBase(BaseModel):
    contract_id: int
    note_id: int
    report_no: Optional[str] = None
    report_type: AuditReportsReportType
    verdict: Optional[AuditReportsVerdict] = None
    issued_by: int
    issued_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    status: AuditReportsStatus
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AuditReportsCreate(AuditReportsBase):
    pass


class AuditReportsUpdate(BaseModel):
    contract_id: Optional[int] = None
    note_id: Optional[int] = None
    report_no: Optional[str] = None
    report_type: Optional[AuditReportsReportType] = None
    verdict: Optional[AuditReportsVerdict] = None
    issued_by: Optional[int] = None
    issued_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    status: Optional[AuditReportsStatus] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditReportsResponse(AuditReportsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
