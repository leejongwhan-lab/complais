"""기업(Client) 인증 신청 설문/심사주기 모델.

명세의 `clients` 는 본 프로젝트의 `companies` 테이블에 매핑한다.
`audit_requests` 는 차수별 설문 이력과 심사 주기를 보관한다.
"""
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditRequest(Base):
    """인증 심사 신청 + 설문 응답 이력 (1건 = 1차수)."""

    __tablename__ = "audit_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="신청 기업(clients)",
    )
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id"),
        nullable=False,
        index=True,
    )
    applicant_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    iso_standards: Mapped[Any] = mapped_column(JSON, nullable=False, comment='["ISO 9001", ...]')
    audit_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="initial",
        comment="initial|surveillance|recertification|special",
    )
    audit_cycle_months: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=12,
        comment="6 또는 12",
    )
    survey_responses: Mapped[Optional[Any]] = mapped_column(
        JSON,
        nullable=True,
        comment="공통+표준별 설문 응답",
    )
    previous_request_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("audit_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="submitted",
        index=True,
    )
    application_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="신청번호"
    )
    preferred_start_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="희망 심사 시작일"
    )
    process_step: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, comment="1제안서~7종료"
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    previous_request = relationship(
        "AuditRequest",
        remote_side=[id],
        foreign_keys=[previous_request_id],
        uselist=False,
    )
