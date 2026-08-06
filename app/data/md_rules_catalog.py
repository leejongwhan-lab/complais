"""M/D 가·감 규칙 · 설문 카탈로그 (FE types/standard.ts 와 동일 스키마).

시드 목표: MD_RULES 70 · SURVEY_QUESTIONS 44.
행 데이터가 확정되면 이 모듈에 채운 뒤 scripts/seed_md_adjustments.py 실행.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal

StandardCode = Literal[
    "COMMON",
    "IMS",
    "QMS",
    "EMS",
    "OHSMS",
    "ISMS",
    "ABMS",
    "CMS",
    "EnMS",
    "FSMS",
    "MDQMS",
    "NSMS",
    "PIMS",
    "AIMS",
]

AdjustmentType = Literal["ADD", "SUBTRACT"]
AdjustmentSourceType = Literal["AUTO_MAPPED", "MANUAL_ONLY"]

MD_RULE_TARGET_COUNT = 70
SURVEY_QUESTION_TARGET_COUNT = 44

STANDARD_CODES: List[StandardCode] = [
    "COMMON",
    "IMS",
    "QMS",
    "EMS",
    "OHSMS",
    "ISMS",
    "ABMS",
    "CMS",
    "EnMS",
    "FSMS",
    "MDQMS",
    "NSMS",
    "PIMS",
    "AIMS",
]


@dataclass(frozen=True)
class MDRuleDef:
    id: str
    standard_code: StandardCode
    code_section: str
    label: str
    type: AdjustmentType
    default_rate: float
    source_type: AdjustmentSourceType
    description: str


@dataclass(frozen=True)
class SurveyQuestionDef:
    id: str
    standard_code: StandardCode
    question_text: str
    trigger_condition: bool
    mapped_rule_id: str


# TODO: 70개 규칙 행을 아래에 채운다.
MD_RULES: List[MDRuleDef] = []

# TODO: 44개 설문 행을 아래에 채운다. mapped_rule_id 는 MD_RULES.id 를 참조.
SURVEY_QUESTIONS: List[SurveyQuestionDef] = []


def validate_catalog() -> None:
    """시드 전 무결성 검사 (데이터가 있을 때만 건수 assert)."""
    rule_ids = {r.id for r in MD_RULES}
    if len(rule_ids) != len(MD_RULES):
        raise ValueError("MD_RULES id 중복")
    for q in SURVEY_QUESTIONS:
        if q.mapped_rule_id not in rule_ids:
            raise ValueError(f"{q.id} mapped_rule_id 없음: {q.mapped_rule_id}")
    if MD_RULES and len(MD_RULES) != MD_RULE_TARGET_COUNT:
        raise ValueError(
            f"MD_RULES 건수 {len(MD_RULES)} != 목표 {MD_RULE_TARGET_COUNT}"
        )
    if SURVEY_QUESTIONS and len(SURVEY_QUESTIONS) != SURVEY_QUESTION_TARGET_COUNT:
        raise ValueError(
            f"SURVEY_QUESTIONS 건수 {len(SURVEY_QUESTIONS)} "
            f"!= 목표 {SURVEY_QUESTION_TARGET_COUNT}"
        )
