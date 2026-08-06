"""Pydantic DTO schemas for CertApplication / CertContract (app.models.cert_application)."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.cert_application import ContractStatus


class CertContractBase(BaseModel):
    application_id: int = Field(..., description="cert_applications.id 참조")
    contract_no: str = Field(..., description="계약번호 (예: CNT-2026-0801)")
    audit_type: str = Field(..., description="최초, 사후, 갱신 등")
    total_md: float = Field(..., description="산정된 총 MD")
    total_amount: Optional[float] = Field(default=0, description="계약 금액")
    contract_date: date = Field(..., description="계약 체결일")
    status: Optional[ContractStatus] = Field(default=ContractStatus.DRAFT)


class CertContractCreate(CertContractBase):
    pass


class CertContractResponse(CertContractBase):
    id: int
    cb_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
