"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

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
