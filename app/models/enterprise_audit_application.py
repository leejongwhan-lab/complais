# DEPRECATED — 진짜 경로는 certification_applications + cb_cert_applications.py (enterprise_cert_applications). 삭제 예정(정리 후보). 오늘 작업에서 사용 금지.
"""기업 인증신청 MD 스냅샷 테이블 (enterprise_audit_applications).

주의: 기존 `audit_applications` 테이블/모델(`AuditApplication` in auditor.py)은
심사원 IAF 자격 신청용이다. 이름 충돌을 피하기 위해 본 테이블은
`enterprise_audit_applications` 로 분리하고, 사용자 DDL 컬럼명
(application_id, enterprise_id, …)을 그대로 따른다.

enterprise_id → companies.id (INT UNSIGNED)
cb_id → certification_bodies.id (INT UNSIGNED)
audit_request_id → audit_requests.id (optional link to 인증현황 flow)
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Enum, text
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EnterpriseAuditApplication(Base):
    """MD 엔진 산출 + CB 제안검토 스냅샷 (신청 이벤트당 1행)."""

    __tablename__ = "enterprise_audit_applications"

    application_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    enterprise_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="companies.id (명세 enterprise_id)",
    )
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id"),
        nullable=False,
        index=True,
    )
    audit_request_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("audit_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="기존 audit_requests / 인증현황 연동(선택)",
    )
    audit_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="INITIAL",
        index=True,
        comment="INITIAL|SURVEILLANCE_1|SURVEILLANCE_2|RECERT|TRANSFER|SPECIAL",
    )

    applied_standards: Mapped[Any] = mapped_column(
        JSON, nullable=False, comment='신청 및 보유 표준 목록 (예: ["ISO 9001"])'
    )
    ksic_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="KSIC 코드")
    iaf_scope_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="KSIC 매핑 IAF Scope")
    active_employee_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="신청 시점 종업원 수")

    complexity_level: Mapped[str] = mapped_column(
        Enum("HIGH", "MEDIUM", "LOW", "LIMITED", name="eaa_complexity_level"),
        nullable=False,
        comment="복잡도",
    )
    base_stage1_md: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    base_stage2_md: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    base_surveillance_md: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    base_recertification_md: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    base_md_detail_json: Mapped[Optional[Any]] = mapped_column(
        JSON, nullable=True, comment="MD 엔진 상세 로그 (_lastCalcLog 대응)"
    )

    cb_adjustment_ratio: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("0.00"),
        server_default=text("0.00"),
        comment="CB 결정 가감비율 (%)",
    )
    cb_adjustment_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_audit_md: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)

    is_witness_audit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    witness_type: Mapped[str] = mapped_column(
        Enum("NONE", "KAB_WITNESS", "INTERNAL_WITNESS", name="eaa_witness_type"),
        nullable=False,
        default="NONE",
        server_default="NONE",
    )
    witness_auditor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        Enum("SUBMITTED", "REVIEWING", "PROPOSED", "CONTRACTED", name="eaa_status"),
        nullable=False,
        default="SUBMITTED",
        server_default="SUBMITTED",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # --- 초안 Application 스펙 동의어 ---
    @property
    def company_id(self) -> int:
        return self.enterprise_id

    @company_id.setter
    def company_id(self, value: int) -> None:
        self.enterprise_id = value

    @property
    def standards_json(self):
        return self.applied_standards

    @standards_json.setter
    def standards_json(self, value) -> None:
        self.applied_standards = value


# 초안 스펙의 class Application 이름 호환
Application = EnterpriseAuditApplication
