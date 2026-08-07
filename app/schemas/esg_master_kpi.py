"""ESG master KPI catalog schemas (esg_master_kpis)."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EsgMasterKpiOut(BaseModel):
    kpi_id: int
    esg_category: str
    sub_category: str
    kpi_name: str
    is_quantitative: bool
    unit_format: str
    managed_standard_name: str
    iso_clause_detail: str
    is_iso_auditable: Optional[bool] = None
    source_type_code: str
    extraction_detail_method: str
    is_public_api_available: Optional[bool] = None
    criteria_mapping: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EsgKpiTrendOut(BaseModel):
    pct: Optional[float] = None
    direction: Optional[str] = Field(
        default=None, description="up | down | flat | null when unknown"
    )


class EsgMasterKpiPortalOut(EsgMasterKpiOut):
    """기업 포털 테이블용 — 입력 모드·연도값·목표·노트 포함."""

    kpi_code: str
    input_mode: str = Field(description="public | auditor | company")
    data_path_label: Optional[str] = None
    is_required: bool = False
    years: List[int] = Field(default_factory=list)
    year_values: Dict[str, Optional[str]] = Field(default_factory=dict)
    trend: Optional[EsgKpiTrendOut] = None
    goal_value: Optional[str] = None
    goal_year: Optional[int] = None
    has_audit_note: bool = False
    audit_note_preview: Optional[str] = None
    can_company_input: bool = False
    can_set_goal: bool = True
    current_year: int


class EsgMasterKpiListResponse(BaseModel):
    total: int
    skip: int = 0
    limit: int = 50
    data: List[EsgMasterKpiOut] = Field(default_factory=list)
    held_standards: List[str] = Field(
        default_factory=list,
        description="기업 보유 표준(배지와 동일). held_only 필터 기준.",
    )
    available_standards: List[str] = Field(
        default_factory=list,
        description="카탈로그 distinct managed_standard_name",
    )
    matched_to_held: bool = Field(
        default=False,
        description="held_only=true 로 보유 표준에 매칭된 결과인지",
    )
    years: List[int] = Field(default_factory=list)
    current_year: Optional[int] = None
    notice: Optional[str] = Field(
        default=None,
        description="빈 카탈로그·폴백 안내 등 soft-fail 메시지",
    )
    data_source: Optional[str] = Field(
        default=None,
        description="esg_master_kpis | kpi_master | empty",
    )


class EsgMasterKpiPortalListResponse(EsgMasterKpiListResponse):
    data: List[EsgMasterKpiPortalOut] = Field(default_factory=list)


class EsgMasterKpiMetaResponse(BaseModel):
    total: int
    by_category: dict = Field(default_factory=dict)
    available_standards: List[str] = Field(default_factory=list)


class CompanyEsgKpiGoalUpsert(BaseModel):
    kpi_id: int
    target_year: int
    target_value: str = Field(..., min_length=1, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    company_id: Optional[int] = None


class CompanyEsgKpiGoalOut(BaseModel):
    id: int
    company_id: int
    kpi_id: int
    target_year: int
    target_value: str
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyEsgKpiValueUpsert(BaseModel):
    kpi_id: int
    year: int
    value: str = Field(..., min_length=1, max_length=100)
    company_id: Optional[int] = None


class CompanyEsgKpiValueOut(BaseModel):
    id: int
    company_id: int
    kpi_id: int
    year: int
    value: str
    source_mode: str

    model_config = ConfigDict(from_attributes=True)


class CompanyEsgAuditNoteUpsert(BaseModel):
    kpi_id: int
    note: str = Field(..., min_length=1)
    company_id: Optional[int] = None


class CompanyEsgAuditNoteOut(BaseModel):
    id: int
    company_id: int
    kpi_id: int
    note: str
    auditor_user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
