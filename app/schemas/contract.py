"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ContractsAuditMode, ContractsAuditType, ContractsContractType, ContractsStage, ContractsStatus, ContractsVerificationStatus


class ContractsBase(BaseModel):
    contract_id: str
    cb_id: int
    company_id: int
    proposal_id: Optional[int] = None
    lead_auditor_id: int
    verifier_auditor_id: Optional[int] = None
    verification_status: Optional[ContractsVerificationStatus] = None
    member_auditor_ids: Optional[str] = None
    observer_ids: Optional[str] = None
    audit_type: ContractsAuditType
    standards: str
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    stage: Optional[ContractsStage] = None
    current_stage: int
    total_md: Decimal
    agreed_amount: Decimal
    status: ContractsStatus
    note_submitted_at: Optional[datetime] = None
    report_issued_at: Optional[datetime] = None
    cert_issued_at: Optional[datetime] = None
    cert_expiry_at: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    contract_type: ContractsContractType
    audit_days: Optional[Decimal] = None
    fee_audit: Optional[int] = None
    fee_travel: Optional[int] = None
    fee_other: Optional[int] = None
    fee_total: Optional[int] = None
    payment_terms: Optional[str] = None
    travel_policy: Optional[str] = None
    fee_report: Optional[int] = None
    fee_application: Optional[int] = None
    applied_standards: Optional[str] = None
    cb_sent_at: Optional[datetime] = None
    client_signed_at: Optional[datetime] = None
    client_signed_by: Optional[int] = None
    cb_signed_at: Optional[datetime] = None
    cb_signed_by: Optional[int] = None
    audit_mode: ContractsAuditMode


class ContractsCreate(ContractsBase):
    pass


class ContractsUpdate(BaseModel):
    contract_id: Optional[str] = None
    cb_id: Optional[int] = None
    company_id: Optional[int] = None
    proposal_id: Optional[int] = None
    lead_auditor_id: Optional[int] = None
    verifier_auditor_id: Optional[int] = None
    verification_status: Optional[ContractsVerificationStatus] = None
    member_auditor_ids: Optional[str] = None
    observer_ids: Optional[str] = None
    audit_type: Optional[ContractsAuditType] = None
    standards: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    stage: Optional[ContractsStage] = None
    current_stage: Optional[int] = None
    total_md: Optional[Decimal] = None
    agreed_amount: Optional[Decimal] = None
    status: Optional[ContractsStatus] = None
    note_submitted_at: Optional[datetime] = None
    report_issued_at: Optional[datetime] = None
    cert_issued_at: Optional[datetime] = None
    cert_expiry_at: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    contract_type: Optional[ContractsContractType] = None
    audit_days: Optional[Decimal] = None
    fee_audit: Optional[int] = None
    fee_travel: Optional[int] = None
    fee_other: Optional[int] = None
    fee_total: Optional[int] = None
    payment_terms: Optional[str] = None
    travel_policy: Optional[str] = None
    fee_report: Optional[int] = None
    fee_application: Optional[int] = None
    applied_standards: Optional[str] = None
    cb_sent_at: Optional[datetime] = None
    client_signed_at: Optional[datetime] = None
    client_signed_by: Optional[int] = None
    cb_signed_at: Optional[datetime] = None
    cb_signed_by: Optional[int] = None
    audit_mode: Optional[ContractsAuditMode] = None


class ContractsResponse(ContractsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
