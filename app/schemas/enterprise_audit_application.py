"""Enterprise audit application (MD snapshot) Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MdPreviewRequest(BaseModel):
    standards: List[str] = Field(..., min_length=1)
    employees: int = Field(..., ge=1)
    ksic_code: str = ""
    audit_type: str = "INITIAL"
    mode: str = "single"
    site_total: int = 1
    site_factor: float = 0.5
    shift_type: str = "same"
    shift_cnt: int = 2
    intg_level: float = 40
    intg_team_z: int = 1
    intg_team_sumx: int = 0
    # optional engine extras
    fsms_cat: str = "CI"
    haccp: int = 1
    en_tj: float = 50
    seu: int = 3
    it_users: int = 100
    md_risk: int = 1
    pii_role: str = "controller"


class MdPreviewResponse(BaseModel):
    complexity_level: str
    iaf_scope_code: Optional[str] = None
    iaf_sub: Optional[str] = None
    ksic_code: str
    employees: int
    audit_type: str
    standards: List[str]
    base_stage1_md: float
    base_stage2_md: float
    base_surveillance_md: float
    base_recertification_md: float
    final_days: float
    detail_log: Dict[str, Any] = Field(default_factory=dict)


class EnterpriseApplicationCreate(BaseModel):
    cb_id: int
    standards: List[str] = Field(..., min_length=1)
    employees: Optional[int] = Field(None, ge=1, description="미입력 시 company.employee_count")
    ksic_code: Optional[str] = None
    audit_type: str = "INITIAL"
    audit_request_id: Optional[int] = None
    company_id: Optional[int] = None
    mode: str = "single"
    site_total: int = 1
    site_factor: float = 0.5
    # engine extras (optional)
    fsms_cat: str = "CI"
    haccp: int = 1
    en_tj: float = 50
    seu: int = 3
    it_users: int = 100
    md_risk: int = 1
    intg_level: float = 40
    intg_team_z: int = 1
    intg_team_sumx: int = 0


class EnterpriseApplicationYearly(BaseModel):
    """연차/사후/재인증 — 인원 갱신 후 새 스냅샷 행 생성."""
    employees: int = Field(..., ge=1)
    audit_type: str = "SURVEILLANCE_1"
    standards: Optional[List[str]] = None
    ksic_code: Optional[str] = None
    cb_id: Optional[int] = None
    audit_request_id: Optional[int] = None
    company_id: Optional[int] = None


class CbApplicationReviewUpdate(BaseModel):
    cb_adjustment_ratio: float = Field(0, description="가감비율 % (음수=감산)")
    cb_adjustment_reason: Optional[str] = None
    is_witness_audit: Optional[bool] = None
    witness_type: Optional[str] = Field(None, description="NONE|KAB_WITNESS|INTERNAL_WITNESS")
    witness_auditor_name: Optional[str] = None
    status: Optional[str] = Field(None, description="SUBMITTED|REVIEWING|PROPOSED|CONTRACTED")


class EnterpriseApplicationOut(BaseModel):
    application_id: int
    enterprise_id: int
    cb_id: int
    audit_request_id: Optional[int] = None
    audit_type: str
    applied_standards: List[Any] = Field(default_factory=list)
    ksic_code: str
    iaf_scope_code: str
    active_employee_count: int
    complexity_level: str
    base_stage1_md: Decimal
    base_stage2_md: Decimal
    base_surveillance_md: Decimal
    base_recertification_md: Decimal
    base_md_detail_json: Optional[Dict[str, Any]] = None
    cb_adjustment_ratio: Decimal
    cb_adjustment_reason: Optional[str] = None
    final_audit_md: Optional[Decimal] = None
    is_witness_audit: bool
    witness_type: str
    witness_auditor_name: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
