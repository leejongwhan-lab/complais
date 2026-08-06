"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EmissionFactorMasterFuelType, EsgMasterCategory, EsgMasterSourceType, MasterIafCodesRisk14001, MasterIafCodesRisk45001, MasterIafCodesRisk9001, NaceCodesRisk14001, NaceCodesRisk45001, NaceCodesRisk9001


class AccreditationBodiesBase(BaseModel):
    name: str
    country: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class AccreditationBodiesCreate(AccreditationBodiesBase):
    pass


class AccreditationBodiesUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class AccreditationBodiesResponse(AccreditationBodiesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentNumbersBase(BaseModel):
    cb_id: int
    doc_type: str
    doc_no: str
    ref_id: Optional[int] = None
    created_at: datetime


class DocumentNumbersCreate(DocumentNumbersBase):
    pass


class DocumentNumbersUpdate(BaseModel):
    cb_id: Optional[int] = None
    doc_type: Optional[str] = None
    doc_no: Optional[str] = None
    ref_id: Optional[int] = None
    created_at: Optional[datetime] = None


class DocumentNumbersResponse(DocumentNumbersBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EmissionFactorMasterBase(BaseModel):
    fuel_code: str
    fuel_name: str
    fuel_type: Optional[EmissionFactorMasterFuelType] = None
    factor_year: int
    factor_co2: Optional[Decimal] = None
    factor_ch4: Optional[Decimal] = None
    factor_n2o: Optional[Decimal] = None
    unit_input: Optional[str] = None
    scope_type: Optional[int] = None
    fuel_category: Optional[str] = Field(default=None, description="대분류")
    fuel_subcategory: Optional[str] = Field(default=None, description="중분류")
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class EmissionFactorMasterCreate(EmissionFactorMasterBase):
    pass


class EmissionFactorMasterUpdate(BaseModel):
    fuel_code: Optional[str] = None
    fuel_name: Optional[str] = None
    fuel_type: Optional[EmissionFactorMasterFuelType] = None
    factor_year: Optional[int] = None
    factor_co2: Optional[Decimal] = None
    factor_ch4: Optional[Decimal] = None
    factor_n2o: Optional[Decimal] = None
    unit_input: Optional[str] = None
    scope_type: Optional[int] = None
    fuel_category: Optional[str] = None
    fuel_subcategory: Optional[str] = None
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class EmissionFactorMasterResponse(EmissionFactorMasterBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EsgMasterBase(BaseModel):
    kpi_id: str
    category: EsgMasterCategory
    subcategory: Optional[str] = None
    name_kr: str
    name_en: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    iso_clause: Optional[str] = None
    source_type: Optional[EsgMasterSourceType] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class EsgMasterCreate(EsgMasterBase):
    pass


class EsgMasterUpdate(BaseModel):
    kpi_id: Optional[str] = None
    category: Optional[EsgMasterCategory] = None
    subcategory: Optional[str] = None
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    iso_clause: Optional[str] = None
    source_type: Optional[EsgMasterSourceType] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class EsgMasterResponse(EsgMasterBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class IafNaceMapBase(BaseModel):
    iaf_code: str = Field(description="IAF 코드 (예: 01)")
    nace_division: str = Field(description="NACE Division (예: 01)")


class IafNaceMapCreate(IafNaceMapBase):
    pass


class IafNaceMapUpdate(BaseModel):
    iaf_code: Optional[str] = None
    nace_division: Optional[str] = None


class IafNaceMapResponse(IafNaceMapBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class InstitutionDataBase(BaseModel):
    korName: str = Field(description="인증기관 국문명")
    engName: str = Field(description="인증기관 영문명")
    abbreviation: str = Field(description="인증기관 약어")
    bizNumber: str = Field(description="사업자등록번호")
    president: str = Field(description="대표 이름")
    zipCode: Optional[str] = Field(default=None, description="우편번호")
    address: Optional[str] = Field(default=None, description="기본 주소")
    detailAddress: Optional[str] = Field(default=None, description="상세 주소")
    bank: Optional[str] = Field(default=None, description="은행 정보")
    bankAccount: Optional[str] = Field(default=None, description="은행 계좌")
    depositor: Optional[str] = Field(default=None, description="예금주명")
    tel: Optional[str] = Field(default=None, description="대표전화")
    fax: Optional[str] = Field(default=None, description="팩스")
    homepage: Optional[str] = Field(default=None, description="홈페이지")


class InstitutionDataCreate(InstitutionDataBase):
    pass


class InstitutionDataUpdate(BaseModel):
    korName: Optional[str] = None
    engName: Optional[str] = None
    abbreviation: Optional[str] = None
    bizNumber: Optional[str] = None
    president: Optional[str] = None
    zipCode: Optional[str] = None
    address: Optional[str] = None
    detailAddress: Optional[str] = None
    bank: Optional[str] = None
    bankAccount: Optional[str] = None
    depositor: Optional[str] = None
    tel: Optional[str] = None
    fax: Optional[str] = None
    homepage: Optional[str] = None


class InstitutionDataResponse(InstitutionDataBase):
    idx: int
    model_config = ConfigDict(from_attributes=True)


class KsicNaceMappingBase(BaseModel):
    ksic_code: str = Field(description="KSIC 코드 (4자리)")
    nace_code: str = Field(description="FK → nace_codes")
    iaf_code: str = Field(description="중복 저장 (조회 최적화)")
    created_at: datetime


class KsicNaceMappingCreate(KsicNaceMappingBase):
    pass


class KsicNaceMappingUpdate(BaseModel):
    ksic_code: Optional[str] = None
    nace_code: Optional[str] = None
    iaf_code: Optional[str] = None
    created_at: Optional[datetime] = None


class KsicNaceMappingResponse(KsicNaceMappingBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class MasterIafCodesBase(BaseModel):
    iaf_code: str
    nace_code: Optional[str] = Field(default=None, description="NACE 중분류 코드 (03A, 03B...)")
    ksic_codes: Optional[str] = Field(default=None, description="KSIC 코드 목록 (콤마 구분)")
    name_kr: str
    name_en: str
    scope_name_ko: Optional[str] = None
    complexity_qms: Optional[str] = None
    complexity_ems: Optional[str] = None
    complexity_ohsms: Optional[str] = None
    risk_9001: Optional[MasterIafCodesRisk9001] = None
    risk_14001: Optional[MasterIafCodesRisk14001] = None
    risk_45001: Optional[MasterIafCodesRisk45001] = None
    sector: Optional[str] = None
    is_active: bool


class MasterIafCodesCreate(MasterIafCodesBase):
    pass


class MasterIafCodesUpdate(BaseModel):
    iaf_code: Optional[str] = None
    nace_code: Optional[str] = None
    ksic_codes: Optional[str] = None
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    scope_name_ko: Optional[str] = None
    complexity_qms: Optional[str] = None
    complexity_ems: Optional[str] = None
    complexity_ohsms: Optional[str] = None
    risk_9001: Optional[MasterIafCodesRisk9001] = None
    risk_14001: Optional[MasterIafCodesRisk14001] = None
    risk_45001: Optional[MasterIafCodesRisk45001] = None
    sector: Optional[str] = None
    is_active: Optional[bool] = None


class MasterIafCodesResponse(MasterIafCodesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MasterIafSubCodesBase(BaseModel):
    iaf_code: str = Field(description="IAF 대분류 코드 (01~39)")
    sub_code: str = Field(description="IAF 세분류 코드 (03A, 14B 등)")
    sub_name_ko: str = Field(description="세분류 한국어명")
    complexity_qms: Optional[str] = Field(default=None, description="QMS 복잡성 (높음/중간/낮음/제한/특별)")
    complexity_ems: Optional[str] = Field(default=None, description="EMS 복잡성")
    complexity_ohsms: Optional[str] = Field(default=None, description="OHSMS 복잡성")
    is_active: Optional[bool] = None


class MasterIafSubCodesCreate(MasterIafSubCodesBase):
    pass


class MasterIafSubCodesUpdate(BaseModel):
    iaf_code: Optional[str] = None
    sub_code: Optional[str] = None
    sub_name_ko: Optional[str] = None
    complexity_qms: Optional[str] = None
    complexity_ems: Optional[str] = None
    complexity_ohsms: Optional[str] = None
    is_active: Optional[bool] = None


class MasterIafSubCodesResponse(MasterIafSubCodesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MasterKsicIafBase(BaseModel):
    ksic_code: str = Field(description="KSIC 5자리 세분류")
    ksic_name: Optional[str] = None
    iaf_code: str = Field(description="IAF 코드 1~39")


class MasterKsicIafCreate(MasterKsicIafBase):
    pass


class MasterKsicIafUpdate(BaseModel):
    ksic_code: Optional[str] = None
    ksic_name: Optional[str] = None
    iaf_code: Optional[str] = None


class MasterKsicIafResponse(MasterKsicIafBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MasterNaceCodesBase(BaseModel):
    division: str = Field(description="2자리 부문코드 (예: 01, 35)")
    section: str = Field(description="A~U 섹션")
    section_name_ko: str = Field(description="섹션 한국어명")
    name_ko: str
    name_en: str
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MasterNaceCodesCreate(MasterNaceCodesBase):
    pass


class MasterNaceCodesUpdate(BaseModel):
    division: Optional[str] = None
    section: Optional[str] = None
    section_name_ko: Optional[str] = None
    name_ko: Optional[str] = None
    name_en: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class MasterNaceCodesResponse(MasterNaceCodesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MdCalculationRulesBase(BaseModel):
    cb_id: int
    employee_min: int
    employee_max: Optional[int] = None
    base_md: Decimal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MdCalculationRulesCreate(MdCalculationRulesBase):
    pass


class MdCalculationRulesUpdate(BaseModel):
    cb_id: Optional[int] = None
    employee_min: Optional[int] = None
    employee_max: Optional[int] = None
    base_md: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MdCalculationRulesResponse(MdCalculationRulesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class MdqmsTechnicalAreasBase(BaseModel):
    area_code: str = Field(description="A.1.1~A.4")
    area_name_ko: str
    area_name_en: str
    parent_code: Optional[str] = Field(default=None, description="상위 영역")
    risk_class: Optional[str] = Field(default=None, description="Class I/II/III")
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class MdqmsTechnicalAreasCreate(MdqmsTechnicalAreasBase):
    pass


class MdqmsTechnicalAreasUpdate(BaseModel):
    area_code: Optional[str] = None
    area_name_ko: Optional[str] = None
    area_name_en: Optional[str] = None
    parent_code: Optional[str] = None
    risk_class: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class MdqmsTechnicalAreasResponse(MdqmsTechnicalAreasBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class NaceCodesBase(BaseModel):
    nace_code: str = Field(description="NACE 코드 (03A, 03B...)")
    iaf_code: str = Field(description="FK → iaf_codes")
    name_kr: str
    name_en: str
    risk_9001: Optional[NaceCodesRisk9001] = None
    risk_14001: Optional[NaceCodesRisk14001] = None
    risk_45001: Optional[NaceCodesRisk45001] = None
    is_active: bool
    created_at: datetime


class NaceCodesCreate(NaceCodesBase):
    pass


class NaceCodesUpdate(BaseModel):
    nace_code: Optional[str] = None
    iaf_code: Optional[str] = None
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    risk_9001: Optional[NaceCodesRisk9001] = None
    risk_14001: Optional[NaceCodesRisk14001] = None
    risk_45001: Optional[NaceCodesRisk45001] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class NaceCodesResponse(NaceCodesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class QualificationBodiesBase(BaseModel):
    code: str
    name_kr: str
    name_en: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    is_official: Optional[bool] = Field(default=None, description="공식 등록 기관 여부")
    is_verified: Optional[bool] = Field(default=None, description="운영자 검증 여부 (직접입력=0)")
    is_active: Optional[bool] = None
    note: Optional[str] = Field(default=None, description="직접입력 시 원본 텍스트 또는 비고")
    created_at: datetime
    updated_at: datetime


class QualificationBodiesCreate(QualificationBodiesBase):
    pass


class QualificationBodiesUpdate(BaseModel):
    code: Optional[str] = None
    name_kr: Optional[str] = None
    name_en: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    is_official: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class QualificationBodiesResponse(QualificationBodiesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class StandardClausesBase(BaseModel):
    clause_id: str
    standard_code: str
    group_name: Optional[str] = None
    label: Optional[str] = None
    question: Optional[str] = None
    checkpoints: Optional[str] = None
    kpi_refs: Optional[str] = None
    min_completion: Optional[int] = None
    esg_tags: Optional[str] = None
    sort_order: Optional[int] = None
    created_at: datetime


class StandardClausesCreate(StandardClausesBase):
    pass


class StandardClausesUpdate(BaseModel):
    clause_id: Optional[str] = None
    standard_code: Optional[str] = None
    group_name: Optional[str] = None
    label: Optional[str] = None
    question: Optional[str] = None
    checkpoints: Optional[str] = None
    kpi_refs: Optional[str] = None
    min_completion: Optional[int] = None
    esg_tags: Optional[str] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None


class StandardClausesResponse(StandardClausesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class StandardProcessesBase(BaseModel):
    process_id: str
    label: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    clause_ids: Optional[str] = None
    esg_tags: Optional[str] = None
    sort_order: Optional[int] = None
    created_at: datetime


class StandardProcessesCreate(StandardProcessesBase):
    pass


class StandardProcessesUpdate(BaseModel):
    process_id: Optional[str] = None
    label: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    clause_ids: Optional[str] = None
    esg_tags: Optional[str] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None


class StandardProcessesResponse(StandardProcessesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
