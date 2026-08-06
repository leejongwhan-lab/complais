"""가격·출장·할인 정책 조회 API."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.data.pricing_catalog import (
    DISCOUNT_POLICIES,
    STANDARD_PRICE_MASTERS,
    TRAVEL_EXPENSE_POLICIES,
)
from app.models.pricing import (
    DiscountPolicyRow,
    StandardPriceMasterRow,
    TravelExpensePolicyRow,
)
from app.schemas.pricing import (
    CostCalculationInput,
    CostCalculationResult,
    DiscountPolicy,
    PricingCatalogBundle,
    StandardPriceMaster,
    TravelExpensePolicy,
)
from app.services.audit_pricing import calculate_audit_pricing


router = APIRouter(prefix="/pricing", tags=["Pricing"])

DDL_PRICE = """
CREATE TABLE IF NOT EXISTS standard_price_masters (
  id VARCHAR(40) NOT NULL,
  standard_code VARCHAR(20) NOT NULL,
  base_price_per_md DECIMAL(15,2) NOT NULL,
  minimum_md DECIMAL(8,2) NOT NULL DEFAULT 1,
  currency VARCHAR(10) NOT NULL DEFAULT 'KRW',
  effective_start_date DATE NOT NULL,
  effective_end_date DATE NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_spm_std (standard_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

DDL_TRAVEL = """
CREATE TABLE IF NOT EXISTS travel_expense_policies (
  region_code VARCHAR(40) NOT NULL,
  region_name VARCHAR(80) NOT NULL,
  per_diem_per_md DECIMAL(15,2) NOT NULL DEFAULT 0,
  accommodation_per_night DECIMAL(15,2) NOT NULL DEFAULT 0,
  flat_travel_fee DECIMAL(15,2) NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

DDL_DISCOUNT = """
CREATE TABLE IF NOT EXISTS discount_policies (
  discount_code VARCHAR(40) NOT NULL,
  discount_name VARCHAR(120) NOT NULL,
  discount_type VARCHAR(20) NOT NULL,
  value DECIMAL(15,2) NOT NULL,
  max_discount_amount DECIMAL(15,2) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (discount_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def ensure_pricing_schema(db: Session) -> None:
    db.execute(text(DDL_PRICE))
    db.execute(text(DDL_TRAVEL))
    db.execute(text(DDL_DISCOUNT))
    db.commit()


def seed_from_catalog(db: Session) -> None:
    ensure_pricing_schema(db)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active_regions = {t.region_code for t in TRAVEL_EXPENSE_POLICIES}
    for t in TRAVEL_EXPENSE_POLICIES:
        row = db.get(TravelExpensePolicyRow, t.region_code)
        if row is None:
            row = TravelExpensePolicyRow(region_code=t.region_code)
            db.add(row)
        row.region_name = t.region_name
        row.per_diem_per_md = t.per_diem_per_md
        row.accommodation_per_night = t.accommodation_per_night
        row.flat_travel_fee = t.flat_travel_fee
        row.is_active = True
        row.updated_at = now
    # 구 권역 비활성
    for old in db.query(TravelExpensePolicyRow).all():
        if old.region_code not in active_regions:
            old.is_active = False
            old.updated_at = now

    for d in DISCOUNT_POLICIES:
        row = db.get(DiscountPolicyRow, d.discount_code)
        if row is None:
            row = DiscountPolicyRow(discount_code=d.discount_code)
            db.add(row)
        row.discount_name = d.discount_name
        row.discount_type = d.discount_type
        row.value = d.value
        row.max_discount_amount = d.max_discount_amount
        row.is_active = True
        row.updated_at = now

    active_price_ids = {p.id for p in STANDARD_PRICE_MASTERS}
    for p in STANDARD_PRICE_MASTERS:
        row = db.get(StandardPriceMasterRow, p.id)
        if row is None:
            row = StandardPriceMasterRow(id=p.id)
            db.add(row)
        row.standard_code = p.standard_code
        row.base_price_per_md = p.base_price_per_md
        row.minimum_md = p.minimum_md
        row.currency = p.currency
        row.effective_start_date = date.fromisoformat(p.effective_start_date)
        row.effective_end_date = date.fromisoformat(p.effective_end_date)
        row.is_active = p.is_active
        row.updated_at = now
    for old in db.query(StandardPriceMasterRow).all():
        if old.id not in active_price_ids:
            old.is_active = False
            old.updated_at = now
    db.commit()


@router.get("/catalog", response_model=PricingCatalogBundle)
def get_pricing_catalog(
    standard_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    ensure_pricing_schema(db)
    if db.query(TravelExpensePolicyRow.region_code).first() is None:
        seed_from_catalog(db)

    prices_q = db.query(StandardPriceMasterRow).filter(
        StandardPriceMasterRow.is_active.is_(True)
    )
    if standard_code:
        prices_q = prices_q.filter(StandardPriceMasterRow.standard_code == standard_code)
    price_rows = prices_q.all()
    travel_rows = (
        db.query(TravelExpensePolicyRow)
        .filter(TravelExpensePolicyRow.is_active.is_(True))
        .all()
    )
    discount_rows = (
        db.query(DiscountPolicyRow).filter(DiscountPolicyRow.is_active.is_(True)).all()
    )

    standard_prices: List[StandardPriceMaster] = (
        [
            StandardPriceMaster.model_validate(
                {
                    "id": r.id,
                    "standardCode": r.standard_code,
                    "basePricePerMD": float(r.base_price_per_md),
                    "minimumMD": float(r.minimum_md),
                    "currency": r.currency,
                    "effectiveStartDate": r.effective_start_date.isoformat(),
                    "effectiveEndDate": r.effective_end_date.isoformat(),
                    "isActive": bool(r.is_active),
                }
            )
            for r in price_rows
        ]
        if price_rows
        else [
            StandardPriceMaster.model_validate(
                {
                    "id": p.id,
                    "standardCode": p.standard_code,
                    "basePricePerMD": p.base_price_per_md,
                    "minimumMD": p.minimum_md,
                    "currency": p.currency,
                    "effectiveStartDate": p.effective_start_date,
                    "effectiveEndDate": p.effective_end_date,
                    "isActive": p.is_active,
                }
            )
            for p in STANDARD_PRICE_MASTERS
            if not standard_code or p.standard_code == standard_code
        ]
    )

    travel = (
        [
            TravelExpensePolicy.model_validate(
                {
                    "regionCode": r.region_code,
                    "regionName": r.region_name,
                    "perDiemPerMD": float(r.per_diem_per_md),
                    "accommodationPerNight": float(r.accommodation_per_night),
                    "flatTravelFee": float(r.flat_travel_fee),
                }
            )
            for r in travel_rows
        ]
        if travel_rows
        else [
            TravelExpensePolicy.model_validate(
                {
                    "regionCode": t.region_code,
                    "regionName": t.region_name,
                    "perDiemPerMD": t.per_diem_per_md,
                    "accommodationPerNight": t.accommodation_per_night,
                    "flatTravelFee": t.flat_travel_fee,
                }
            )
            for t in TRAVEL_EXPENSE_POLICIES
        ]
    )

    discounts = (
        [
            DiscountPolicy.model_validate(
                {
                    "discountCode": r.discount_code,
                    "discountName": r.discount_name,
                    "discountType": r.discount_type,
                    "value": float(r.value),
                    "maxDiscountAmount": (
                        float(r.max_discount_amount)
                        if r.max_discount_amount is not None
                        else None
                    ),
                }
            )
            for r in discount_rows
        ]
        if discount_rows
        else [
            DiscountPolicy.model_validate(
                {
                    "discountCode": d.discount_code,
                    "discountName": d.discount_name,
                    "discountType": d.discount_type,
                    "value": d.value,
                    "maxDiscountAmount": d.max_discount_amount,
                }
            )
            for d in DISCOUNT_POLICIES
        ]
    )

    return PricingCatalogBundle(
        standardPrices=standard_prices,
        travelPolicies=travel,
        discountPolicies=discounts,
    )


@router.post("/seed")
def seed_pricing(db: Session = Depends(get_db)):
    seed_from_catalog(db)
    return {"ok": True}


@router.post("/calculate", response_model=CostCalculationResult)
def post_calculate_audit_pricing(
    payload: CostCalculationInput,
    db: Session = Depends(get_db),
):
    """심사비·출장비·부가세 통합 산출."""
    ensure_pricing_schema(db)
    if db.query(TravelExpensePolicyRow.region_code).first() is None:
        seed_from_catalog(db)

    price_row = (
        db.query(StandardPriceMasterRow)
        .filter(
            StandardPriceMasterRow.standard_code == payload.standard_code,
            StandardPriceMasterRow.is_active.is_(True),
        )
        .order_by(StandardPriceMasterRow.effective_start_date.desc())
        .first()
    )
    if price_row:
        price_master = StandardPriceMaster.model_validate(
            {
                "id": price_row.id,
                "standardCode": price_row.standard_code,
                "basePricePerMD": float(price_row.base_price_per_md),
                "minimumMD": float(price_row.minimum_md),
                "currency": price_row.currency,
                "effectiveStartDate": price_row.effective_start_date.isoformat(),
                "effectiveEndDate": price_row.effective_end_date.isoformat(),
                "isActive": bool(price_row.is_active),
            }
        )
    else:
        cat = next(
            (p for p in STANDARD_PRICE_MASTERS if p.standard_code == payload.standard_code),
            None,
        )
        if not cat:
            raise HTTPException(
                status_code=404,
                detail=f"단가 마스터 없음: {payload.standard_code}",
            )
        price_master = StandardPriceMaster.model_validate(
            {
                "id": cat.id,
                "standardCode": cat.standard_code,
                "basePricePerMD": cat.base_price_per_md,
                "minimumMD": cat.minimum_md,
                "currency": cat.currency,
                "effectiveStartDate": cat.effective_start_date,
                "effectiveEndDate": cat.effective_end_date,
                "isActive": cat.is_active,
            }
        )

    travel_row = db.get(TravelExpensePolicyRow, payload.region_code)
    if travel_row and travel_row.is_active:
        travel = TravelExpensePolicy.model_validate(
            {
                "regionCode": travel_row.region_code,
                "regionName": travel_row.region_name,
                "perDiemPerMD": float(travel_row.per_diem_per_md),
                "accommodationPerNight": float(travel_row.accommodation_per_night),
                "flatTravelFee": float(travel_row.flat_travel_fee),
            }
        )
    else:
        cat_t = next(
            (t for t in TRAVEL_EXPENSE_POLICIES if t.region_code == payload.region_code),
            None,
        )
        if not cat_t:
            raise HTTPException(
                status_code=404,
                detail=f"출장 정책 없음: {payload.region_code}",
            )
        travel = TravelExpensePolicy.model_validate(
            {
                "regionCode": cat_t.region_code,
                "regionName": cat_t.region_name,
                "perDiemPerMD": cat_t.per_diem_per_md,
                "accommodationPerNight": cat_t.accommodation_per_night,
                "flatTravelFee": cat_t.flat_travel_fee,
            }
        )

    return calculate_audit_pricing(payload, price_master, travel)
