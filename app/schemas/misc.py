"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KarCpdRecordsActivityType, KarCpdRecordsStatus, KarQualificationsGrade, KarQualificationsStatus, KarRenewalRequestsStatus, MaterialBalanceItemsCategory, NcrReportsNcGrade, NcrReportsStatus, SupplierDueDiligenceDataSecurity, SupplierDueDiligenceEnvironment, SupplierDueDiligenceEthics, SupplierDueDiligenceHumanRights, SupplierDueDiligenceOverallStatus, SupplierDueDiligenceSafety, SupplierDueDiligenceSupplyChain


class KarCpdRecordsBase(BaseModel):
    auditor_id: int
    kar_qual_id: Optional[int] = None
    activity_date: date
    activity_type: KarCpdRecordsActivityType
    activity_name: str
    hours: Decimal
    status: KarCpdRecordsStatus
    review_note: Optional[str] = None
    created_at: datetime
    is_fulfilled: Optional[bool] = Field(default=None, description="CPD 이수 요건 충족 여부")


class KarCpdRecordsCreate(KarCpdRecordsBase):
    pass


class KarCpdRecordsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    kar_qual_id: Optional[int] = None
    activity_date: Optional[date] = None
    activity_type: Optional[KarCpdRecordsActivityType] = None
    activity_name: Optional[str] = None
    hours: Optional[Decimal] = None
    status: Optional[KarCpdRecordsStatus] = None
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None
    is_fulfilled: Optional[bool] = None


