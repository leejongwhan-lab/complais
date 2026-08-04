# app/models/master_data.py
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
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
    """IAF (인증분류) 마스터"""
    __tablename__ = "iaf_codes"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True, comment="IAF 코드 (예: 19, 19B, 33)")
    name_ko = Column(String(100), nullable=False, comment="국문 범주명")
    name_en = Column(String(100), nullable=True, comment="영문 범주명")

    # Relationships
    ksic_mappings = relationship("KsicIafMapping", back_populates="iaf")
    major_mappings = relationship("MajorIafMapping", back_populates="iaf")


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
