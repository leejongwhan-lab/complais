"""CB Portal — 인증원 운영 (Witness Assessment) schemas."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WitnessSchemeTab(BaseModel):
    id: int
    code: str
    name_kr: str
    iso_ref: Optional[str] = None
    label: str
    has_cluster_logic: bool = False


class WitnessSummary(BaseModel):
    total: int = 0
    due_soon: int = 0  # 임박 ≤90일
    expired: int = 0
    missing: int = 0


class WitnessCodeRow(BaseModel):
    id: int
    scheme_id: int
    scheme_code: str
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None
    iaf_code: str
    description: Optional[str] = None
    is_critical: bool = False
    eligible_for_coverage: bool = False
    cycle_years: int = 5
    last_witness_date: Optional[date] = None
    next_due_date: Optional[date] = None
    is_auto: bool = False
    status: str  # 정상|임박|만료|미입력
    same_iaf_other_schemes: List[dict] = Field(default_factory=list)


class WitnessDashboardResponse(BaseModel):
    schemes: List[WitnessSchemeTab]
    scheme: Optional[WitnessSchemeTab] = None
    summary: WitnessSummary
    items: List[WitnessCodeRow]


class WitnessCompleteRequest(BaseModel):
    last_witness_date: date
    complete_integrated: bool = False  # 통합심사 — 같은 IAF 타 스킴도 완료


class WitnessCompleteResponse(BaseModel):
    updated_ids: List[int]
    auto_propagated_ids: List[int] = Field(default_factory=list)
    integrated_ids: List[int] = Field(default_factory=list)


class WitnessSettingsItem(BaseModel):
    id: int
    iaf_code: str
    description: Optional[str] = None
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None
    is_critical: bool = False
    eligible_for_coverage: bool = False
    cycle_years: int = 5
    last_witness_date: Optional[date] = None
    next_due_date: Optional[date] = None
    status: str = "미입력"


class WitnessSettingsBulkItem(BaseModel):
    id: int
    is_critical: Optional[bool] = None
    eligible_for_coverage: Optional[bool] = None
    cycle_years: Optional[int] = None
    last_witness_date: Optional[date] = None


class WitnessSettingsPutRequest(BaseModel):
    scheme: str
    items: List[WitnessSettingsBulkItem]


class WitnessSettingsResponse(BaseModel):
    scheme: WitnessSchemeTab
    has_cluster_logic: bool
    items: List[WitnessSettingsItem]
