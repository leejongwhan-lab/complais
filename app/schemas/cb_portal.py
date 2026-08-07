"""CB Portal dashboard / deep-link DTOs."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class StandardCount(BaseModel):
    standard_code: str
    count: int = 0


class AuditTypeBreakdown(BaseModel):
    """심사유형별: 최초 / 사후 / 갱신 / 특별."""

    initial: int = 0
    surveillance: int = 0
    renewal: int = 0
    special: int = 0


class CertActivityCard(BaseModel):
    """연간·당월 인증건수 카드."""

    total: int = 0
    by_standard: List[StandardCount] = Field(default_factory=list)
    by_audit_type: AuditTypeBreakdown = Field(default_factory=AuditTypeBreakdown)
    cancelled_count: int = 0


class StandardPerformance(BaseModel):
    """하위 호환 — 표준별 MD 실적."""

    standard_code: str
    count: int = 0
    total_md: Decimal = Decimal("0")


class PeriodPerformance(BaseModel):
    """하위 호환 래퍼."""

    count: int = 0
    total_md: Decimal = Decimal("0")
    by_standard: List[StandardPerformance] = Field(default_factory=list)


class PendingQualificationItem(BaseModel):
    id: int
    auditor_id: int
    auditor_name: Optional[str] = None
    status: str
    apply_grade: Optional[str] = None
    requested_at: Optional[str] = None


class AuditorQueueSummary(BaseModel):
    pending_qualification_count: int = 0
    pending_items: List[PendingQualificationItem] = Field(default_factory=list)
    registered_this_month: int = 0
    renewal_due_count: int = 0


class FinanceSummary(BaseModel):
    revenue_month: Decimal = Decimal("0")
    revenue_year: Decimal = Decimal("0")
    auditor_allowance_total: Decimal = Decimal("0")
    pending_settlement_amount: Decimal = Decimal("0")
    currency: str = "KRW"


class PipelineStage(BaseModel):
    key: str
    count: int = 0
    title: str
    subtitle: str
    href: str


class PipelineSummary(BaseModel):
    """5-stage pipeline counts (deep-link targets)."""

    submitted: int = 0
    reviewing: int = 0
    signed: int = 0
    audit_completed: int = 0
    approved: int = 0
    stages: List[PipelineStage] = Field(default_factory=list)


class CalendarEvent(BaseModel):
    date: str  # YYYY-MM-DD
    company_name: str
    contract_id: Optional[int] = None
    project_id: Optional[int] = None
    standard: Optional[str] = None
    audit_type: Optional[str] = None
    status: Optional[str] = None
    auditors: List[str] = Field(default_factory=list)
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class CalendarMonth(BaseModel):
    year: int
    month: int
    events: List[CalendarEvent] = Field(default_factory=list)


class CbPortalDashboard(BaseModel):
    cb_id: Optional[int] = None
    # Section 1 — 인증원 현황
    cert_year: CertActivityCard = Field(default_factory=CertActivityCard)
    cert_month: CertActivityCard = Field(default_factory=CertActivityCard)
    auditors: AuditorQueueSummary = Field(default_factory=AuditorQueueSummary)
    finance: FinanceSummary = Field(default_factory=FinanceSummary)
    # Section 2
    pipeline: PipelineSummary = Field(default_factory=PipelineSummary)
    calendar: CalendarMonth = Field(default_factory=lambda: CalendarMonth(year=0, month=0))
    # Legacy aliases (older JS)
    performance_year: PeriodPerformance = Field(default_factory=PeriodPerformance)
    performance_month: PeriodPerformance = Field(default_factory=PeriodPerformance)
    warnings: List[str] = Field(
        default_factory=list,
        description="Soft-fail notices (missing tables, etc.)",
    )
