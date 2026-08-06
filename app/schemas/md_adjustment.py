"""MD adjustment / survey API schemas."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

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


class MDRuleOut(BaseModel):
    id: str
    standard_code: StandardCode
    code_section: str
    label: str
    type: Literal["ADD", "SUBTRACT"]
    default_rate: float
    source_type: Literal["AUTO_MAPPED", "MANUAL_ONLY"]
    description: str

    class Config:
        from_attributes = True


class SurveyQuestionOut(BaseModel):
    id: str
    standard_code: StandardCode
    question_text: str
    trigger_condition: bool
    mapped_rule_id: str

    class Config:
        from_attributes = True


class MdCatalogMeta(BaseModel):
    rule_count: int
    question_count: int
    rule_target: int = 70
    question_target: int = 44
    ready: bool = Field(description="목표 건수(70/44) 충족 여부")


class MdCatalogBundle(BaseModel):
    meta: MdCatalogMeta
    rules: List[MDRuleOut]
    questions: List[SurveyQuestionOut]


class MDCalculationInput(BaseModel):
    selected_standards: List[StandardCode] = Field(
        ..., description="신청 규격 (예: QMS, OHSMS) — COMMON/IMS 제외"
    )
    survey_answers: Dict[str, bool] = Field(
        default_factory=dict,
        description="{ Q_OHS_01: true, ... }",
    )
    manual_rule_ids: List[str] = Field(
        default_factory=list,
        description="인증원 수동 체크 Rule ID",
    )


class MDCalculationResultOut(BaseModel):
    applied_rules: List[MDRuleOut]
    auto_mapped_rule_ids: List[str]
    manual_rule_ids: List[str]
    total_surcharge: float
    total_discount: float
    raw_net_rate: float
    final_net_rate: float
    active_categories: List[str]
