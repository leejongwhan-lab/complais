"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class Companies(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cert_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="ComplAIs 기업번호 (100001~)")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    biz_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    corp_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ceo_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    biz_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="업태")
    biz_class: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="업종")
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    detail_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    iaf_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ksic_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scope_kr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # --- 백오피스 마스터 확장 컬럼 (개인/법인 구분, MD 산출용 인원, 세금계산서 담당자) ---
    entity_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="개인/법인")
    headcount_regular: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="정규직 인원")
    headcount_non_regular: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="비정규직 인원")
    headcount_outsourced: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="외주 인원")
    headcount_certified: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="표준별 유효인원")
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="정상/휴업/폐업/인증취소")
    tax_contact_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="세금계산서 담당자명")
    tax_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="세금계산서 수신 이메일")


class CompanyBranches(Base):
    __tablename__ = "company_branches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    scope_kr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanyDocuments(Base):
    __tablename__ = "company_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_id: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    revision: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    iso_clauses: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    access_level: Mapped[str] = mapped_column(String(50), nullable=False)
    review_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanyKpiSelection(Base):
    __tablename__ = "company_kpi_selection"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_code: Mapped[str] = mapped_column(String(20), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanyKpiTargets(Base):
    __tablename__ = "company_kpi_targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_id: Mapped[str] = mapped_column(String(50), nullable=False)
    value_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CompanyProcesses(Base):
    __tablename__ = "company_processes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    process_code: Mapped[str] = mapped_column(String(2), nullable=False)
    process_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class CompanySites(Base):
    """추가 사업장 (Multi-site, company_id -> companies.id FK)."""
    __tablename__ = "company_sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    site_name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    biz_no: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, nullable=False)
    work_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="사업장 업무 형태/업종")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanySuppliers(Base):
    __tablename__ = "company_suppliers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    supplier_biz_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    supply_item: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