class KarCpdRecordsResponse(KarCpdRecordsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KarQualificationsBase(BaseModel):
    auditor_id: int
    qualification_body_id: Optional[int] = None
    custom_body_name: Optional[str] = None
    cert_doc_no: Optional[str] = None
    kar_no: Optional[str] = Field(default=None, description="KAR 자격번호")
    standard: str
    grade: Optional[KarQualificationsGrade] = None
    status: KarQualificationsStatus
    issued_at: Optional[date] = Field(default=None, description="최초 취득일 (initial_date)")
    renewal_date: Optional[date] = None
    expires_at: Optional[date] = Field(default=None, description="만료일 (expire_date)")
    created_at: datetime
    iaf_codes: Optional[str] = Field(default=None, description="IAF 코드 (콤마구분)")
    mdqms_areas: Optional[str] = Field(default=None, description="ISO 13485 기술영역")
    nace_codes: Optional[str] = Field(default=None, description="NACE Division 코드 (콤마구분)")


class KarQualificationsCreate(KarQualificationsBase):
    pass


class KarQualificationsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    qualification_body_id: Optional[int] = None
    custom_body_name: Optional[str] = None
    cert_doc_no: Optional[str] = None
    kar_no: Optional[str] = None
    standard: Optional[str] = None
    grade: Optional[KarQualificationsGrade] = None
    status: Optional[KarQualificationsStatus] = None
    issued_at: Optional[date] = None
    renewal_date: Optional[date] = None
    expires_at: Optional[date] = None
    created_at: Optional[datetime] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = None
    nace_codes: Optional[str] = None


class KarQualificationsResponse(KarQualificationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class KarRenewalRequestsBase(BaseModel):
    auditor_id: int
    kar_qual_id: Optional[int] = None
    career_count: int
    cpd_hours: Decimal
    conflict_submitted: int
    conduct_signed: int
    status: KarRenewalRequestsStatus
    submitted_at: Optional[datetime] = None
    created_at: datetime


class KarRenewalRequestsCreate(KarRenewalRequestsBase):
    pass


class KarRenewalRequestsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    kar_qual_id: Optional[int] = None
    career_count: Optional[int] = None
    cpd_hours: Optional[Decimal] = None
    conflict_submitted: Optional[int] = None
    conduct_signed: Optional[int] = None
    status: Optional[KarRenewalRequestsStatus] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class KarRenewalRequestsResponse(KarRenewalRequestsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class MaterialBalanceActualsBase(BaseModel):
    company_id: int
    item_id: int
    measured_year: int
    measured_value: Optional[Decimal] = None
    ghg_calc: Optional[Decimal] = None
    data_source: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaterialBalanceActualsCreate(MaterialBalanceActualsBase):
    pass


class MaterialBalanceActualsUpdate(BaseModel):
    company_id: Optional[int] = None
    item_id: Optional[int] = None
    measured_year: Optional[int] = None
    measured_value: Optional[Decimal] = None
    ghg_calc: Optional[Decimal] = None
    data_source: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaterialBalanceActualsResponse(MaterialBalanceActualsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class MaterialBalanceItemsBase(BaseModel):
    item_code: str
    category: MaterialBalanceItemsCategory
    item_type: str
    item_name: str
    unit: Optional[str] = None
    is_energy: Optional[bool] = None
    api_source: Optional[str] = None
    emission_factor_id: Optional[int] = None
    kpi_code: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class MaterialBalanceItemsCreate(MaterialBalanceItemsBase):
    pass


class MaterialBalanceItemsUpdate(BaseModel):
    item_code: Optional[str] = None
    category: Optional[MaterialBalanceItemsCategory] = None
    item_type: Optional[str] = None
    item_name: Optional[str] = None
    unit: Optional[str] = None
    is_energy: Optional[bool] = None
    api_source: Optional[str] = None
    emission_factor_id: Optional[int] = None
    kpi_code: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class MaterialBalanceItemsResponse(MaterialBalanceItemsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class NcrReportsBase(BaseModel):
    ncr_no: str
    project_id: int = Field(description="contracts.id")
    company_id: int
    nc_grade: NcrReportsNcGrade
    clause_no: Optional[str] = None
    finding_detail: Optional[str] = None
    due_date: Optional[date] = None
    issued_by: Optional[int] = None
    issued_at: Optional[datetime] = None
    status: NcrReportsStatus
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    created_at: datetime


class NcrReportsCreate(NcrReportsBase):
    pass


class NcrReportsUpdate(BaseModel):
    ncr_no: Optional[str] = None
    project_id: Optional[int] = None
    company_id: Optional[int] = None
    nc_grade: Optional[NcrReportsNcGrade] = None
    clause_no: Optional[str] = None
    finding_detail: Optional[str] = None
    due_date: Optional[date] = None
    issued_by: Optional[int] = None
    issued_at: Optional[datetime] = None
    status: Optional[NcrReportsStatus] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    created_at: Optional[datetime] = None


class NcrReportsResponse(NcrReportsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PopbillBizCacheBase(BaseModel):
    biz_no: str = Field(description="사업자등록번호")
    corp_name: Optional[str] = Field(default=None, description="기업명")
    ksic_code: Optional[str] = Field(default=None, description="KSIC 코드 (팝빌 industCode)")
    iaf_code: Optional[str] = Field(default=None, description="IAF 코드 (KSIC→IAF 자동변환)")
    raw_data: Optional[str] = Field(default=None, description="팝빌 원본 응답 (JSON)")
    created_at: Optional[datetime] = Field(default=None, description="최초 조회일")


class PopbillBizCacheCreate(PopbillBizCacheBase):
    pass


class PopbillBizCacheUpdate(BaseModel):
    biz_no: Optional[str] = None
    corp_name: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    raw_data: Optional[str] = None
    created_at: Optional[datetime] = None


class PopbillBizCacheResponse(PopbillBizCacheBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PublicDataSnapshotsBase(BaseModel):
    company_id: Optional[int] = None
    kpi_id: int
    source_type: str
    source_org: Optional[str] = None
    period: str
    value: Optional[Decimal] = None
    raw_json: Optional[str] = None
    collected_at: datetime


class PublicDataSnapshotsCreate(PublicDataSnapshotsBase):
    pass


class PublicDataSnapshotsUpdate(BaseModel):
    company_id: Optional[int] = None
    kpi_id: Optional[int] = None
    source_type: Optional[str] = None
    source_org: Optional[str] = None
    period: Optional[str] = None
    value: Optional[Decimal] = None
    raw_json: Optional[str] = None
    collected_at: Optional[datetime] = None


class PublicDataSnapshotsResponse(PublicDataSnapshotsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SupplierDueDiligenceBase(BaseModel):
    supplier_id: int
    audited_by: int
    dd_date: date
    human_rights: SupplierDueDiligenceHumanRights
    environment: SupplierDueDiligenceEnvironment
    safety: SupplierDueDiligenceSafety
    ethics: SupplierDueDiligenceEthics
    data_security: SupplierDueDiligenceDataSecurity
    supply_chain: SupplierDueDiligenceSupplyChain
    overall_status: SupplierDueDiligenceOverallStatus
    memo: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SupplierDueDiligenceCreate(SupplierDueDiligenceBase):
    pass


class SupplierDueDiligenceUpdate(BaseModel):
    supplier_id: Optional[int] = None
    audited_by: Optional[int] = None
    dd_date: Optional[date] = None
    human_rights: Optional[SupplierDueDiligenceHumanRights] = None
    environment: Optional[SupplierDueDiligenceEnvironment] = None
    safety: Optional[SupplierDueDiligenceSafety] = None
    ethics: Optional[SupplierDueDiligenceEthics] = None
    data_security: Optional[SupplierDueDiligenceDataSecurity] = None
    supply_chain: Optional[SupplierDueDiligenceSupplyChain] = None
    overall_status: Optional[SupplierDueDiligenceOverallStatus] = None
    memo: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SupplierDueDiligenceResponse(SupplierDueDiligenceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
