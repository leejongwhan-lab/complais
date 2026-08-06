"""기업 계약금 및 심사원 정산금(수수료) 산출 로직.

고액 계약 공제(기준 금액 / 공제 비율)는 항상 호출자가 전달하는 파라미터로만 결정되며,
이 모듈 내부에 특정 금액이나 비율을 하드코딩하지 않는다.
`high_value_threshold`가 0이거나 지정되지 않으면 고액 공제는 적용되지 않는다.
"""


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
