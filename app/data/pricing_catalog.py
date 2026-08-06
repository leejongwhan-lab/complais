"""심사비 · 출장비 · 할인 정책 카탈로그 (FE constants/pricingMasterData 동기)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal, Optional


@dataclass(frozen=True)
class StandardPriceDef:
    id: str
    standard_code: str
    base_price_per_md: float
    minimum_md: float
    currency: Literal["KRW"]
    effective_start_date: str
    effective_end_date: str
    is_active: bool = True


@dataclass(frozen=True)
class TravelExpenseDef:
    region_code: str
    region_name: str
    per_diem_per_md: float
    accommodation_per_night: float
    flat_travel_fee: float


@dataclass(frozen=True)
class DiscountPolicyDef:
    discount_code: str
    discount_name: str
    discount_type: Literal["PERCENTAGE", "FIXED_AMOUNT"]
    value: float
    max_discount_amount: Optional[float] = None


# 규격별 M/D 표준 단가 (원)
DEFAULT_PRICE_MASTERS: Dict[str, int] = {
    "QMS": 900_000,
    "EMS": 900_000,
    "OHSMS": 950_000,
    "ISMS": 1_100_000,
    "ABMS": 1_000_000,
    "CMS": 1_000_000,
    "EnMS": 1_000_000,
    "FSMS": 950_000,
    "MDQMS": 1_100_000,
    "NSMS": 1_200_000,
    "PIMS": 1_100_000,
    "AIMS": 1_200_000,
    "COMMON": 900_000,
    "IMS": 850_000,
}

_PRICE_START = "2026-01-01"
_PRICE_END = "2099-12-31"
_MIN_MD = 1.0

STANDARD_PRICE_MASTERS: List[StandardPriceDef] = [
    StandardPriceDef(
        id=f"PRICE_{code}_2026",
        standard_code=code,
        base_price_per_md=float(price),
        minimum_md=_MIN_MD,
        currency="KRW",
        effective_start_date=_PRICE_START,
        effective_end_date=_PRICE_END,
        is_active=True,
    )
    for code, price in DEFAULT_PRICE_MASTERS.items()
]

# 권역별 출장비 정책
DEFAULT_TRAVEL_POLICIES: Dict[str, TravelExpenseDef] = {
    "SEOUL_METRO": TravelExpenseDef(
        "SEOUL_METRO", "수도권(서울/경기/인천)", 30_000, 80_000, 20_000
    ),
    "DAEGU_GB": TravelExpenseDef(
        "DAEGU_GB", "대경권(대구/경북)", 40_000, 90_000, 60_000
    ),
    "SEJONG_CB": TravelExpenseDef(
        "SEJONG_CB", "충청권(대전/세종/충남북)", 35_000, 85_000, 40_000
    ),
    "JEJU": TravelExpenseDef("JEJU", "제주권", 50_000, 100_000, 150_000),
}

TRAVEL_EXPENSE_POLICIES: List[TravelExpenseDef] = list(DEFAULT_TRAVEL_POLICIES.values())

DISCOUNT_POLICIES: List[DiscountPolicyDef] = [
    DiscountPolicyDef(
        "MULTI_STD", "복수규격 통합할인", "PERCENTAGE", 10, max_discount_amount=2_000_000
    ),
    DiscountPolicyDef("RENEWAL", "갱신심사 할인", "PERCENTAGE", 5, None),
    DiscountPolicyDef("SME", "중소기업 정액할인", "FIXED_AMOUNT", 200_000, None),
]
