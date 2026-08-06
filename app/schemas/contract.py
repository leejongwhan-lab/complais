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


# --- Contract (신규 정규화 모델: app.models.contract.Contract, audit_contracts 테이블) ---

class ContractBase(BaseModel):
    application_id: int = Field(..., description="audit_applications.id 참조")
    contract_no: Optional[str] = Field(default=None, description="계약 번호")
    audit_type: str = Field(..., description="INITIAL/SURVEILLANCE1/SURVEILLANCE2/RENEWAL 등")
    standards: Optional[str] = Field(default=None, description="적용 표준 목록 (콤마구분 또는 JSON)")
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    total_md: Optional[float] = Field(default=None, description="계약 확정 총 MD")
    agreed_amount: Optional[Decimal] = Field(default=None, description="계약 확정 금액")
    high_value_threshold: Optional[float] = Field(default=None, description="고액 공제 기준 금액 (0 또는 미입력 시 공제 미적용)")
    high_value_deduction_rate: Optional[float] = Field(default=None, description="고액 공제 비율 (5.0=5% 또는 0.05)")
    status: str = Field(default="DRAFT", description="DRAFT/SENT/SIGNED/CANCELLED 등")
    signed_at: Optional[datetime] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    application_id: Optional[int] = None
    contract_no: Optional[str] = None
    audit_type: Optional[str] = None
    standards: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    total_md: Optional[float] = None
    agreed_amount: Optional[Decimal] = None
    high_value_threshold: Optional[float] = None
    high_value_deduction_rate: Optional[float] = None
    status: Optional[str] = None
    signed_at: Optional[datetime] = None


# --- 계약 정산 시뮬레이션 (settlement_calculator.calculate_contract_settlement 연동) ---

class ContractSettlementResult(BaseModel):
    """calculate_contract_settlement()의 반환값을 그대로 매핑하는 응답 스키마."""
    agreed_amount: float
    travel_expense: float
    vat_amount: float
    total_contract_amount: float
    base_settlement_fee: float
    extra_deduction: float
    final_auditor_fee: float


class ContractResponse(ContractBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    settlement: Optional[ContractSettlementResult] = Field(
        default=None, description="생성/수정 시점 기준 정산 시뮬레이션 결과 (계산값, DB 저장 아님)"
    )
    model_config = ConfigDict(from_attributes=True)


class ContractSettlementRequest(BaseModel):
    """정산 시뮬레이션 요청.

    `contract_id`를 지정하면 해당 계약의 저장된 값(agreed_amount, high_value_threshold,
    high_value_deduction_rate)을 기본값으로 사용하고, 요청에 명시된 값이 있으면 그 값으로 덮어쓴다.
    """
    contract_id: Optional[int] = Field(default=None, description="기준 계약 id (선택, 저장값을 기본값으로 사용)")
    fee_calculation_type: str = Field(default="PERCENTAGE", description="PERCENTAGE 또는 FLAT_FEE")
    agreed_amount: Optional[float] = Field(default=None, description="순수 기업 계약금 (부가세/출장비 제외)")
    travel_expense: float = Field(default=0.0, description="출장비")
    fee_ratio: float = Field(default=0.80, description="정률 모델 시 심사원 비율 (예: 0.80 = 80%)")
    flat_fee: float = Field(default=0.0, description="정액 모델 시 기본 고정 금액")
    high_value_threshold: Optional[float] = Field(default=None, description="고액 공제 기준 금액 (0 또는 미입력 시 공제 미적용)")
    high_value_deduction_rate: Optional[float] = Field(default=None, description="고액 공제 비율 (5.0=5% 또는 0.05)")


# --- AuditAssignment (신규 정규화 모델: app.models.contract.AuditAssignment, audit_application_assignments 테이블) ---

class AuditAssignmentBase(BaseModel):
    application_id: int = Field(..., description="audit_applications.id 참조")
    auditor_id: int = Field(..., description="auditors.id 참조")
    contract_id: Optional[int] = Field(default=None, description="배정이 귀속된 계약 (선택)")
    role: str = Field(default="MEMBER", description="LEAD/MEMBER/OBSERVER/WITNESS")
    status: str = Field(default="ASSIGNED", description="ASSIGNED/CONFIRMED/DECLINED/COMPLETED")
    assigned_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    note: Optional[str] = None


class AuditAssignmentCreate(AuditAssignmentBase):
    standard: Optional[str] = Field(
        default=None,
        description="배정 사전 자격 검증에 사용할 표준 코드 (QMS/EMS/OHSMS 등). "
        "지정 시 로그인한 CB에서 해당 심사원이 승인된 자격범위를 보유하는지 검증 후 배정을 생성합니다. "
        "DB에는 저장되지 않는 검증 전용 필드입니다.",
    )


class AuditAssignmentUpdate(BaseModel):
    application_id: Optional[int] = None
    auditor_id: Optional[int] = None
    contract_id: Optional[int] = None
    role: Optional[str] = None
    status: Optional[str] = None
    assigned_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    note: Optional[str] = None
    standard: Optional[str] = Field(
        default=None,
        description="배정 사전 자격 검증에 사용할 표준 코드 (지정 시에만 검증). DB에는 저장되지 않습니다.",
    )


class AuditAssignmentResponse(AuditAssignmentBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
