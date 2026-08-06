"""CB 과금/계약 유틸."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.admin import CBContract, CBTier
from app.models.cb import CertificationBodies


def ensure_default_cb_contract(
    db: Session,
    cb: CertificationBodies,
    *,
    year: Optional[int] = None,
) -> CBContract:
    """CB에 해당 연도 계약이 없으면 기본 과금 계약을 생성한다."""
    contract_year = year or datetime.utcnow().year
    existing = (
        db.query(CBContract)
        .filter(
            CBContract.cb_id == cb.id,
            CBContract.contract_year == contract_year,
        )
        .first()
    )
    if existing:
        return existing

    start = datetime(contract_year, 1, 1)
    end = datetime(contract_year, 12, 31, 23, 59, 59)
    price_md = Decimal(str(int(cb.fee_per_md or 0)))
    contract = CBContract(
        cb_id=cb.id,
        contract_year=contract_year,
        tier=CBTier.MEDIUM.value,
        annual_base_fee=Decimal("0"),
        price_per_md=price_md,
        contract_start_date=start,
        contract_end_date=end,
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db.add(contract)
    db.flush()
    return contract
