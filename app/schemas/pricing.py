"""심사비 · 출장비 · 할인 정책 마스터 (FE types/pricing.ts)."""
from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class StandardPriceMaster(BaseModel):
    id: str
    standard_code: str = Field(..., alias="standardCode", description="familyCode")
    base_price_per_md: float = Field(
        ..., alias="basePricePerMD", description="M/D당 기본 심사 단가 (원)"
    )
    minimum_md: float = Field(..., alias="minimumMD", description="최소 적용 M/D")
    currency: Literal["KRW"] = "KRW"
    effective_start_date: str = Field(..., alias="effectiveStartDate")
    effective_end_date: str = Field(..., alias="effectiveEndDate")
    is_active: bool = Field(True, alias="isActive")

    class Config:
        populate_by_name = True


class TravelExpensePolicy(BaseModel):
    region_code: str = Field(..., alias="regionCode")
    region_name: str = Field(..., alias="regionName")
    per_diem_per_md: float = Field(..., alias="perDiemPerMD")
    accommodation_per_night: float = Field(..., alias="accommodationPerNight")
    flat_travel_fee: float = Field(..., alias="flatTravelFee")

    class Config:
        populate_by_name = True


class DiscountPolicy(BaseModel):
    discount_code: str = Field(..., alias="discountCode")
    discount_name: str = Field(..., alias="discountName")
    discount_type: Literal["PERCENTAGE", "FIXED_AMOUNT"] = Field(
        ..., alias="discountType"
    )
    value: float = Field(..., description="% 또는 정액 할인금액")
    max_discount_amount: Optional[float] = Field(None, alias="maxDiscountAmount")

    class Config:
        populate_by_name = True


class PricingCatalogBundle(BaseModel):
    standard_prices: List[StandardPriceMaster] = Field(
        default_factory=list, alias="standardPrices"
    )
    travel_policies: List[TravelExpensePolicy] = Field(
        default_factory=list, alias="travelPolicies"
    )
    discount_policies: List[DiscountPolicy] = Field(
        default_factory=list, alias="discountPolicies"
    )

    class Config:
        populate_by_name = True


class CostCalculationInput(BaseModel):
    standard_code: str = Field(..., alias="standardCode")
    final_md: float = Field(..., alias="finalMD")
    region_code: str = Field(..., alias="regionCode")
    requires_accommodation: bool = Field(..., alias="requiresAccommodation")
    accommodation_nights: int = Field(0, alias="accommodationNights")
    discounts: List[DiscountPolicy] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class CostCalculationResult(BaseModel):
    base_audit_fee: float = Field(..., alias="baseAuditFee")
    total_travel_fee: float = Field(..., alias="totalTravelFee")
    subtotal: float
    total_discount_amount: float = Field(..., alias="totalDiscountAmount")
    supply_price: float = Field(..., alias="supplyPrice")
    vat_amount: float = Field(..., alias="vatAmount")
    grand_total: float = Field(..., alias="grandTotal")

    class Config:
        populate_by_name = True
