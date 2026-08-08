"""기업 계약금 및 심사원 정산금(수수료) 산출 로직.

고액 계약 공제(기준 금액 / 공제 비율)는 항상 호출자가 전달하는 파라미터로만 결정되며,
이 모듈 내부에 특정 금액이나 비율을 하드코딩하지 않는다.
`high_value_threshold`가 0이거나 지정되지 않으면 고액 공제는 적용되지 않는다.

배정 건별(PERCENTAGE / DAILY_RATE)은 calculate_assignment_fee 로 병행한다.
"""
from __future__ import annotations


def calculate_contract_settlement(
    fee_calculation_type: str,          # "PERCENTAGE" 또는 "FLAT_FEE"
    agreed_amount: float,               # 순수 기업 계약금 (부가세/출장비 제외)
    travel_expense: float = 0.0,        # 출장비
    fee_ratio: float = 0.80,            # 정률 모델 시 심사원 비율 (예: 80%)
    flat_fee: float = 0.0,              # 정액 모델 시 기본 고정 금액
    high_value_threshold: float = 0.0,  # 가변 기준 금액 (예: 2,000,000 또는 5,000,000 / 0이면 미적용)
    high_value_deduction_rate: float = 0.0,  # 가변 공제 비율 (예: 5.0 = 5% 또는 0.05)
) -> dict:
    """
    기업 계약금 및 심사원 최종 정산액 산출 로직 (기준금액 & 공제율 완전 가변형)
    """
    # 1. 모델별 정산 기준금 계산
    if fee_calculation_type == "PERCENTAGE":
        base_fee = agreed_amount * fee_ratio
    else:  # FLAT_FEE
        base_fee = flat_fee

    # 2. 지정한 기준 금액 이상이고, 공제 비율이 설정되어 있을 때만 추가 공제 적용
    extra_deduction = 0.0
    if high_value_threshold > 0 and agreed_amount >= high_value_threshold and high_value_deduction_rate > 0:
        rate = high_value_deduction_rate / 100.0 if high_value_deduction_rate > 1.0 else high_value_deduction_rate
        extra_deduction = base_fee * rate

    # 3. 최종 심사원 정산 지급액
    final_auditor_fee = base_fee - extra_deduction

    return {
        "agreed_amount": agreed_amount,
        "travel_expense": travel_expense,
        "vat_amount": agreed_amount * 0.10,
        "total_contract_amount": agreed_amount + travel_expense + (agreed_amount * 0.10),
        "base_settlement_fee": base_fee,
        "extra_deduction": extra_deduction,
        "final_auditor_fee": final_auditor_fee,
    }


def _normalize_ratio(fee_ratio: float) -> float:
    """80 → 0.80, 0.80 → 0.80. 0 이하면 0."""
    if fee_ratio is None:
        return 0.0
    r = float(fee_ratio)
    if r <= 0:
        return 0.0
    return r / 100.0 if r > 1.0 else r


def calculate_assignment_fee(
    fee_type: str,
    *,
    agreed_amount: float = 0.0,
    fee_ratio: float = 0.0,
    daily_rate: float = 0.0,
    assigned_days: float = 0.0,
) -> dict:
    """배정 1건 수수료 산출. fee_type: PERCENTAGE | DAILY_RATE."""
    ftype = (fee_type or "").strip().upper()
    if ftype == "PERCENTAGE":
        ratio = _normalize_ratio(fee_ratio)
        calculated = float(agreed_amount or 0.0) * ratio
    elif ftype == "DAILY_RATE":
        calculated = float(daily_rate or 0.0) * float(assigned_days or 0.0)
    else:
        raise ValueError(f"지원하지 않는 fee_type: {fee_type}")

    return {
        "fee_type": ftype,
        "agreed_amount": float(agreed_amount or 0.0),
        "fee_ratio": float(fee_ratio or 0.0),
        "daily_rate": float(daily_rate or 0.0),
        "assigned_days": float(assigned_days or 0.0),
        "calculated_fee": round(calculated, 2),
    }


def calculate_daily_rate_settlement(
    daily_rate: float,
    assigned_days: float,
    travel_expense: float = 0.0,
) -> dict:
    """일당 정산 헬퍼 — calculate_contract_settlement 와 병행."""
    base = float(daily_rate or 0.0) * float(assigned_days or 0.0)
    return {
        "fee_calculation_type": "DAILY_RATE",
        "daily_rate": float(daily_rate or 0.0),
        "assigned_days": float(assigned_days or 0.0),
        "travel_expense": float(travel_expense or 0.0),
        "base_settlement_fee": base,
        "extra_deduction": 0.0,
        "final_auditor_fee": base,
        "total_payout": base + float(travel_expense or 0.0),
    }


def resolve_fee_type_for_auditor(*, is_managed_company: bool) -> str:
    """관리기업 ACTIVE → PERCENTAGE, 그 외(지원) → DAILY_RATE."""
    return "PERCENTAGE" if is_managed_company else "DAILY_RATE"
