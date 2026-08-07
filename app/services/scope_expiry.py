"""CB 표준(Scope) 인정만료일 검증.

`cb_standard_accreditations.expiry_date` 기준:
  - ok     : 만료일 없음 또는 D-30 초과 잔여
  - warn   : 잔여 0~30일 (D-30 경고)
  - locked : 만료일 경과 → 해당 표준 Proposal 생성/송부 차단

Examples
--------
>>> from datetime import date, timedelta
>>> r = evaluate_expiry(date.today() - timedelta(days=1))
>>> r.status
'locked'
>>> r = evaluate_expiry(date.today() + timedelta(days=10))
>>> r.status
'warn'
>>> r.days_remaining
10
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, List, Literal, Optional, Sequence, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.data.standards_catalog import to_family_initial
from app.models.certification_body import CbStandardAccreditation

ScopeExpiryStatus = Literal["ok", "warn", "locked"]
WARN_DAYS = 30

LOCKED_DETAIL_KO = (
    "해당 ISO 표준의 인정 유효기간이 만료되어 제안서를 작성·송부할 수 없습니다. "
    "인정 갱신 후 다시 시도해 주세요."
)


@dataclass(frozen=True)
class ScopeExpiryResult:
    status: ScopeExpiryStatus
    days_remaining: Optional[int] = None
    expiry_date: Optional[date] = None
    expiry_warning: Optional[str] = None
    matched_standard_code: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def is_locked(self) -> bool:
        return self.status == "locked"


def _as_date(value: Union[date, datetime, None]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def evaluate_expiry(
    expiry_date: Union[date, datetime, None],
    *,
    today: Optional[date] = None,
) -> ScopeExpiryResult:
    """순수 날짜 판정 (DB 불필요)."""
    exp = _as_date(expiry_date)
    if exp is None:
        return ScopeExpiryResult(status="ok")

    day = today or date.today()
    remaining = (exp - day).days
    if remaining < 0:
        return ScopeExpiryResult(
            status="locked",
            days_remaining=remaining,
            expiry_date=exp,
            expiry_warning=f"인정만료일 경과({exp.isoformat()}, {abs(remaining)}일 초과)",
        )
    if remaining <= WARN_DAYS:
        return ScopeExpiryResult(
            status="warn",
            days_remaining=remaining,
            expiry_date=exp,
            expiry_warning=f"인정만료 D-{remaining} ({exp.isoformat()})",
        )
    return ScopeExpiryResult(
        status="ok",
        days_remaining=remaining,
        expiry_date=exp,
    )


def _pick_accreditation_row(
    rows: Sequence[CbStandardAccreditation],
    standard: str,
) -> Optional[CbStandardAccreditation]:
    std = (standard or "").strip()
    if not std or not rows:
        return None
    exact = next((r for r in rows if (r.standard_code or "") == std), None)
    if exact is not None:
        return exact
    fam = to_family_initial(std)
    if not fam:
        return None
    # Prefer active row with expiry among family matches
    fam_rows = [r for r in rows if to_family_initial(r.standard_code) == fam]
    if not fam_rows:
        return None
    with_exp = [r for r in fam_rows if getattr(r, "expiry_date", None)]
    pool = with_exp or fam_rows
    active = [r for r in pool if getattr(r, "is_active", True)]
    return (active or pool)[0]


def check_scope_expiry(
    db: Session,
    cb_id: int,
    standard: str,
    *,
    today: Optional[date] = None,
) -> ScopeExpiryResult:
    """CB × ISO 표준/패밀리 인정만료 상태.

    Returns ok | warn | locked. 만료일 미등록은 ok (차단하지 않음).
    """
    try:
        cid = int(cb_id)
    except (TypeError, ValueError):
        return ScopeExpiryResult(status="ok")
    if not cid or not (standard or "").strip():
        return ScopeExpiryResult(status="ok")

    try:
        rows = (
            db.query(CbStandardAccreditation)
            .filter(CbStandardAccreditation.cb_id == cid)
            .all()
        )
    except Exception:
        # soft-fail: schema/DB drift 시 제안 경로를 깨지 않음
        try:
            db.rollback()
        except Exception:
            pass
        return ScopeExpiryResult(status="ok")

    row = _pick_accreditation_row(rows, standard)
    if row is None:
        return ScopeExpiryResult(status="ok")

    result = evaluate_expiry(getattr(row, "expiry_date", None), today=today)
    return ScopeExpiryResult(
        status=result.status,
        days_remaining=result.days_remaining,
        expiry_date=result.expiry_date,
        expiry_warning=result.expiry_warning,
        matched_standard_code=getattr(row, "standard_code", None),
    )


def check_standards_expiry(
    db: Session,
    cb_id: int,
    standards: Iterable[str],
    *,
    today: Optional[date] = None,
) -> List[ScopeExpiryResult]:
    """여러 표준 검사. locked가 있으면 앞에 오도록 정렬하지는 않음 — 호출측에서 any()."""
    out: List[ScopeExpiryResult] = []
    seen: set[str] = set()
    for raw in standards or []:
        std = str(raw or "").strip()
        if not std or std in seen:
            continue
        seen.add(std)
        out.append(check_scope_expiry(db, cb_id, std, today=today))
    return out


def enforce_scope_not_expired(
    db: Session,
    cb_id: int,
    standards: Iterable[str],
    *,
    today: Optional[date] = None,
) -> None:
    """만료된 표준이 있으면 403 Forbidden (한국어 detail)."""
    for result in check_standards_expiry(db, cb_id, standards, today=today):
        if result.is_locked:
            std = result.matched_standard_code or ""
            detail = LOCKED_DETAIL_KO
            if std:
                detail = f"[{std}] {LOCKED_DETAIL_KO}"
            if result.expiry_date:
                detail = f"{detail} (만료일: {result.expiry_date.isoformat()})"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            )


def expiry_api_fields(
    expiry_date: Union[date, datetime, None],
    *,
    today: Optional[date] = None,
) -> dict:
    """목록/모달 응답용 필드 dict."""
    r = evaluate_expiry(expiry_date, today=today)
    return {
        "days_remaining": r.days_remaining,
        "expiry_warning": r.expiry_warning,
        "expiry_status": r.status,
    }
