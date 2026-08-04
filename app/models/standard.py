from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class StandardMaster(Base):
    """15개 ISO 표준 마스터 (예: ISO 9001:2015, ISO 14001:2026 등)"""
    __tablename__ = "standard_masters"

    id = Column(Integer, primary_key=True, index=True)
    standard_code = Column(String(50), nullable=False, unique=True, index=True)  # 예: 'ISO 9001:2015'
    standard_name = Column(String(100), nullable=False)                         # 예: '품질경영시스템'
    version_year = Column(Integer, nullable=False)                              # 예: 2015, 2026
    is_active = Column(Boolean, default=True, nullable=False)                   # 수정/활성화 여부
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    clauses = relationship("StandardClause", back_populates="standard", cascade="all, delete-orphan")


class StandardClause(Base):
    """표준별 세부 조항 (엑셀 원본 100% 매핑, 수정 가능).

    주의: 레거시 `StandardClauses`(app/models/master.py, 테이블 standard_clauses, 177건 실데이터
    보유)와 이름이 겹치지만 완전히 다른(체크리스트형) 스키마이므로, 테이블명을 분리해
    `standard_clause_masters`로 정규화한다.
    """
    __tablename__ = "standard_clause_masters"

    id = Column(Integer, primary_key=True, index=True)
    standard_id = Column(Integer, ForeignKey("standard_masters.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_number = Column(String(30), nullable=False, index=True)              # 예: '4.1', '6.1.2'
    clause_title_kr = Column(String(255), nullable=False)                       # 엑셀 기준 한글 조항 제목
    depth = Column(Integer, default=1, nullable=False)                           # 뎁스 (4 -> 1, 4.1 -> 2)
    sort_order = Column(Integer, default=0, nullable=False)
    requirements_summary = Column(Text, nullable=True)                          # 추가 수정 가능 요구사항 요약
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    standard = relationship("StandardMaster", back_populates="clauses")
    process_mappings = relationship("ProcessClauseMapping", back_populates="clause", cascade="all, delete-orphan")
    notes = relationship("AuditNote", back_populates="clause")
    ncrs = relationship("AuditNCR", back_populates="clause")

    __table_args__ = (
        UniqueConstraint('standard_id', 'clause_number', name='uix_standard_clause_number'),
    )


class StandardProcess(Base):
    """표준 프로세스 마스터 (아이콘 제거, 수정/확장 가능).

    주의: 레거시 `StandardProcesses`(app/models/master.py, 테이블 standard_processes, 16건 실데이터
    보유, clause_ids를 JSON 텍스트로 저장)와 이름이 겹치지만, N:M 매핑 테이블(ProcessClauseMapping)로
    정규화한 별개 스키마이므로 테이블명을 `standard_process_masters`로 분리한다.
    """
    __tablename__ = "standard_process_masters"

    id = Column(Integer, primary_key=True, index=True)
    process_code = Column(String(30), nullable=False, unique=True, index=True)  # 예: 'PRC_MGMT', 'PRC_RISK'
    process_name_kr = Column(String(100), nullable=False)                       # 예: '경영 및 전략 프로세스'
    description = Column(Text, nullable=True)                                   # 프로세스 설명
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    clause_mappings = relationship("ProcessClauseMapping", back_populates="process", cascade="all, delete-orphan")


class ProcessClauseMapping(Base):
    """프로세스 - ISO 표준 조항 N:M 매핑 테이블 (수정/재배치 가능)"""
    __tablename__ = "process_clause_mappings"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("standard_process_masters.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(Integer, ForeignKey("standard_clause_masters.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    process = relationship("StandardProcess", back_populates="clause_mappings")
    clause = relationship("StandardClause", back_populates="process_mappings")

    __table_args__ = (
        UniqueConstraint('process_id', 'clause_id', name='uix_process_clause_mapping'),
    )
