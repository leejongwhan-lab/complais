"""MD(Man-Day) 산정 및 행정 가감 검토 계산 로직."""
import math


def round_half(val: float) -> float:
    """0.5 단위 반올림 (IAF MD5/MD11 실무 표준)"""
    return round(val * 2.0) / 2.0


def calculate_review_md(base_md: float, add_pct: int, subtract_pct: int, is_integrated: bool = False):
    """
    기본 MD와 선택된 가/감산 비율을 받아 순가감 한도(20% 또는 30%) 체크 후 최종 MD 계산
    """
    if base_md <= 0:
        return 0.0, 0.0, 0.0

    limit_pct = 20 if is_integrated else 30
    net_pct = add_pct - subtract_pct

    # 순가감 한도 제한
    if net_pct > limit_pct:
        add_pct = subtract_pct + limit_pct
    elif net_pct < -limit_pct:
        subtract_pct = add_pct + limit_pct

    add_md = base_md * (add_pct / 100.0)
    subtract_md = base_md * (subtract_pct / 100.0)

    # 최종 MD 계산 및 0.5 M/D 단위 정단
    raw_final = max(0.0, base_md + add_md - subtract_md)
    final_md = round_half(raw_final)

    return round(add_md, 2), round(subtract_md, 2), final_md
