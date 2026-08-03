"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class KarCpdRecords(Base):
    __tablename__ = "kar_cpd_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kar_qual_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hours: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class KarQualifications(Base):
    __tablename__ = "kar_qualifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qualification_body_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_body_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cert_doc_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    kar_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="KAR 자격번호")
    standard: Mapped[str] = mapped_column(String(100), nullable=False)
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    issued_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    iaf_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IAF 코드 (콤마구분)")
    mdqms_areas: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="ISO 13485 기술영역")
    nace_codes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="NACE Division 코드 (콤마구분)")


class KarRenewalRequests(Base):
    __tablename__ = "kar_renewal_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kar_qual_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    career_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cpd_hours: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    conflict_submitted: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    conduct_signed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class MaterialBalanceActuals(Base):
    __tablename__ = "material_balance_actuals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    measured_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    ghg_calc: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class MaterialBalanceItems(Base):
    __tablename__ = "material_balance_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_code: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_energy: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    api_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emission_factor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kpi_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class NcrReports(Base):
    __tablename__ = "ncr_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ncr_no: Mapped[str] = mapped_column(String(50), nullable=False)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="contracts.id")
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    nc_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    finding_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    issued_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class PopbillBizCache(Base):
    __tablename__ = "popbill_biz_cache"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    biz_no: Mapped[str] = mapped_column(String(20), nullable=False, comment="사업자등록번호")
    corp_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="기업명")
    ksic_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="KSIC 코드 (팝빌 industCode)")
    iaf_code: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, comment="IAF 코드 (KSIC→IAF 자동변환)")
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="팝빌 원본 응답 (JSON)")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="최초 조회일")


class PublicDataSnapshots(Base):
    __tablename__ = "public_data_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_org: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SupplierDueDiligence(Base):
    __tablename__ = "supplier_due_diligence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False)
    audited_by: Mapped[int] = mapped_column(Integer, nullable=False)
    dd_date: Mapped[date] = mapped_column(Date, nullable=False)
    human_rights: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False)
    safety: Mapped[str] = mapped_column(String(50), nullable=False)
    ethics: Mapped[str] = mapped_column(String(50), nullable=False)
    data_security: Mapped[str] = mapped_column(String(50), nullable=False)
    supply_chain: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
