"""CB 표준(Scope)별 MD 단가 조회.

Fallback order (source of truth first):
  1) cb_standard_accreditations.md_rate  — 표준별 단가 (nullable)
  2) cb_contracts.price_per_md         — CB 계약 레벨 (하위호환)
  3) 0
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.data.standards_catalog import to_family_initial
from app.models.admin import CBContract
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
        return Decimal(str(contract.price_per_md or 0))

    return Decimal("0")
