"""IAF / KSIC master ORM models."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class IafCode(Base):
    """IAF 인정범위 마스터 테이블 (IAF 01 ~ 39)"""
    __tablename__ = "iaf_codes"

    sub_code = Column(String(10), primary_key=True, index=True)  # 예: '01A', '01B', '03A'
    iaf_code = Column(String(5), nullable=False, index=True)  # 예: '01', '02', '03'
    name_kr = Column(String(200), nullable=False)  # 국문 명칭
    name_en = Column(String(200), nullable=False)  # 영문 명칭

    # 표준별 복잡성 구분 (높음 / 중간 / 낮음)
    qms_complexity = Column(String(10), nullable=True)
    ems_complexity = Column(String(10), nullable=True)
    ohsms_complexity = Column(String(10), nullable=True)

    mappings = relationship(
        "KsicIafLink",
        back_populates="iaf_rel",
        cascade="all, delete-orphan",
    )


class KsicCode(Base):
    """한국표준산업분류(KSIC) 마스터 테이블"""
    __tablename__ = "ksic_codes"

    ksic_code = Column(String(10), primary_key=True, index=True)  # 4~5자리 KSIC 코드
    name_kr = Column(String(200), nullable=True)  # 업종명 (선택)

    mappings = relationship(
        "KsicIafLink",
        back_populates="ksic_rel",
        cascade="all, delete-orphan",
    )


class KsicIafLink(Base):
    """KSIC <-> IAF 정규화 연계 테이블 (iaf_codes / ksic_codes FK)."""
    __tablename__ = "ksic_iaf_mapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ksic_code = Column(
        String(10),
        ForeignKey("ksic_codes.ksic_code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sub_code = Column(
        String(10),
        ForeignKey("iaf_codes.sub_code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_primary = Column(Boolean, default=True)

    ksic_rel = relationship("KsicCode", back_populates="mappings")
    iaf_rel = relationship("IafCode", back_populates="mappings")
