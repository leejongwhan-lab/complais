"""심사비 · 출장비 · 부가세 통합 연산 (FE calculateAuditPricing 1:1)."""
from __future__ import annotations

from typing import Optional, Sequence

from app.data.pricing_catalog import (
    STANDARD_PRICE_MASTERS,
    TRAVEL_EXPENSE_POLICIES,
)
from app.schemas.pricing import (
    CostCalculationInput,
    CostCalculationResult,
    DiscountPolicy,
    StandardPriceMaster,
    TravelExpensePolicy,
)

VAT_RATE = 0.1


def _single_discount(discount: DiscountPolicy, base_audit_fee: float) -> float:
    if discount.discount_type == "PERCENTAGE":
        amount = round(base_audit_fee * (discount.value / 100.0))
        if (
            discount.max_discount_amount is not None
            and amount > discount.max_discount_amount
        ):
            amount = discount.max_discount_amount
        return float(amount)
    if discount.discount_type == "FIXED_AMOUNT":
        return float(discount.value)
    return 0.0


def calculate_audit_pricing(
    input_data: CostCalculationInput,
    price_master: StandardPriceMaster,
    travel_policy: TravelExpensePolicy,
) -> CostCalculationResult:
    final_md = float(input_data.final_md)
    nights = int(input_data.accommodation_nights or 0)
    discounts = list(input_data.discounts or [])

    base_audit_fee = round(final_md * float(price_master.base_price_per_md))
    per_diem_total = round(final_md * float(travel_policy.per_diem_per_md))
    accommodation_total = (
        nights * float(travel_policy.accommodation_per_night)
        if input_data.requires_accommodation
        else 0.0
    )
    total_travel_fee = (
        float(travel_policy.flat_travel_fee) + per_diem_total + accommodation_total
    )
    subtotal = base_audit_fee + total_travel_fee

    total_discount = 0.0
    for d in discounts:
        total_discount += _single_discount(d, base_audit_fee)

    supply_price = max(0.0, subtotal - total_discount)
    vat_amount = round(supply_price * VAT_RATE)
    grand_total = supply_price + vat_amount

    return CostCalculationResult(
        baseAuditFee=base_audit_fee,
        totalTravelFee=total_travel_fee,
        subtotal=subtotal,
        totalDiscountAmount=total_discount,
        supplyPrice=supply_price,
        vatAmount=vat_amount,
        grandTotal=grand_total,
    )


def resolve_price_master(
    standard_code: str,
    masters: Optional[Sequence[StandardPriceMaster]] = None,
) -> Optional[StandardPriceMaster]:
    rows = list(masters) if masters is not None else [
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
        if p.is_active
    ]
    for m in rows:
        if m.standard_code == standard_code and m.is_active:
            return m
    return None


def resolve_travel_policy(
    region_code: str,
    policies: Optional[Sequence[TravelExpensePolicy]] = None,
) -> Optional[TravelExpensePolicy]:
    rows = list(policies) if policies is not None else [
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
    for t in rows:
        if t.region_code == region_code:
            return t
    return None
