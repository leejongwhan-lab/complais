"""ESG master KPI models (enterprise evaluation catalog).

Distinct from legacy `esg_master` / `kpi_master` tables.
`managed_standard_name` stores the official management-standard label (DDL: 14대).
Platform `standard_masters` holds operating 14 versioned ISO codes (+ META); do not force FK.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import ENUM as MySQLEnum
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EsgMasterKpi(Base):
    """ESG 마스터 KPI — 관리표준·조항·추출방식 연계 카탈로그."""

    __tablename__ = "esg_master_kpis"

    kpi_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    esg_category: Mapped[str] = mapped_column(
        MySQLEnum("E", "S", "G", name="esg_master_kpi_category"),
        nullable=False,
    )
    sub_category: Mapped[str] = mapped_column(String(100), nullable=False)
    kpi_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_quantitative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unit_format: Mapped[str] = mapped_column(String(50), nullable=False)

    managed_standard_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="14대 공식 관리 표준명",
    )
    iso_clause_detail: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="세부 조항 번호 (예: 6.1.2 환경측면)",
    )
    is_iso_auditable: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=True,
        comment="ISO 심사 검증 가능 여부",
    )

    source_type_code: Mapped[str] = mapped_column(String(20), nullable=False)
    extraction_detail_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="A-1 ~ C-2 7단계 상세 추출 방식",
    )
    is_public_api_available: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
    )
    criteria_mapping: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="ISO/기준 매핑 · 데이터 경로 표시용",
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CompanyEsgKpiGoal(Base):
    """기업별 ESG KPI 목표값 (목표설정)."""

    __tablename__ = "company_esg_kpi_goals"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "kpi_id", "target_year", name="uq_company_esg_kpi_goal_year"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("esg_master_kpis.kpi_id", ondelete="CASCADE"), nullable=False
    )
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CompanyEsgKpiValue(Base):
    """기업별 ESG KPI 연도 값 — 기업 직접입력(당해) 또는 심사원 작성."""

    __tablename__ = "company_esg_kpi_values"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "kpi_id", "year", name="uq_company_esg_kpi_value_year"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("esg_master_kpis.kpi_id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    source_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="company", comment="company | auditor | public"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CompanyEsgAuditNote(Base):
    """ESG KPI 심사노트 (심사원 작성 · 기업 열람)."""

    __tablename__ = "company_esg_audit_notes"
    __table_args__ = (
        UniqueConstraint("company_id", "kpi_id", name="uq_company_esg_audit_note_kpi"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("esg_master_kpis.kpi_id", ondelete="CASCADE"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    auditor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
