"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class KpiActuals(Base):
    __tablename__ = "kpi_actuals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    measured_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    measured_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    data_source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class KpiBenchmark(Base):
    __tablename__ = "kpi_benchmark"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="kpi_master.id")
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="IAF 업종코드")
    ref_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="기준연도")
    benchmark_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="업종 평균값")
    percentile_25: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    percentile_50: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    percentile_75: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="표본 기업 수")
    data_source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="출처 (공공API 등)")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class KpiMaster(Base):
    __tablename__ = "kpi_master"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kpi_key: Mapped[str] = mapped_column(String(50), nullable=False)
    kpi_code: Mapped[str] = mapped_column(String(20), nullable=False)
    category_esg: Mapped[str] = mapped_column(String(50), nullable=False)
    category_mid: Mapped[str] = mapped_column(String(100), nullable=False)
    name_kr: Mapped[str] = mapped_column(String(200), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    direction: Mapped[str] = mapped_column(String(50), nullable=False)
    frameworks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    applicable_stds: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    gri_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    k_esg_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    esrs_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    iso_clause: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    auto_collect: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    api_source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class KpiTargets(Base):
    __tablename__ = "kpi_targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    baseline_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
