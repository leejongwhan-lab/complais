"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

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
    entity_type: Optional[str] = Field(default=None, description="개인/법인")
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_certified: Optional[int] = None
    status: Optional[str] = Field(default="정상", description="정상/휴업/폐업/인증취소")
    tax_contact_name: Optional[str] = None
    tax_email: Optional[str] = None


class CompaniesCreate(BaseModel):
    """기업 신규 등록 — 서버가 created_at/updated_at 및 채번(id)을 설정한다.

    프론트 별칭도 허용한다.
    - company_name_kr → name, company_name_en → name_en
    - biz_reg_num → biz_no, business_type → biz_type, business_item → biz_class
    - address_kr → address
    - ksic_codes/iaf_codes(배열) → ksic_code/iaf_code(콤마 구분 문자열)
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    company_no: Optional[int] = None
    cert_no: Optional[str] = None
    name: str = Field(
        validation_alias=AliasChoices("name", "company_name", "company_name_kr"),
    )
    name_en: Optional[str] = Field(default=None, validation_alias=AliasChoices("name_en", "company_name_en"))
    biz_no: Optional[str] = Field(default=None, validation_alias=AliasChoices("biz_no", "biz_reg_num"))
    corp_no: Optional[str] = None
    ceo_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ceo_name", "representative"),
    )
    biz_type: Optional[str] = Field(default=None, validation_alias=AliasChoices("biz_type", "business_type"))
    biz_class: Optional[str] = Field(default=None, validation_alias=AliasChoices("biz_class", "business_item"))
    address: Optional[str] = Field(default=None, validation_alias=AliasChoices("address", "address_kr"))
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    iaf_code: Optional[str] = None
    ksic_code: Optional[str] = None
    ksic_codes: Optional[List[str]] = None
    iaf_codes: Optional[List[str]] = None
    employee_count: int = 0
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    is_active: bool = True
    entity_type: Optional[str] = None
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_certified: Optional[int] = None
    status: Optional[str] = "정상"
    tax_contact_name: Optional[str] = None
    tax_email: Optional[str] = None

    @model_validator(mode="after")
    def flatten_code_arrays(self) -> "CompaniesCreate":
        if self.ksic_codes:
            self.ksic_code = ",".join(self.ksic_codes)
        if self.iaf_codes:
            self.iaf_code = ",".join(self.iaf_codes)
        return self


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
    entity_type: Optional[str] = None
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_certified: Optional[int] = None
    status: Optional[str] = None
    tax_contact_name: Optional[str] = None
    tax_email: Optional[str] = None


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
    work_type: Optional[str] = None
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
    work_type: Optional[str] = None
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


class CompanyStaffBase(BaseModel):
    company_id: int
    staff_name: str
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None


class CompanyStaffCreate(CompanyStaffBase):
    pass


class CompanyStaffUpdate(BaseModel):
    company_id: Optional[int] = None
    staff_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None


class CompanyStaffResponse(CompanyStaffBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyAuditHistoryBase(BaseModel):
    company_id: int
    initial_cert_date: Optional[date] = None
    surveillance_1_date: Optional[date] = None
    surveillance_2_date: Optional[date] = None
    renewal_date: Optional[date] = None
    manager_auditor: Optional[str] = None
    transfer_history: Optional[str] = None


class CompanyAuditHistoryCreate(CompanyAuditHistoryBase):
    pass


class CompanyAuditHistoryUpdate(BaseModel):
    company_id: Optional[int] = None
    initial_cert_date: Optional[date] = None
    surveillance_1_date: Optional[date] = None
    surveillance_2_date: Optional[date] = None
    renewal_date: Optional[date] = None
    manager_auditor: Optional[str] = None
    transfer_history: Optional[str] = None


class CompanyAuditHistoryResponse(CompanyAuditHistoryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyDepartmentsBase(BaseModel):
    company_id: int
    name: str
    sort_order: int = 0
    is_active: bool = True


class CompanyDepartmentsCreate(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True


class CompanyDepartmentsUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CompanyDepartmentsResponse(CompanyDepartmentsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 초안 스펙 호환 — 간소 Company DTO (기존 Companies* 와 병행)
# ---------------------------------------------------------------------------


class CompanyCreate(BaseModel):
    """고객사 생성 — company_name/representative 초안 필드명."""

    model_config = ConfigDict(populate_by_name=True)

    company_name: str = Field(..., validation_alias=AliasChoices("company_name", "name"))
    biz_no: str
    representative: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("representative", "ceo_name"),
    )
    employee_count: int = 1

    def to_companies_create(self) -> "CompaniesCreate":
        return CompaniesCreate(
            name=self.company_name,
            biz_no=self.biz_no,
            ceo_name=self.representative,
            employee_count=self.employee_count,
            is_active=True,
        )


class CompanyResponse(BaseModel):
    """고객사 조회 응답."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    company_name: str = Field(validation_alias=AliasChoices("company_name", "name"))
    biz_no: Optional[str] = None
    representative: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("representative", "ceo_name"),
    )
    employee_count: int = 1
    created_at: datetime

    @classmethod
    def from_orm_company(cls, company) -> "CompanyResponse":
        return cls(
            id=company.id,
            company_name=getattr(company, "company_name", None) or company.name,
            biz_no=company.biz_no,
            representative=getattr(company, "representative", None) or company.ceo_name,
            employee_count=int(company.employee_count or 1),
            created_at=company.created_at,
        )
