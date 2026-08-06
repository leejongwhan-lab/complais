"""심사 신청건별 MD(Man-Day) 산출 및 행정 가감 검토 모델.

레거시 certification_application_md_reviews / certification_application_review_logs
테이블을 정규화하여, master_data 기반 신규 심사 신청 모델(AuditApplication)에
FK로 연결한다.
"""
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AuditMdReview(Base):
    """
    ISO 인증 신청건별 MD 산출 및 행정 가감 검토 테이블
    (레거시 certification_application_md_reviews 대응)
    """
    __tablename__ = "audit_md_reviews"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # 신청서 참조 (1:1 또는 최신 1건 매핑)
    application_id = Column(BigInteger, ForeignKey("audit_applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # 1. 자동 산정 영역 (MD 계산기 산출 스냅샷)
    base_md = Column(Float, nullable=False, default=0.0, comment="계산기 기준 자동 산정 기본 MD")
    base_md_detail_json = Column(JSON, nullable=True, comment="계산기 엔진 로그 스냅샷 (_lastCalcLog)")
    base_md_calculated_at = Column(DateTime(timezone=True), nullable=True)
    base_md_calculated_by = Column(BigInteger, nullable=True, comment="계산 수행 유저 ID")

    # 2. 행정 가감 검토 영역 (심사원/행정직원 조정)
    add_pct = Column(Integer, nullable=False, default=0, comment="가산 비율 (%)")
    subtract_pct = Column(Integer, nullable=False, default=0, comment="감산 비율 (%)")
    add_md = Column(Float, nullable=False, default=0.0, comment="가산 MD")
    subtract_md = Column(Float, nullable=False, default=0.0, comment="감산 MD")
    final_md = Column(Float, nullable=False, default=0.0, comment="최종 확정 MD")
    calculation_note = Column(Text, nullable=True, comment="가감 사유 및 인용 조항 메모")

    # 3. 검토 이력 정보
    reviewer_user_id = Column(BigInteger, nullable=True, comment="최종 검토/승인자 ID")
    reviewer_role = Column(String(50), nullable=True, comment="검토자 역할")
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    application = relationship("AuditApplication", back_populates="md_review")
    review_logs = relationship("AuditMdReviewLog", back_populates="md_review", cascade="all, delete-orphan")


class AuditMdReviewLog(Base):
    """
    MD 검토 상태 변경 및 저장 히스토리 로그
    (레거시 certification_application_review_logs 대응)
    """
    __tablename__ = "audit_md_review_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    md_review_id = Column(BigInteger, ForeignKey("audit_md_reviews.id", ondelete="CASCADE"), nullable=False, index=True)

    actor_user_id = Column(BigInteger, nullable=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(50), nullable=False, comment="save_md, under_review, approved 등")
    before_status = Column(String(50), nullable=True)
    after_status = Column(String(50), nullable=True)
    memo = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    md_review = relationship("AuditMdReview", back_populates="review_logs")
