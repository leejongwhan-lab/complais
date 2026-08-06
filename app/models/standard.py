"""ISO/KAB 표준 마스터 — 운영 14규격 + META(COMMON/IMS).

매핑·저장은 항상 ``standard_key`` (예: QMS_2015) 를 사용한다.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class StandardMaster(Base):
    """인증 표준 마스터 (운영 14 + META).

    용어
    ----
    standard_key  : 고유키 QMS_2015 (FK/매핑 기준)
    family_code   : KAB 이니셜 QMS/EMS/…
    edition_year  : 판본 연도
    iso_number    : ISO 9001 (연도 없음)
    display_code  : ISO 9001:2015 (화면 표기)
    standard_code : display_code 와 동일 (레거시 시드 호환)
    standard_name : 국문 명칭
    clauses_status: READY | PENDING
    """

    __tablename__ = "standard_masters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    standard_key = Column(String(40), nullable=False, unique=True, index=True)
    family_code = Column(String(20), nullable=False, index=True)
    edition_year = Column(Integer, nullable=True, index=True)
    iso_number = Column(String(40), nullable=False)
    display_code = Column(String(60), nullable=False)
    # 레거시 seed_standards.py / 기존 코드 호환
    standard_code = Column(String(60), nullable=False, unique=True, index=True)
    standard_name = Column(String(100), nullable=False)
    version_year = Column(Integer, nullable=True)  # = edition_year (호환)
    clauses_status = Column(String(20), nullable=False, default="READY")
    clauses_note = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="CERTIFIABLE")
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    clauses = relationship(
        "StandardClause",
        back_populates="standard",
        cascade="all, delete-orphan",
    )


class StandardClause(Base):
    """표준별 세부 조항.

    QMS_2026 / EMS_2026 은 clauses_status=PENDING 이라 조항이 비어 있을 수 있다.
    레거시 ``standard_clauses``(체크리스트)와 분리: ``standard_clause_masters``.
    """

    __tablename__ = "standard_clause_masters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    standard_id = Column(
        Integer,
        ForeignKey("standard_masters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_number = Column(String(30), nullable=False, index=True)
    clause_title_kr = Column(String(255), nullable=False, default="")
    depth = Column(Integer, default=1, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    requirements_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    standard = relationship("StandardMaster", back_populates="clauses")
    process_mappings = relationship(
        "ProcessClauseMapping",
        back_populates="clause",
        cascade="all, delete-orphan",
    )
    notes = relationship("AuditNote", back_populates="clause")
    ncrs = relationship("AuditNCR", back_populates="clause")

    __table_args__ = (
        UniqueConstraint("standard_id", "clause_number", name="uix_standard_clause_number"),
    )


class StandardProcess(Base):
    """표준 프로세스 마스터."""

    __tablename__ = "standard_process_masters"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    process_code = Column(String(30), nullable=False, unique=True, index=True)
    process_name_kr = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    clause_mappings = relationship(
        "ProcessClauseMapping",
        back_populates="process",
        cascade="all, delete-orphan",
    )


class ProcessClauseMapping(Base):
    """프로세스 ↔ 조항 N:M."""

    __tablename__ = "process_clause_mappings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    process_id = Column(
        Integer,
        ForeignKey("standard_process_masters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clause_id = Column(
        Integer,
        ForeignKey("standard_clause_masters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, server_default=func.now())

    process = relationship("StandardProcess", back_populates="clause_mappings")
    clause = relationship("StandardClause", back_populates="process_mappings")

    __table_args__ = (
        UniqueConstraint("process_id", "clause_id", name="uix_process_clause_mapping"),
    )
