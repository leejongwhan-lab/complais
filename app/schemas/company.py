"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CompanyDocumentsAccessLevel, CompanyDocumentsStatus, CompanySuppliersRelation, CompanySuppliersStatus


class CompaniesBase(BaseModel):
    company_no: Optional[int] = None
    cert_no: Optional[str] = Field(default=None, description="ComplAIs 기업번호 (100001~)")
    name: str
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_type: Optional[str] = Field(default=None, description="업태")
    biz_class: Optional[str] = Field(default=None, description="업종")
    address: Optional[str] = None
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    iaf_code: Optional[str] = None
    ksic_code: Optional[str] = None
    employee_count: int
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CompaniesCreate(CompaniesBase):
    pass


class CompaniesUpdate(BaseModel):
    company_no: Optional[int] = None
    cert_no: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_type: Optional[str] = None
    biz_class: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    iaf_code: Optional[str] = None
    ksic_code: Optional[str] = None
    employee_count: Optional[int] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompaniesResponse(CompaniesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyBranchesBase(BaseModel):
    company_id: int
    name: str
    address: Optional[str] = None
    address_en: Optional[str] = None
    employee_count: Optional[int] = None
    scope_kr: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: datetime


class CompanyBranchesCreate(CompanyBranchesBase):
    pass


class CompanyBranchesUpdate(BaseModel):
    company_id: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None
    address_en: Optional[str] = None
    employee_count: Optional[int] = None
    scope_kr: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class CompanyBranchesResponse(CompanyBranchesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyDocumentsBase(BaseModel):
    company_id: int
    doc_id: str
    category: str
    name: str
    revision: Optional[str] = None
    status: CompanyDocumentsStatus
    iso_clauses: Optional[str] = None
    owner_user_id: Optional[int] = None
    file_path: Optional[str] = None
    access_level: CompanyDocumentsAccessLevel
    review_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class CompanyDocumentsCreate(CompanyDocumentsBase):
    pass


class CompanyDocumentsUpdate(BaseModel):
    company_id: Optional[int] = None
    doc_id: Optional[str] = None
    category: Optional[str] = None
    name: Optional[str] = None
    revision: Optional[str] = None
    status: Optional[CompanyDocumentsStatus] = None
    iso_clauses: Optional[str] = None
    owner_user_id: Optional[int] = None
    file_path: Optional[str] = None
    access_level: Optional[CompanyDocumentsAccessLevel] = None
    review_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyDocumentsResponse(CompanyDocumentsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyKpiSelectionBase(BaseModel):
    company_id: int
    kpi_id: int
    kpi_code: str
    selected_at: datetime


class CompanyKpiSelectionCreate(CompanyKpiSelectionBase):
    pass


class CompanyKpiSelectionUpdate(BaseModel):
    company_id: Optional[int] = None
    kpi_id: Optional[int] = None
    kpi_code: Optional[str] = None
    selected_at: Optional[datetime] = None


class CompanyKpiSelectionResponse(CompanyKpiSelectionBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CompanyKpiTargetsBase(BaseModel):
    company_id: int
    kpi_id: str
    value_year: int
    target_value: str
    unit: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyKpiTargetsCreate(CompanyKpiTargetsBase):
    pass


class CompanyKpiTargetsUpdate(BaseModel):
    company_id: Optional[int] = None
    kpi_id: Optional[str] = None
    value_year: Optional[int] = None
    target_value: Optional[str] = None
    unit: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyKpiTargetsResponse(CompanyKpiTargetsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyProcessesBase(BaseModel):
    company_id: int
    process_code: str
    process_name: str
    department: Optional[str] = None
    sort_order: Optional[int] = None


class CompanyProcessesCreate(CompanyProcessesBase):
    pass


class CompanyProcessesUpdate(BaseModel):
    company_id: Optional[int] = None
    process_code: Optional[str] = None
    process_name: Optional[str] = None
    department: Optional[str] = None
    sort_order: Optional[int] = None


class CompanyProcessesResponse(CompanyProcessesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CompanySitesBase(BaseModel):
    company_id: int
    site_name: str
    address: Optional[str] = None
    biz_no: Optional[str] = None
    employee_count: int
    is_main: bool
    created_at: datetime
    updated_at: datetime


class CompanySitesCreate(CompanySitesBase):
    pass


class CompanySitesUpdate(BaseModel):
    company_id: Optional[int] = None
    site_name: Optional[str] = None
    address: Optional[str] = None
    biz_no: Optional[str] = None
    employee_count: Optional[int] = None
    is_main: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanySitesResponse(CompanySitesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanySuppliersBase(BaseModel):
    company_id: int
    supplier_company_id: Optional[int] = None
    supplier_name: str
    supplier_biz_no: Optional[str] = None
    tier: int
    relation: CompanySuppliersRelation
    supply_item: Optional[str] = None
    status: CompanySuppliersStatus
    created_at: datetime
    updated_at: datetime


class CompanySuppliersCreate(CompanySuppliersBase):
    pass


class CompanySuppliersUpdate(BaseModel):
    company_id: Optional[int] = None
    supplier_company_id: Optional[int] = None
    supplier_name: Optional[str] = None
    supplier_biz_no: Optional[str] = None
    tier: Optional[int] = None
    relation: Optional[CompanySuppliersRelation] = None
    supply_item: Optional[str] = None
    status: Optional[CompanySuppliersStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanySuppliersResponse(CompanySuppliersBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
