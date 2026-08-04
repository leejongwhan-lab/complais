"""KSIC/IAF 및 전공학과 매핑 ORM 모델 (부속서 1·2 기준)."""
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text

from app.core.database import Base


class KsicIafMapping(Base):
    """
    한국표준산업분류(KSIC) ↔ IAF 코드 및 심사 복잡도 매핑 테이블
    """
    __tablename__ = "ksic_iaf_mappings"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    ksic_code = Column(String(10), nullable=False, index=True, comment="KSIC 코드 (예: 2611)")
    iaf_code = Column(String(10), nullable=False, index=True, comment="IAF 코드 (예: 19B)")
    iaf_name_ko = Column(String(100), nullable=False, comment="IAF 국문명")
    iaf_name_en = Column(String(100), nullable=True, comment="IAF 영문명")

    # 심사 복잡도 (부속서 1 / IAF ID1 기준)
    qms_complexity = Column(String(20), nullable=True, comment="QMS 복잡도 (높음/중간/낮음)")
    ems_complexity = Column(String(20), nullable=True, comment="EMS 복잡도 (높음/중간/낮음/제한)")
    ohsms_complexity = Column(String(20), nullable=True, comment="OHSMS 복잡도 (높음/중간/낮음)")

    description = Column(Text, nullable=True, comment="세부분류 및 비고")


class MajorIafMapping(Base):
    """
    전공학과 ↔ IAF 코드 매핑 테이블 (부속서 2 기준)
    """
    __tablename__ = "major_iaf_mappings"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    major_name = Column(String(100), nullable=False, index=True, comment="전공학과명/키워드 (예: 기계공학)")
    iaf_code = Column(String(10), nullable=False, index=True, comment="매핑/추천 IAF 코드 (예: 18)")
    degree_level = Column(String(20), default="BACHELOR_4Y", comment="요구 학력 수준")

    # 부속서 2 단서조항(제한사항) 관리 필드
    is_mandatory = Column(Boolean, default=True, comment="전공만으로 즉시 부여 가능 여부")
    extra_exp_years = Column(Integer, default=0, comment="추가 필수 실무경력 년수 (예: 의약/원자력 3년)")
    requires_committee = Column(Boolean, default=False, comment="자격인증위원회 심의 필요 여부 (예: 기타제조업 23번)")

    notes = Column(Text, nullable=True, comment="인정/제한 규정 요약 설명")
