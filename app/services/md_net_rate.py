"""설문·수동 선택 기반 순 M/D 가/감률 산출 (FE calculateNetMDRate 와 동일).

IAF MD5:2019 §5.4 — 순 가/감률 ±30% 캡.
SUBTRACT 규칙 default_rate 는 음수(예: -10), ADD 는 양수(예: 15).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set

from app.data.md_rules_catalog import MDRuleDef, SurveyQuestionDef, MD_RULES, SURVEY_QUESTIONS

MD_NET_RATE_CAP = 30.0


@dataclass
class MDCalculationResult:
    applied_rules: List[MDRuleDef]
    auto_mapped_rule_ids: List[str]
    manual_rule_ids: List[str]
    total_surcharge: float
    total_discount: float
    raw_net_rate: float
    final_net_rate: float
    active_categories: List[str]


def calculate_net_md_rate(
    selected_standards: Sequence[str],
    survey_answers: Dict[str, bool],
    manual_rule_ids: Optional[Sequence[str]] = None,
    *,
    rules: Optional[Sequence[MDRuleDef]] = None,
    questions: Optional[Sequence[SurveyQuestionDef]] = None,
    net_cap: float = MD_NET_RATE_CAP,
) -> MDCalculationResult:
    """FE ``calculateNetMDRate`` 1:1.

    1) COMMON + selectedStandards, 2개 이상이면 IMS
    2) 활성 카테고리 설문 응답 == trigger_condition → AUTO_MAPPED
    3) manual_rule_ids 병합·중복 제거
    4) ADD/SUBTRACT 합산 (SUBTRACT default_rate 는 음수)
    5) ±net_cap(기본 30) 캡
    """
    manual = list(manual_rule_ids or [])
    rule_list = list(rules if rules is not None else MD_RULES)
    question_list = list(questions if questions is not None else SURVEY_QUESTIONS)

    active_categories: Set[str] = {"COMMON", *selected_standards}
    if len(selected_standards) >= 2:
        active_categories.add("IMS")

    auto_mapped: List[str] = []
    for q in question_list:
        if q.standard_code not in active_categories:
            continue
        user_ans = survey_answers.get(q.id)
        if user_ans is not None and user_ans is q.trigger_condition:
            auto_mapped.append(q.mapped_rule_id)

    applied_ids = list(dict.fromkeys([*auto_mapped, *manual]))
    id_set = set(applied_ids)
    applied_rules = [r for r in rule_list if r.id in id_set]

    total_surcharge = sum(r.default_rate for r in applied_rules if r.type == "ADD")
    total_discount = sum(r.default_rate for r in applied_rules if r.type == "SUBTRACT")
    raw_net = float(total_surcharge + total_discount)
    final_net = max(-net_cap, min(net_cap, raw_net))

    return MDCalculationResult(
        applied_rules=applied_rules,
        auto_mapped_rule_ids=auto_mapped,
        manual_rule_ids=list(manual),
        total_surcharge=float(total_surcharge),
        total_discount=float(total_discount),
        raw_net_rate=raw_net,
        final_net_rate=final_net,
        active_categories=sorted(active_categories),
    )
