"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class Invitations(Base):
    __tablename__ = "invitations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    invited_by: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Notifications(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Tenants(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_type: Mapped[str] = mapped_column(String(50), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    activated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    max_auditors: Mapped[int] = mapped_column(Integer, nullable=False)
    max_contracts_pm: Mapped[int] = mapped_column(Integer, nullable=False)
    base_fee: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, comment="기본금(인증기관) / 월구독료(컨설팅)")
    per_auditor_fee: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, comment="심사원 1인당 단가(인증기관)")
    current_auditors: Mapped[int] = mapped_column(Integer, nullable=False, comment="현재 등록 심사원 수")
    credit_balance: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="크레딧 잔액(교육기관)")
    credit_per_day: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="홍보 노출 1일당 차감 크레딧")
    consulting_fee: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, comment="컨설팅 월구독료")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    member_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    complais_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="ComplAIs 개인번호 (YYYYMMDD-NNN)")
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    # 소속(CB/기업) 승인 상태
    membership_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="approved", comment="approved, pending, rejected"
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="승인해 준 대표계정 user_id"
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
