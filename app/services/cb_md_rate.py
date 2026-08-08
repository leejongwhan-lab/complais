"""CB 표준(Scope)별 MD 단가 조회.

Fallback order (source of truth first):
  1) cb_standard_accreditations.md_rate  — 표준별 단가 (nullable)
  2) cb_contracts.price_per_md         — CB 계약 레벨 (하위호환)
  3) cb_std_md_rates.md_rate           — CB×표준 단가 테이블
  4) 0
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable, Optional, Sequence

from sqlalchemy.orm import Session

from app.data.standards_catalog import to_family_initial
from app.models.admin import CBContract
from app.models.cb import CbStdMdRates
from app.models.certification_body import CbStandardAccreditation


def resolve_cb_md_rate(
    db: Session,
    cb_id: int,
    standard_code: str,
    *,
    contract_year: Optional[int] = None,
) -> Decimal:
    """Resolve MD unit price (KRW) for a CB × ISO standard.

    Matches accreditation rows by exact standard_code, then by family
    (QMS ↔ ISO 9001:2015 via to_family_initial).
    """
    std = (standard_code or "").strip()
    if not cb_id or not std:
        return Decimal("0")

    rows = (
        db.query(CbStandardAccreditation)
        .filter(CbStandardAccreditation.cb_id == int(cb_id))
        .all()
    )
    exact = next((r for r in rows if (r.standard_code or "") == std), None)
    if exact is not None and exact.md_rate is not None:
        return Decimal(str(exact.md_rate))

    fam = to_family_initial(std)
    if fam:
        for r in rows:
            if to_family_initial(r.standard_code) == fam and r.md_rate is not None:
                return Decimal(str(r.md_rate))

    year = contract_year or datetime.utcnow().year
    contract = (
        db.query(CBContract)
        .filter(
            CBContract.cb_id == int(cb_id),
            CBContract.contract_year == year,
            CBContract.is_active.is_(True),
        )
        .first()
    )
    if contract is None:
        contract = (
            db.query(CBContract)
            .filter(CBContract.cb_id == int(cb_id))
            .order_by(CBContract.contract_year.desc())
            .first()
        )
    if contract is not None and contract.price_per_md is not None:
        rate = Decimal(str(contract.price_per_md or 0))
        if rate > 0:
            return rate

    # 3) cb_std_md_rates — 로컬에 실제 데이터가 있는 소스
    std_rows = (
        db.query(CbStdMdRates)
        .filter(CbStdMdRates.cb_id == int(cb_id))
        .all()
    )
    exact_std = next((r for r in std_rows if (r.standard_code or "") == std), None)
    if exact_std is not None and exact_std.md_rate:
        return Decimal(str(exact_std.md_rate))
    if fam:
        for r in std_rows:
            if to_family_initial(r.standard_code) == fam and r.md_rate:
                return Decimal(str(r.md_rate))

    return Decimal("0")


def resolve_max_cb_md_rate(
    db: Session,
    cb_id: int,
    standard_codes: Sequence[str],
    *,
    contract_year: Optional[int] = None,
) -> Decimal:
    """통합심사: 표준별 단가 중 최댓값 1개 (MD5 B.2 최고값 원칙)."""
    best = Decimal("0")
    for code in standard_codes or []:
        if not code:
            continue
        rate = resolve_cb_md_rate(db, cb_id, str(code), contract_year=contract_year)
        if rate > best:
            best = rate
    return best


def calculate_agreed_amount(
    db: Session,
    *,
    cb_id: int,
    standard_codes: Iterable[str],
    final_md: float,
    contract_year: Optional[int] = None,
) -> Decimal:
    """agreed_amount = final_md × max(표준별 MD단가)."""
    md = Decimal(str(final_md or 0))
    if md <= 0:
        return Decimal("0")
    rate = resolve_max_cb_md_rate(
        db, cb_id, list(standard_codes), contract_year=contract_year
    )
    return (md * rate).quantize(Decimal("1"))
