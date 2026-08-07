"""Enterprise certification application + CB review DTOs."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AnswerIn(BaseModel):
    standard_code: str
    question_key: str
    answer_value: Optional[str] = None  # yes|no
    answer_text: Optional[str] = None


class EnterpriseCertSubmitIn(BaseModel):
    cb_id: int
    standards: List[str] = Field(default_factory=list)
    standard_types: Dict[str, str] = Field(default_factory=dict)
    application_type: str = "initial"
    scope_kr: str
    scope_en: Optional[str] = None
    employee_count: int = 0
    site_count: int = 1
    work_type: Optional[str] = None
    desired_audit_start: date
    desired_audit_end: Optional[date] = None
    note: Optional[str] = None
    ksic_code: Optional[str] = None  # legacy primary; prefer ksic_codes
    ksic_codes: List[str] = Field(default_factory=list)
    iaf_code: Optional[str] = None  # legacy primary; prefer iaf_codes
    iaf_codes: List[str] = Field(default_factory=list)
    answers: List[AnswerIn] = Field(default_factory=list)
    integrated_check: Optional[Dict[str, str]] = None  # key -> yes|no
    # company_aspects payloads (ISO 14001 / 45001 / 50001)
    ems: Optional[Dict[str, Any]] = None
    ohs: Optional[Dict[str, Any]] = None
    enms: Optional[Dict[str, Any]] = None
    aspects: Optional[Dict[str, Any]] = None  # {ems, ohs, enms}


class EnterpriseCertListItem(BaseModel):
    id: int
    application_no: str
    company_id: int
    company_name: Optional[str] = None
    cb_id: Optional[int] = None
    standards: List[Any] = Field(default_factory=list)
    audit_mode: str
    application_type: str
    employee_count: int
    desired_audit_start: Optional[date] = None
    status: str
    submitted_at: Optional[datetime] = None


class EnterpriseCertDetail(BaseModel):
    id: int
    application_no: str
    company_id: int
    company_name: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zip_code: Optional[str] = None
    address_en: Optional[str] = None
    name_en: Optional[str] = None
    company_iaf_code: Optional[str] = None
    company_ksic_code: Optional[str] = None
    ksic_codes: List[str] = Field(default_factory=list)
    cb_id: Optional[int] = None
    cb_name: Optional[str] = None
    contract_id: Optional[int] = None
    application_type: str
    status: str
    standards: List[Any] = Field(default_factory=list)
    standard_audit_types: Dict[str, str] = Field(default_factory=dict)
    iaf_codes: List[str] = Field(default_factory=list)
    audit_mode: str
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    employee_count: int = 0
    site_count: int = 1
    work_type: Optional[str] = None
    desired_audit_start: Optional[date] = None
    desired_audit_end: Optional[date] = None
    note: Optional[str] = None
    questionnaire: Any = None
    integrated_check: Any = None
    aspects: Optional[Dict[str, Any]] = None
    snapshot: Any = None
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    sites: List[Dict[str, Any]] = Field(default_factory=list)
    md_review: Optional[Dict[str, Any]] = None
    review_logs: List[Dict[str, Any]] = Field(default_factory=list)
    integrated_summary: Optional[Dict[str, Any]] = None
    is_design_excluded: bool = False
    exclusion_note: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None


class CompanyInfoEditIn(BaseModel):
    employee_count: int
    address: Optional[str] = None
    detail_address: Optional[str] = None
    zip_code: Optional[str] = None
    ksic_codes: List[str] = Field(default_factory=list)


class MdSaveIn(BaseModel):
    md_plus_pct: int = 0
    md_minus_pct: int = 0
    md_note: Optional[str] = None
    is_design_excluded: bool = False
    exclusion_note: Optional[str] = None
    recompute_base: bool = True


class ReviewActionIn(BaseModel):
    action: str  # under_review | need_fix | approved | rejected | save_md
    memo: Optional[str] = None
    md_plus_pct: int = 0
    md_minus_pct: int = 0
    md_note: Optional[str] = None
    is_design_excluded: bool = False
    exclusion_note: Optional[str] = None


class OkOut(BaseModel):
    ok: bool = True
    message: Optional[str] = None
    id: Optional[int] = None
    contract_id: Optional[int] = None
    application_no: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
