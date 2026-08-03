"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class AccreditationBodies(Base):
    __tablename__ = "accreditation_bodies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class DocumentNumbers(Base):
    __tablename__ = "document_numbers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(30), nullable=False)
    doc_no: Mapped[str] = mapped_column(String(60), nullable=False)
    ref_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class EmissionFactorMaster(Base):
    __tablename__ = "emission_factor_master"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fuel_code: Mapped[str] = mapped_column(String(20), nullable=False)
    fuel_name: Mapped[str] = mapped_column(String(100), nullable=False)
    fuel_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    factor_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    factor_co2: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    factor_ch4: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    factor_n2o: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    unit_input: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    scope_type: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    fuel_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="대분류")
    fuel_subcategory: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="중분류")
    source_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EsgMaster(Base):
    __tablename__ = "esg_master"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name_kr: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iso_clause: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IafNaceMap(Base):
    __tablename__ = "iaf_nace_map"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iaf_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="IAF 코드 (예: 01)")
    nace_division: Mapped[str] = mapped_column(String(2), nullable=False, comment="NACE Division (예: 01)")


class InstitutionData(Base):
    __tablename__ = "institutionData"
    idx: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="인덱스")
    korName: Mapped[str] = mapped_column(String(300), nullable=False, comment="인증기관 국문명")
    engName: Mapped[str] = mapped_column(String(300), nullable=False, comment="인증기관 영문명")
    abbreviation: Mapped[str] = mapped_column(String(30), nullable=False, comment="인증기관 약어")
    bizNumber: Mapped[str] = mapped_column(String(10), nullable=False, comment="사업자등록번호")
    president: Mapped[str] = mapped_column(String(100), nullable=False, comment="대표 이름")
    zipCode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="우편번호")
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="기본 주소")
    detailAddress: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="상세 주소")
    bank: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="은행 정보")
    bankAccount: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="은행 계좌")
    depositor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="예금주명")
    tel: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="대표전화")
    fax: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="팩스")
    homepage: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="홈페이지")


class KsicNaceMapping(Base):
    __tablename__ = "ksic_nace_mapping"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ksic_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="KSIC 코드 (4자리)")
    nace_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="FK → nace_codes")
    iaf_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="중복 저장 (조회 최적화)")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MasterIafCodes(Base):
    __tablename__ = "master_iaf_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    nace_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="NACE 중분류 코드 (03A, 03B...)")
    ksic_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="KSIC 코드 목록 (콤마 구분)")
    name_kr: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    scope_name_ko: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    complexity_qms: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    complexity_ems: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    complexity_ohsms: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    risk_9001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_14001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_45001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class MasterIafSubCodes(Base):
    __tablename__ = "master_iaf_sub_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    iaf_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="IAF 대분류 코드 (01~39)")
    sub_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="IAF 세분류 코드 (03A, 14B 등)")
    sub_name_ko: Mapped[str] = mapped_column(String(200), nullable=False, comment="세분류 한국어명")
    complexity_qms: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="QMS 복잡성 (높음/중간/낮음/제한/특별)")
    complexity_ems: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="EMS 복잡성")
    complexity_ohsms: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="OHSMS 복잡성")
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class MasterKsicIaf(Base):
    __tablename__ = "master_ksic_iaf"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ksic_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="KSIC 5자리 세분류")
    ksic_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    iaf_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="IAF 코드 1~39")


class MasterNaceCodes(Base):
    __tablename__ = "master_nace_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    division: Mapped[str] = mapped_column(String(2), nullable=False, comment="2자리 부문코드 (예: 01, 35)")
    section: Mapped[str] = mapped_column(String(2), nullable=False, comment="A~U 섹션")
    section_name_ko: Mapped[str] = mapped_column(String(100), nullable=False, comment="섹션 한국어명")
    name_ko: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class MdCalculationRules(Base):
    __tablename__ = "md_calculation_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_min: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    base_md: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class MdqmsTechnicalAreas(Base):
    __tablename__ = "mdqms_technical_areas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    area_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="A.1.1~A.4")
    area_name_ko: Mapped[str] = mapped_column(String(100), nullable=False)
    area_name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="상위 영역")
    risk_class: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="Class I/II/III")
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class NaceCodes(Base):
    __tablename__ = "nace_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nace_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="NACE 코드 (03A, 03B...)")
    iaf_code: Mapped[str] = mapped_column(String(5), nullable=False, comment="FK → iaf_codes")
    name_kr: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    risk_9001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_14001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_45001: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class QualificationBodies(Base):
    __tablename__ = "qualification_bodies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name_kr: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    is_official: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, comment="공식 등록 기관 여부")
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, comment="운영자 검증 여부 (직접입력=0)")
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="직접입력 시 원본 텍스트 또는 비고")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class StandardClauses(Base):
    __tablename__ = "standard_clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clause_id: Mapped[str] = mapped_column(String(20), nullable=False)
    standard_code: Mapped[str] = mapped_column(String(10), nullable=False)
    group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checkpoints: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kpi_refs: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    min_completion: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    esg_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class StandardProcesses(Base):
    __tablename__ = "standard_processes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    process_id: Mapped[str] = mapped_column(String(10), nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clause_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    esg_tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
