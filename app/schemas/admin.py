"""Pydantic DTO schemas for platform admin (app.models.admin)."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """단순 처리 결과 메시지 응답."""
    message: str


# --- CBContract ---

class CBContractBase(BaseModel):
    cb_id: int
    contract_year: int = 2026
    tier: str = "MEDIUM"
    annual_base_fee: Decimal
    price_per_md: Decimal
    contract_start_date: datetime
    contract_end_date: datetime
    is_active: bool = True


class CBContractCreate(CBContractBase):
    pass


class CBContractUpdate(BaseModel):
    tier: Optional[str] = None
    annual_base_fee: Optional[Decimal] = None
    price_per_md: Optional[Decimal] = None
    contract_start_date: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None
    is_active: Optional[bool] = None


class CBContractResponse(CBContractBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CBContractListResponse(CBContractResponse):
    cb_name: str  # certification_bodies 조인 필드
    cb_code: Optional[str] = None
    cb_status: Optional[str] = None
    scope_count: int = 0
    held_standard_count: int = 0
    held_standards: list[str] = Field(default_factory=list)
    ab_summary: str = ""
    accreditation_body: Optional[str] = None


class AdminDashboardStats(BaseModel):
    cb_count: int = 0
    company_count: int = 0
    auditor_count: int = 0
    pending_accreditation_count: int = 0


# --- CBAccreditedScope ---

class CBAccreditedScopeCreate(BaseModel):
    standard_master_id: int = Field(..., description="standard_masters.id 참조 (모델의 iso_standard_id에 매핑됨)")
    iaf_code: str


class CBAccreditedScopeResponse(BaseModel):
    id: int
    cb_accreditation_id: int
    iso_standard_id: int
    iaf_code: str
    is_approved: bool
    model_config = ConfigDict(from_attributes=True)


# --- CBAccreditation ---

class CBAccreditationRecordCreate(BaseModel):
    cb_id: int
    accreditation_body: str
    certificate_number: str
    certificate_file_url: Optional[str] = None
    scopes: list[CBAccreditedScopeCreate] = Field(default_factory=list)


class CBAccreditationResponse(BaseModel):
    id: int
    cb_id: int
    accreditation_body: str
    certificate_number: str
    certificate_file_url: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    scopes: list[CBAccreditedScopeResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CBAccreditationRecordListResponse(BaseModel):
    id: int
    cb_id: int
    cb_name: str
    accreditation_body: str
    certificate_number: str
    certificate_file_url: Optional[str] = None
    status: str
    reject_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    scopes: list[CBAccreditedScopeResponse]
    model_config = ConfigDict(from_attributes=True)


class AccreditationActionResponse(MessageResponse):
    accreditation: CBAccreditationResponse


class AccreditationRejectRequest(BaseModel):
    reject_reason: Optional[str] = Field(default=None, description="반려 사유")


# --- PlatformCalculationRule ---

class PlatformCalculationRuleUpdate(BaseModel):
    formula_expression: Optional[str] = Field(default=None, description="수식 표현")
    variables_json: Optional[dict] = Field(default=None, description="계수 및 변수 테이블")


class PlatformCalculationRuleResponse(BaseModel):
    id: int
    category: str
    rule_code: str
    title: str
    formula_expression: Optional[str] = None
    variables_json: Optional[dict] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CalculationRuleUpdateResponse(MessageResponse):
    rule: PlatformCalculationRuleResponse
