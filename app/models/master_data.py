# app/models/master_data.py
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# --- [ 마스터 테이블 정의 ] ---

class KsicCode(Base):
    """KSIC (한국표준산업분류) 마스터"""
    __tablename__ = "ksic_codes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True, comment="KSIC 코드 (예: 26110, 6202)")
    name_ko = Column(String(150), nullable=False, comment="국문 업종명")
    name_en = Column(String(150), nullable=True, comment="영문 업종명")
    digit_level = Column(Integer, default=5, comment="코드 자릿수 (3: 소분류, 4: 세분류, 5: 세세분류)")

    # Relationships
    iaf_mappings = relationship("KsicIafMapping", back_populates="ksic")


class IafCode(Base):
    """IAF (인증분류) 마스터 — 개정/폐기에 대비해 독립 관리."""

    __tablename__ = "iaf_codes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)  # iaf_code_id
    code = Column(String(20), unique=True, nullable=False, index=True, comment="IAF 코드 (예: 01, 14, 19)")
    name_ko = Column(String(255), nullable=False, comment="산업 분야명(국문)")
    name_en = Column(String(100), nullable=True, comment="영문 범주명")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, comment="코드 유효 여부")
    updated_at = Column(DateTime, nullable=True)

    # Relationships
    ksic_mappings = relationship("KsicIafMapping", back_populates="iaf")
    major_mappings = relationship("MajorIafMapping", back_populates="iaf")
    accredited_scopes = relationship("CbAccreditedScope", back_populates="iaf_code")


class IsoStandard(Base):
    """ISO 인증 표준 마스터 (인정 Scope용 · 운영 14규격).

    standard_key  : QMS_2015 등 — standard_masters / 매핑과 동일 키
    standard_code : display_code (ISO 9001:2015) — 화면·레거시 호환
    """

    __tablename__ = "iso_standards"

    id = Column(Integer, primary_key=True, autoincrement=True)  # standard_id
    standard_key = Column(String(40), unique=True, nullable=True, index=True, comment="예: QMS_2015")
    standard_code = Column(String(50), unique=True, nullable=False, comment="예: ISO 9001:2015")
    standard_name_ko = Column(String(255), nullable=False, comment="표준명(국문)")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

    accredited_scopes = relationship("CbAccreditedScope", back_populates="standard")


class CbAccreditedScope(Base):
    """CB 자격 Scope — CB × 표준(1) × IAF(1) 행 단위 매핑."""

    __tablename__ = "cb_accredited_scopes"
    __table_args__ = (
        UniqueConstraint("cb_id", "standard_id", "iaf_code_id", name="uk_cb_standard_iaf"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)  # scope_id
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    standard_id: Mapped[int] = mapped_column(ForeignKey("iso_standards.id"), nullable=False)
    iaf_code_id: Mapped[int] = mapped_column(ForeignKey("iaf_codes.id"), nullable=False)
    accreditation_body: Mapped[str] = mapped_column(String(100), nullable=False, default="KAB")
    approval_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    standard = relationship("IsoStandard", back_populates="accredited_scopes")
    iaf_code = relationship("IafCode", back_populates="accredited_scopes")


class Major(Base):
    """전공학과 마스터"""
    __tablename__ = "majors"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="전공학과명")
    category = Column(String(50), nullable=True, comment="계열 (예: 이공계열, 인문사회계열)")

    # Relationships
    iaf_mappings = relationship("MajorIafMapping", back_populates="major")


# --- [ 매핑/관계 테이블 정의 ] ---

class KsicIafMapping(Base):
    """KSIC ↔ IAF 매핑 및 복잡도 관리 (부속서 1)"""
    __tablename__ = "ksic_iaf_mappings"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    ksic_id = Column(BigInteger, ForeignKey("ksic_codes.id", ondelete="CASCADE"), nullable=False)
    iaf_id = Column(BigInteger, ForeignKey("iaf_codes.id", ondelete="CASCADE"), nullable=False)

    qms_complexity = Column(String(20), nullable=True, comment="QMS 복잡도 (높음/중간/낮음/제한)")
    ems_complexity = Column(String(20), nullable=True, comment="EMS 복잡도")
    ohsms_complexity = Column(String(20), nullable=True, comment="OHSMS 복잡도")

    # Relationships
    ksic = relationship("KsicCode", back_populates="iaf_mappings")
    iaf = relationship("IafCode", back_populates="ksic_mappings")


class MajorIafMapping(Base):
    """전공 ↔ IAF 매핑 및 부속서 2 단서조항 관리"""
    __tablename__ = "major_iaf_mappings"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    major_id = Column(BigInteger, ForeignKey("majors.id", ondelete="CASCADE"), nullable=False)
    iaf_id = Column(BigInteger, ForeignKey("iaf_codes.id", ondelete="CASCADE"), nullable=False)

    degree_level = Column(String(20), default="BACHELOR_4Y", comment="학위 기준 (BACHELOR_4Y, MASTER, 등)")
    is_mandatory = Column(Boolean, default=True, comment="전공 인정 필수 여부")
    extra_exp_years = Column(Integer, default=0, comment="단서조항: 추가 실무경력 필요 년수")
    requires_committee = Column(Boolean, default=False, comment="단서조항: 자격인증위원회 심의 필요 여부")
    notes = Column(Text, nullable=True, comment="비고 및 부속서 2 근거 조항")

    # Relationships
    major = relationship("Major", back_populates="iaf_mappings")
    iaf = relationship("IafCode", back_populates="major_mappings")
