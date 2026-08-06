"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KpiMasterCategoryEsg, KpiMasterDirection


class KpiActualsBase(BaseModel):
    company_id: int
    kpi_id: int
    contract_id: Optional[int] = None
    measured_year: int
    measured_value: Optional[Decimal] = None
    data_source: Optional[str] = None
    is_verified: bool
    verified_by: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class KpiActualsCreate(KpiActualsBase):
    pass


class KpiActualsUpdate(BaseModel):
    company_id: Optional[int] = None
    kpi_id: Optional[int] = None
    contract_id: Optional[int] = None
    measured_year: Optional[int] = None
    measured_value: Optional[Decimal] = None
    data_source: Optional[str] = None
    is_verified: Optional[bool] = None
    verified_by: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KpiActualsResponse(KpiActualsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KpiBenchmarkBase(BaseModel):
    kpi_id: int = Field(description="kpi_master.id")
    iaf_code: str = Field(description="IAF 업종코드")
    ref_year: int = Field(description="기준연도")
    benchmark_value: Optional[Decimal] = Field(default=None, description="업종 평균값")
    percentile_25: Optional[Decimal] = None
    percentile_50: Optional[Decimal] = None
    percentile_75: Optional[Decimal] = None
    sample_size: Optional[int] = Field(default=None, description="표본 기업 수")
    data_source: Optional[str] = Field(default=None, description="출처 (공공API 등)")
    created_at: datetime
    updated_at: datetime


class KpiBenchmarkCreate(KpiBenchmarkBase):
    pass


class KpiBenchmarkUpdate(BaseModel):
    kpi_id: Optional[int] = None
    iaf_code: Optional[str] = None
    ref_year: Optional[int] = None
    benchmark_value: Optional[Decimal] = None
    percentile_25: Optional[Decimal] = None
    percentile_50: Optional[Decimal] = None
    percentile_75: Optional[Decimal] = None
    sample_size: Optional[int] = None
    data_source: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KpiBenchmarkResponse(KpiBenchmarkBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KpiMasterBase(BaseModel):
    kpi_key: str
    kpi_code: str
    category_esg: KpiMasterCategoryEsg
    category_mid: str
    name_kr: str
    name_en: Optional[str] = None
    unit: Optional[str] = None
    direction: KpiMasterDirection
    frameworks: Optional[str] = None
    is_mandatory: bool
    applicable_stds: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    gri_code: Optional[str] = None
    k_esg_code: Optional[str] = None
    esrs_code: Optional[str] = None
    iso_clause: Optional[str] = None
    auto_collect: Optional[int] = None
    api_source: Optional[str] = None


class KpiMasterCreate(KpiMasterBase):
    pass


class KpiMasterUpdate(BaseModel):
    kpi_key: Optional[str] = None
    kpi_code: Optional[str] = None
    category_esg: Optional[KpiMasterCategoryEsg] = None
    category_mid: Optional[str] = None
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    unit: Optional[str] = None
    direction: Optional[KpiMasterDirection] = None
    frameworks: Optional[str] = None
    is_mandatory: Optional[bool] = None
    applicable_stds: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None
    gri_code: Optional[str] = None
    k_esg_code: Optional[str] = None
    esrs_code: Optional[str] = None
    iso_clause: Optional[str] = None
    auto_collect: Optional[int] = None
    api_source: Optional[str] = None


class KpiMasterResponse(KpiMasterBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KpiTargetsBase(BaseModel):
    company_id: int
    kpi_id: int
    target_year: int
    target_value: Optional[Decimal] = None
    baseline_value: Optional[Decimal] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class KpiTargetsCreate(KpiTargetsBase):
    pass


class KpiTargetsUpdate(BaseModel):
    company_id: Optional[int] = None
    kpi_id: Optional[int] = None
    target_year: Optional[int] = None
    target_value: Optional[Decimal] = None
    baseline_value: Optional[Decimal] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KpiTargetsResponse(KpiTargetsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
