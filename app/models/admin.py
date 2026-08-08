"""플랫폼 운영/관리자 도메인 모델.

CB 연간 계약·과금 정책(CBContract), 동적 계산식 마스터(PlatformCalculationRule),
CB 인정서 및 ISO/IAF 승인 범위(CBAccreditation, CBAccreditedScope)를 정의한다.

주의(테이블명 분리):
- 레거시 `CbAccreditations`(app/models/cb.py, 테이블 cb_accreditations)와 이름이 겹치지만
  필드 구성이 전혀 다른(인정서 파일 업로드 + 승인/반려 워크플로우) 별개 스키마이므로,
  `standard_clause_masters` 등과 동일한 규칙에 따라 테이블명을 `cb_accreditation_records`로 분리한다.
- 레거시 `CbAccreditationScopes`(app/models/cb.py, 테이블 cb_accreditation_scopes)와 이름이
  혼동되기 쉬우므로, 테이블명을 `cb_accreditation_record_scopes`로 분리한다.
"""
from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


class CBTier(str, enum.Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    ENTERPRISE = "ENTERPRISE"


class CBAccreditationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# 1. CB 연간 계약 및 과금 정책
class CBContract(Base):
    __tablename__ = "cb_contracts"

    id = Column(Integer, primary_key=True, index=True)
    # certification_bodies.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
    cb_id = Column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id"), nullable=False, index=True)
    contract_year = Column(Integer, nullable=False, default=2026)
    tier = Column(String(20), default=CBTier.MEDIUM.value)
    annual_base_fee = Column(Numeric(12, 0), nullable=False, default=0)  # 연간 기본금
    price_per_md = Column(Numeric(10, 0), nullable=False, default=0)    # MD당 단가
    contract_start_date = Column(DateTime, nullable=False)
    contract_end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# 2. 동적 계산식 및 산출 지침 마스터 (MD계산기, 탄소배출량 등)
class PlatformCalculationRule(Base):
    __tablename__ = "platform_calculation_rules"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # AUDIT_MD, CARBON_EMISSION, ESG_INDEX
    rule_code = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    formula_expression = Column(Text, nullable=True)  # 수식 표현
    variables_json = Column(JSON, nullable=True)      # 계수 및 변수 테이블
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 3. CB 인정서 및 ISO/IAF 승인 범위
class CBAccreditation(Base):
    __tablename__ = "cb_accreditation_records"

    id = Column(Integer, primary_key=True, index=True)
    cb_id = Column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id"), nullable=False, index=True)
    accreditation_body = Column(String(100), nullable=False)  # KAB, ANAB 등
    certificate_number = Column(String(100), nullable=False)
    certificate_file_url = Column(String(500), nullable=True)
    status = Column(String(20), default=CBAccreditationStatus.PENDING.value)
    reject_reason = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)

    scopes = relationship("CBAccreditedScope", back_populates="accreditation", cascade="all, delete-orphan")


class CBAccreditedScope(Base):
    __tablename__ = "cb_accreditation_record_scopes"

    id = Column(Integer, primary_key=True, index=True)
    cb_accreditation_id = Column(
        Integer, ForeignKey("cb_accreditation_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    iso_standard_id = Column(Integer, ForeignKey("standard_masters.id"), nullable=False, index=True)
    iaf_code = Column(String(50), nullable=False)  # EAC/IAF 코드 (e.g. Code 14)
    is_approved = Column(Boolean, default=False)
    # Per-scope workflow (default PENDING). APPROVED/REJECTED after admin action.
    status = Column(String(20), default=CBAccreditationStatus.PENDING.value)
    reject_reason = Column(Text, nullable=True)

    accreditation = relationship("CBAccreditation", back_populates="scopes")
    standard = relationship("StandardMaster")
