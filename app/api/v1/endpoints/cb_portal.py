"""CB Portal dashboard aggregations + ISO 17021 action stubs."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, inspect, or_, text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.admin_companies import (
    CompanyDetailResponse,
    CompanyListResponse,
    CompanySummaryResponse,
)
from app.core.security import CurrentUser, require_cb_portal_user
from app.db.session import get_db
from app.models.auditor import AuditorSettlements
from app.models.certification import CertificationApplications
from app.models.client import AuditRequest
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.enterprise_audit_application import Application
from app.models.enums import AuditorSettlementsStatus
from app.services.company_held_certs import list_company_held_standards
from app.schemas.cb_portal import (
    AuditTypeBreakdown,
    AuditorQueueSummary,
    CalendarEvent,
    CalendarMonth,
    CbPortalDashboard,
    CertActivityCard,
    FinanceSummary,
    PendingQualificationItem,
    PeriodPerformance,
    PipelineStage,
    PipelineSummary,
    StandardCount,
    StandardPerformance,
)
from app.services import company_org as org

router = APIRouter(prefix="/cb-admin", tags=["CB Portal"])
logger = logging.getLogger(__name__)

_AUDIT_TYPE_BUCKET = {
    "initial": "initial",
    "최초": "initial",
    "stage1": "initial",
    "stage2": "initial",
    "surveillance": "surveillance",
    "surveillance1": "surveillance",
    "surveillance2": "surveillance",
    "사후": "surveillance",
    "recertification": "renewal",
    "renewal": "renewal",
    "갱신": "renewal",
    "special": "special",
    "특별": "special",
    "transfer": "special",
}


def _safe(db: Session, label: str, fn, default, warnings: List[str]):
    try:
        return fn()
    except Exception as exc:
        logger.exception("cb portal dashboard %s failed", label)
        warnings.append(f"{label}: {exc.__class__.__name__}")
        try:
            db.rollback()
        except Exception:
            pass
        return default


def _table_exists(db: Session, name: str) -> bool:
    try:
        return name in inspect(db.bind).get_table_names()
    except Exception:
        return False


def _column_exists(db: Session, table: str, column: str) -> bool:
    try:
        cols = {c["name"] for c in inspect(db.bind).get_columns(table)}
        return column in cols
    except Exception:
        return False


def _resolve_cb_id(user: CurrentUser) -> Optional[int]:
    if user.cb_id is not None:
        return int(user.cb_id)
    return None


def _parse_standards(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    text_v = str(raw).strip()
    if not text_v:
        return []
    if text_v.startswith("["):
        try:
            parsed = json.loads(text_v)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    return [p.strip() for p in text_v.replace(";", ",").split(",") if p.strip()]


def _bucket_audit_type(raw: Optional[str]) -> str:
    key = (raw or "").strip().lower()
    return _AUDIT_TYPE_BUCKET.get(key, "special" if key else "initial")


def _agg_cert_activity(
    db: Session,
    cb_id: int,
    *,
    year: int,
    month: Optional[int] = None,
) -> Tuple[CertActivityCard, PeriodPerformance]:
    q = db.query(Contracts).filter(Contracts.cb_id == cb_id)
    q = q.filter(func.year(Contracts.created_at) == year)
    if month is not None:
        q = q.filter(func.month(Contracts.created_at) == month)
    rows = q.all()

    by_std: DefaultDict[str, int] = defaultdict(int)
    by_type = AuditTypeBreakdown()
    cancelled = 0
    total_md = Decimal("0")
    md_by: DefaultDict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "total_md": Decimal("0")}
    )

    has_cancelled_at = _column_exists(db, "contracts", "cancelled_at")

    for row in rows:
        md = Decimal(str(row.total_md or 0))
        total_md += md
        standards = _parse_standards(row.standards) or _parse_standards(
            getattr(row, "applied_standards", None)
        )
        if not standards:
            standards = ["(미지정)"]
        for std in standards:
            by_std[std] += 1
            md_by[std]["count"] += 1
            md_by[std]["total_md"] += md / Decimal(len(standards))

        bucket = _bucket_audit_type(getattr(row, "audit_type", None))
        setattr(by_type, bucket, getattr(by_type, bucket) + 1)

        status_l = (row.status or "").lower()
        cancelled_at = getattr(row, "cancelled_at", None) if has_cancelled_at else None
        if status_l == "cancelled" or cancelled_at is not None:
            cancelled += 1

    card = CertActivityCard(
        total=len(rows),
        by_standard=[
            StandardCount(standard_code=k, count=v)
            for k, v in sorted(by_std.items(), key=lambda x: (-x[1], x[0]))
        ],
        by_audit_type=by_type,
        cancelled_count=cancelled,
    )
    period = PeriodPerformance(
        count=len(rows),
        total_md=total_md,
        by_standard=[
            StandardPerformance(
                standard_code=k,
                count=int(v["count"]),
                total_md=Decimal(str(v["total_md"])),
            )
            for k, v in sorted(md_by.items(), key=lambda x: (-x[1]["count"], x[0]))
        ],
    )
    return card, period


def _pending_qualifications(
    db: Session, cb_id: int
) -> Tuple[int, List[PendingQualificationItem]]:
    count = db.execute(
        text(
            "SELECT COUNT(*) FROM auditor_cb_memberships "
            "WHERE cb_id = :cb_id AND status IN ('requested','under_review','pending')"
        ),
        {"cb_id": cb_id},
    ).scalar()
    rows = db.execute(
        text(
            """
            SELECT m.id, m.auditor_id, m.status, m.apply_grade, m.requested_at, a.name
            FROM auditor_cb_memberships m
            LEFT JOIN auditors a ON a.id = m.auditor_id
            WHERE m.cb_id = :cb_id
              AND m.status IN ('requested','under_review','pending')
            ORDER BY m.id DESC
            LIMIT 20
            """
        ),
        {"cb_id": cb_id},
    ).fetchall()
    items: List[PendingQualificationItem] = []
    for r in rows:
        requested_at = r[4]
        items.append(
            PendingQualificationItem(
                id=int(r[0]),
                auditor_id=int(r[1]),
                auditor_name=r[5],
                status=str(r[2] or ""),
                apply_grade=r[3],
                requested_at=requested_at.isoformat() if requested_at else None,
            )
        )
    return int(count or 0), items


def _auditor_status_counts(
    db: Session, cb_id: int, *, year: int, month: int
) -> Tuple[int, int]:
    """당월 등록건수, 자격갱신준비건수 (soft columns)."""
    registered = 0
    # Prefer approved_at in month; fallback created_at for approved memberships
    registered = int(
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM auditor_cb_memberships
                WHERE cb_id = :cb_id
                  AND status = 'approved'
                  AND (
                    (approved_at IS NOT NULL
                     AND YEAR(approved_at) = :year AND MONTH(approved_at) = :month)
                    OR (approved_at IS NULL
                        AND YEAR(created_at) = :year AND MONTH(created_at) = :month)
                  )
                """
            ),
            {"cb_id": cb_id, "year": year, "month": month},
        ).scalar()
        or 0
    )

    renewal = 0
    if _column_exists(db, "auditor_cb_memberships", "qualification_expires_at"):
        today = date.today()
        horizon = today + timedelta(days=90)
        renewal = int(
            db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM auditor_cb_memberships
                    WHERE cb_id = :cb_id
                      AND status = 'approved'
                      AND qualification_expires_at IS NOT NULL
                      AND qualification_expires_at >= :today
                      AND qualification_expires_at <= :horizon
                    """
                ),
                {"cb_id": cb_id, "today": today, "horizon": horizon},
            ).scalar()
            or 0
        )
    return registered, renewal


def _sum_revenue(db: Session, cb_id: int, *, year: int, month: Optional[int] = None) -> Decimal:
    amount_col = func.coalesce(Contracts.agreed_amount, Contracts.fee_total, 0)
    q = db.query(func.coalesce(func.sum(amount_col), 0)).filter(Contracts.cb_id == cb_id)
    q = q.filter(func.year(Contracts.created_at) == year)
    if month is not None:
        q = q.filter(func.month(Contracts.created_at) == month)
    return Decimal(str(q.scalar() or 0))


def _sum_settlements(
    db: Session, cb_id: int, *, year: int, pending_only: bool = False
) -> Decimal:
    q = db.query(func.coalesce(func.sum(AuditorSettlements.amount), 0)).filter(
        AuditorSettlements.cb_id == cb_id
    )
    # settlement_month is YYYY-MM; also fall back to created_at year
    q = q.filter(
        or_(
            AuditorSettlements.settlement_month.like(f"{year}-%"),
            and_(
                AuditorSettlements.settlement_month.is_(None),
                func.year(AuditorSettlements.created_at) == year,
            ),
        )
    )
    if pending_only:
        q = q.filter(
            AuditorSettlements.status == AuditorSettlementsStatus.PENDING.value
        )
    return Decimal(str(q.scalar() or 0))


def _pipeline(db: Session, cb_id: int) -> PipelineSummary:
    def _app_count(*status_vals: str) -> int:
        return int(
            db.query(func.count(Application.application_id))
            .filter(
                Application.cb_id == cb_id,
                func.upper(Application.status).in_([s.upper() for s in status_vals]),
            )
            .scalar()
            or 0
        )

    submitted = _app_count("SUBMITTED", "NEED_FIX", "UNDER_REVIEW")
    reviewing = _app_count("REVIEWING", "APPROVED", "PROPOSAL", "PAYMENT_PENDING")

    signed = 0
    audit_completed = 0
    approved = 0
    if _table_exists(db, "contracts"):
        signed = int(
            db.query(func.count(Contracts.id))
            .filter(
                Contracts.cb_id == cb_id,
                func.lower(Contracts.status).in_(
                    ["signed", "client_signed", "scheduled", "in_progress"]
                ),
            )
            .scalar()
            or 0
        )
        audit_completed = int(
            db.query(func.count(Contracts.id))
            .filter(
                Contracts.cb_id == cb_id,
                or_(
                    func.lower(Contracts.status).in_(
                        ["note_submitted", "report_ready", "audit_completed"]
                    ),
                    func.lower(func.coalesce(Contracts.verification_status, "")).in_(
                        ["in_review", "pending"]
                    ),
                ),
            )
            .scalar()
            or 0
        )
        approved = int(
            db.query(func.count(Contracts.id))
            .filter(
                Contracts.cb_id == cb_id,
                or_(
                    func.lower(Contracts.status).in_(["certified", "closed"]),
                    func.lower(func.coalesce(Contracts.verification_status, ""))
                    == "approved",
                ),
            )
            .scalar()
            or 0
        )
    if signed == 0:
        signed = _app_count("CONTRACTED")

    stages = [
        PipelineStage(
            key="submitted",
            count=submitted,
            title="신청검토",
            subtitle="신청서 확인/보완",
            href="/cb-portal?tab=applications&status=submitted",
        ),
        PipelineStage(
            key="reviewing",
            count=reviewing,
            title="제안 및 결제",
            subtitle="결제대기와 제안서",
            href="/cb-portal?tab=proposals&status=reviewing",
        ),
        PipelineStage(
            key="signed",
            count=signed,
            title="계약",
            subtitle="계약/심사준비/수검",
            href="/cb-portal?tab=contracts_pre&status=signed",
        ),
        PipelineStage(
            key="audit_completed",
            count=audit_completed,
            title="보고서검토/인증심의",
            subtitle="행정검토/검증/최종결정",
            href="/cb-portal?tab=verification&status=audit_completed",
        ),
        PipelineStage(
            key="approved",
            count=approved,
            title="인증서 발행",
            subtitle="발행/완료 확인",
            href="/cb-portal?tab=verification&status=approved",
        ),
    ]
    return PipelineSummary(
        submitted=submitted,
        reviewing=reviewing,
        signed=signed,
        audit_completed=audit_completed,
        approved=approved,
        stages=stages,
    )


def _calendar_events(
    db: Session, cb_id: int, *, year: int, month: int
) -> List[CalendarEvent]:
    if not _table_exists(db, "contracts"):
        return []
    # Overlap: period intersects this calendar month
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    q = (
        db.query(Contracts, Companies.name)
        .outerjoin(Companies, Companies.id == Contracts.company_id)
        .filter(Contracts.cb_id == cb_id)
        .filter(Contracts.audit_period_start.isnot(None))
        .filter(
            Contracts.audit_period_start <= month_end,
            or_(
                Contracts.audit_period_end.is_(None),
                Contracts.audit_period_end >= month_start,
            ),
        )
    )
    events: List[CalendarEvent] = []
    for row, company_name in q.all():
        start = row.audit_period_start
        end = row.audit_period_end or start
        if not start:
            continue
        # Place company name on each day in range ∩ month
        cur = max(start, month_start)
        last = min(end, month_end)
        standards = _parse_standards(row.standards)
        std_label = ", ".join(standards[:3]) if standards else None
        auditors: List[str] = []
        # lead auditor name soft lookup
        try:
            if row.lead_auditor_id:
                name = db.execute(
                    text("SELECT name FROM auditors WHERE id = :id LIMIT 1"),
                    {"id": row.lead_auditor_id},
                ).scalar()
                if name:
                    auditors.append(str(name))
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

        while cur <= last:
            events.append(
                CalendarEvent(
                    date=cur.isoformat(),
                    company_name=company_name or f"기업 #{row.company_id}",
                    contract_id=row.id,
                    project_id=row.id,
                    standard=std_label,
                    audit_type=row.audit_type,
                    status=row.status,
                    auditors=auditors,
                    period_start=start.isoformat() if start else None,
                    period_end=end.isoformat() if end else None,
                )
            )
            cur += timedelta(days=1)
    return events


@router.get("/dashboard", response_model=CbPortalDashboard)
def get_cb_portal_dashboard(
    year: Optional[int] = Query(None, description="캘린더 연도 (기본: 당해)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="캘린더 월"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> CbPortalDashboard:
    """CB 포털 대시보드 실집계 (세션 cb_id 스코프). platform_admin 403."""
    warnings: List[str] = []
    cb_id = _resolve_cb_id(current_user)
    if cb_id is None:
        return CbPortalDashboard(
            cb_id=None,
            warnings=["cb_id가 없어 집계를 건너뜁니다. CB 계정으로 로그인하세요."],
        )

    now = datetime.utcnow()
    y, m = now.year, now.month
    cal_year = year or y
    cal_month = month or m

    empty_card = CertActivityCard()
    empty_period = PeriodPerformance()
    cert_year, perf_year = empty_card, empty_period
    cert_month, perf_month = empty_card, empty_period

    if _table_exists(db, "contracts"):
        cy = _safe(
            db,
            "cert_year",
            lambda: _agg_cert_activity(db, cb_id, year=y),
            (empty_card, empty_period),
            warnings,
        )
        cert_year, perf_year = cy
        cm = _safe(
            db,
            "cert_month",
            lambda: _agg_cert_activity(db, cb_id, year=y, month=m),
            (empty_card, empty_period),
            warnings,
        )
        cert_month, perf_month = cm
    else:
        warnings.append("contracts 테이블 없음")

    auditors = AuditorQueueSummary()
    if _table_exists(db, "auditor_cb_memberships"):
        cnt, items = _safe(
            db,
            "pending_qualifications",
            lambda: _pending_qualifications(db, cb_id),
            (0, []),
            warnings,
        )
        reg, renew = _safe(
            db,
            "auditor_status",
            lambda: _auditor_status_counts(db, cb_id, year=y, month=m),
            (0, 0),
            warnings,
        )
        auditors = AuditorQueueSummary(
            pending_qualification_count=cnt,
            pending_items=items,
            registered_this_month=reg,
            renewal_due_count=renew,
        )
    else:
        warnings.append("auditor_cb_memberships 없음")

    finance = FinanceSummary()
    if _table_exists(db, "contracts"):
        finance.revenue_year = _safe(
            db,
            "revenue_year",
            lambda: _sum_revenue(db, cb_id, year=y),
            Decimal("0"),
            warnings,
        )
        finance.revenue_month = _safe(
            db,
            "revenue_month",
            lambda: _sum_revenue(db, cb_id, year=y, month=m),
            Decimal("0"),
            warnings,
        )
    if _table_exists(db, "auditor_settlements"):
        finance.auditor_allowance_total = _safe(
            db,
            "auditor_allowance",
            lambda: _sum_settlements(db, cb_id, year=y, pending_only=False),
            Decimal("0"),
            warnings,
        )
        finance.pending_settlement_amount = _safe(
            db,
            "pending_settlements",
            lambda: _sum_settlements(db, cb_id, year=y, pending_only=True),
            Decimal("0"),
            warnings,
        )
    else:
        warnings.append("auditor_settlements 없음")

    pipeline = _safe(
        db, "pipeline", lambda: _pipeline(db, cb_id), PipelineSummary(), warnings
    )

    events = _safe(
        db,
        "calendar",
        lambda: _calendar_events(db, cb_id, year=cal_year, month=cal_month),
        [],
        warnings,
    )
    calendar = CalendarMonth(year=cal_year, month=cal_month, events=events)

    return CbPortalDashboard(
        cb_id=cb_id,
        cert_year=cert_year,
        cert_month=cert_month,
        auditors=auditors,
        finance=finance,
        pipeline=pipeline,
        calendar=calendar,
        performance_year=perf_year,
        performance_month=perf_month,
        warnings=warnings,
    )


# ── 고객사현황 (CB-scoped companies, admin-style list/detail, read-only) ──


def _cb_related_company_ids(db: Session, cb_id: int) -> List[int]:
    """Companies linked to this CB via contracts / applications / audit_requests.

    Soft-fail each source; optional legacy ``companies.cb_id`` if the column exists.
    Also includes ``certification_applications`` and ``company_certificates``.
    """
    ids: set[int] = set()

    def _add_rows(rows) -> None:
        for row in rows:
            cid = row[0] if not isinstance(row, int) else row
            if cid is not None:
                ids.add(int(cid))

    try:
        _add_rows(
            db.query(Contracts.company_id)
            .filter(Contracts.cb_id == cb_id)
            .distinct()
            .all()
        )
    except Exception:
        logger.exception("cb companies: contracts id query failed")
        try:
            db.rollback()
        except Exception:
            pass

    try:
        _add_rows(
            db.query(Application.enterprise_id)
            .filter(Application.cb_id == cb_id)
            .distinct()
            .all()
        )
    except Exception:
        logger.exception("cb companies: applications id query failed")
        try:
            db.rollback()
        except Exception:
            pass

    try:
        _add_rows(
            db.query(CertificationApplications.company_id)
            .filter(CertificationApplications.cb_id == cb_id)
            .distinct()
            .all()
        )
    except Exception:
        logger.exception("cb companies: certification_applications id query failed")
        try:
            db.rollback()
        except Exception:
            pass

    try:
        _add_rows(
            db.query(AuditRequest.company_id)
            .filter(AuditRequest.cb_id == cb_id)
            .distinct()
            .all()
        )
    except Exception:
        logger.exception("cb companies: audit_requests id query failed")
        try:
            db.rollback()
        except Exception:
            pass

    if _table_exists(db, "company_certificates"):
        try:
            _add_rows(
                db.execute(
                    text(
                        "SELECT DISTINCT company_id FROM company_certificates "
                        "WHERE cb_id = :cb_id"
                    ),
                    {"cb_id": cb_id},
                ).fetchall()
            )
        except Exception:
            logger.exception("cb companies: company_certificates id query failed")
            try:
                db.rollback()
            except Exception:
                pass

    if _column_exists(db, "companies", "cb_id"):
        try:
            _add_rows(
                db.execute(
                    text("SELECT id FROM companies WHERE cb_id = :cb_id"),
                    {"cb_id": cb_id},
                ).fetchall()
            )
        except Exception:
            logger.exception("cb companies: legacy companies.cb_id query failed")
            try:
                db.rollback()
            except Exception:
                pass

    return sorted(ids)


def _assert_cb_company_access(db: Session, cb_id: int, company_id: int) -> None:
    related = set(_cb_related_company_ids(db, cb_id))
    if company_id not in related:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="고객사 정보를 찾을 수 없습니다.",
        )


@router.get("/companies", response_model=CompanyListResponse)
def list_cb_companies(
    keyword: Optional[str] = Query(None, description="기업명 또는 사업자번호 검색"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> CompanyListResponse:
    """CB 스코프 고객사 목록 — 계약/신청 연동 기업 (조회 전용)."""
    cb_id = int(current_user.cb_id)
    try:
        company_ids = _cb_related_company_ids(db, cb_id)
        if not company_ids:
            return CompanyListResponse(total=0, page=page, limit=limit, data=[])

        query = db.query(Companies).filter(Companies.id.in_(company_ids))
        if keyword and keyword.strip():
            like = f"%{keyword.strip()}%"
            query = query.filter(
                (Companies.name.ilike(like))
                | (Companies.biz_no.ilike(like))
                | (Companies.name_en.ilike(like))
            )

        total_count = query.count()
        companies = (
            query.order_by(Companies.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        data = []
        for c in companies:
            item = CompanySummaryResponse.model_validate(c)
            try:
                # CB portal: only standards this CB audits/certifies for the company
                item.held_standards = list_company_held_standards(
                    db, int(c.id), cb_id=cb_id, display_mode="cb"
                )
            except Exception:
                logger.exception("held_standards list soft-fail company_id=%s", c.id)
                item.held_standards = []
            data.append(item)
        return CompanyListResponse(
            total=total_count,
            page=page,
            limit=limit,
            data=data,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("cb companies list failed cb_id=%s", cb_id)
        try:
            db.rollback()
        except Exception:
            pass
        return CompanyListResponse(total=0, page=page, limit=limit, data=[])


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
def get_cb_company_detail(
    company_id: int,
    headcount_year: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> CompanyDetailResponse:
    """CB 스코프 고객사 상세 — 어드민과 동일 필드 그룹, 전체 읽기 전용."""
    cb_id = int(current_user.cb_id)
    _assert_cb_company_access(db, cb_id, company_id)
    try:
        detail = org.build_company_org_detail(db, company_id, headcount_year)
        try:
            detail["held_standards"] = list_company_held_standards(
                db, company_id, cb_id=cb_id, display_mode="cb"
            )
        except Exception:
            logger.exception("held_standards detail soft-fail company_id=%s", company_id)
            detail["held_standards"] = []
        return CompanyDetailResponse.model_validate(detail)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("cb company detail failed company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"고객사 상세 조회에 실패했습니다: {exc.__class__.__name__}",
        ) from exc


# ── company_aspects (EMS / OHS / EnMS) ─────────────────────────────────────


@router.get("/companies/{company_id}/aspects")
def get_cb_company_aspects(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> Dict[str, Any]:
    """CB 기업 상세 — 경영시스템 특성 정보(Aspects)."""
    cb_id = int(current_user.cb_id)
    _assert_cb_company_access(db, cb_id, company_id)
    from app.data.company_aspects_catalog import aspects_catalog_payload
    from app.services.company_aspects import aspects_to_dict, get_company_aspects

    row = get_company_aspects(db, company_id)
    return {
        "company_id": company_id,
        "aspects": aspects_to_dict(row),
        "catalog": aspects_catalog_payload(),
    }


@router.put("/companies/{company_id}/aspects")
def put_cb_company_aspects(
    company_id: int,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> Dict[str, Any]:
    """UPSERT company_aspects for CB-managed company."""
    cb_id = int(current_user.cb_id)
    _assert_cb_company_access(db, cb_id, company_id)
    from app.services.company_aspects import aspects_to_dict, upsert_company_aspects

    ems = payload.get("ems")
    ohs = payload.get("ohs")
    enms = payload.get("enms")
    if isinstance(payload.get("aspects"), dict):
        asp = payload["aspects"]
        ems = asp.get("ems", ems)
        ohs = asp.get("ohs", ohs)
        enms = asp.get("enms", enms)
    row, created = upsert_company_aspects(
        db, company_id, ems=ems, ohs=ohs, enms=enms, merge=True
    )
    db.commit()
    return {
        "ok": True,
        "created": created,
        "company_id": company_id,
        "aspects": aspects_to_dict(row),
    }


# ── ISO/IEC 17021 CB-only actions (stub until PDF/issue APIs land) ─────────


@router.post(
    "/verification/{contract_id}/request-supplement",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def request_supplement(
    contract_id: int,
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    """보완 요청 — UI ready, backend stub."""
    raise HTTPException(
        status_code=501,
        detail=f"보완 요청 API 준비 중 (contract_id={contract_id})",
    )


@router.post(
    "/verification/{contract_id}/approve",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def approve_verification(
    contract_id: int,
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    """검증 심의서 승인 — UI ready, backend stub."""
    raise HTTPException(
        status_code=501,
        detail=f"검증 심의 승인 API 준비 중 (contract_id={contract_id})",
    )


@router.post(
    "/verification/{contract_id}/issue-certificate",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
def issue_certificate_pdf(
    contract_id: int,
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    """인증서 PDF 발급 — UI ready, backend stub."""
    raise HTTPException(
        status_code=501,
        detail=f"인증서 PDF 발급 API 준비 중 (contract_id={contract_id})",
    )
