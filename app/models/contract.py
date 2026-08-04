"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base



class Contracts(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(50), nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    proposal_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lead_auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    verifier_auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    member_auditor_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observer_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    standards: Mapped[str] = mapped_column(Text, nullable=False)
    scope_kr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audit_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    audit_period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_stage: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_md: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    agreed_amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    note_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    report_issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cert_issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cert_expiry_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    audit_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    fee_audit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_travel: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_other: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    travel_policy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fee_report: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_application: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applied_standards: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cb_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    client_signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    client_signed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cb_signed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cb_signed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audit_mode: Mapped[str] = mapped_column(String(50), nullable=False)


class Contract(Base):
    """
    심사 계약 (master_data 기반 신규 심사 신청 모델과 정규화 연결).
    레거시 `Contracts`(contracts 테이블, cb_id/company_id 등 느슨한 정수 참조)와 별도로,
    `AuditApplication`을 FK로 참조하는 신규 정규화 계약 레코드.
    """
    __tablename__ = "audit_contracts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    application_id = Column(BigInteger, ForeignKey("audit_applications.id", ondelete="CASCADE"), nullable=False, index=True)

    contract_no = Column(String(50), unique=True, nullable=True, comment="계약 번호")
    audit_type = Column(String(50), nullable=False, comment="INITIAL/SURVEILLANCE1/SURVEILLANCE2/RENEWAL 등")
    standards = Column(Text, nullable=True, comment="적용 표준 목록 (콤마구분 또는 JSON)")
    scope_kr = Column(Text, nullable=True)
    scope_en = Column(Text, nullable=True)

    audit_period_start = Column(Date, nullable=True)
    audit_period_end = Column(Date, nullable=True)

    total_md = Column(Float, nullable=True, comment="계약 확정 총 MD (AuditMdReview.final_md 스냅샷)")
    agreed_amount = Column(Numeric(15, 2), nullable=True, comment="계약 확정 금액")

    # 고액 계약 공제 기준 (settlement_calculator.calculate_contract_settlement 연동, 하드코딩 금지)
    high_value_threshold = Column(Float, nullable=True, default=0.0, comment="고액 공제 기준 금액 (0 또는 NULL이면 미적용)")
    high_value_deduction_rate = Column(Float, nullable=True, default=0.0, comment="고액 공제 비율 (5.0=5% 또는 0.05)")

    status = Column(String(50), nullable=False, default="DRAFT", comment="DRAFT/SENT/SIGNED/CANCELLED 등")
    signed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    application = relationship("AuditApplication", back_populates="contracts")
    assignments = relationship("AuditAssignment", back_populates="contract")


class AuditAssignment(Base):
    """
    심사 신청건별 심사원 배정 (master_data 기반 신규 심사 신청 모델과 정규화 연결).
    레거시 `AuditAssignments`(audit_assignments 테이블, 느슨한 정수 참조)와 별도로,
    `AuditApplication` 및 `auditors`를 FK로 참조하는 신규 정규화 배정 레코드.
    """
    __tablename__ = "audit_application_assignments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    application_id = Column(BigInteger, ForeignKey("audit_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id = Column(BigInteger, ForeignKey("audit_contracts.id", ondelete="SET NULL"), nullable=True, comment="배정이 귀속된 계약 (선택)")

    role = Column(String(30), nullable=False, default="MEMBER", comment="LEAD/MEMBER/OBSERVER/WITNESS")
    status = Column(String(30), nullable=False, default="ASSIGNED", comment="ASSIGNED/CONFIRMED/DECLINED/COMPLETED")

    assigned_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False)

    application = relationship("AuditApplication", back_populates="assignments")
    auditor = relationship("Auditor", back_populates="assignments")
    contract = relationship("Contract", back_populates="assignments")
