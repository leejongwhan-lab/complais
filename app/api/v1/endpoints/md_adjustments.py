"""M/D 가·감 규칙 · 동적 설문 조회 API."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.data.md_rules_catalog import (
    MD_RULE_TARGET_COUNT,
    MD_RULES,
    SURVEY_QUESTION_TARGET_COUNT,
    SURVEY_QUESTIONS,
)
from app.models.md_adjustment import MdAdjustmentRule, MdSurveyQuestion
from app.schemas.md_adjustment import (
    MdCatalogBundle,
    MdCatalogMeta,
    MDCalculationInput,
    MDCalculationResultOut,
    MDRuleOut,
    SurveyQuestionOut,
)
from app.services.md_net_rate import calculate_net_md_rate
from app.data.md_rules_catalog import MDRuleDef


router = APIRouter(prefix="/md-adjustments", tags=["MD Adjustments"])


def _rule_out(row: MdAdjustmentRule) -> MDRuleOut:
    return MDRuleOut(
        id=row.id,
        standard_code=row.standard_code,  # type: ignore[arg-type]
        code_section=row.code_section or "",
        label=row.label,
        type=row.adjustment_type,  # type: ignore[arg-type]
        default_rate=float(row.default_rate),
        source_type=row.source_type,  # type: ignore[arg-type]
        description=row.description or "",
    )


def _question_out(row: MdSurveyQuestion) -> SurveyQuestionOut:
    return SurveyQuestionOut(
        id=row.id,
        standard_code=row.standard_code,  # type: ignore[arg-type]
        question_text=row.question_text,
        trigger_condition=bool(row.trigger_condition),
        mapped_rule_id=row.mapped_rule_id,
    )


def _rules_from_catalog(standard_code: Optional[str] = None) -> List[MDRuleOut]:
    rows = MD_RULES
    if standard_code:
        rows = [r for r in rows if r.standard_code == standard_code]
    return [
        MDRuleOut(
            id=r.id,
            standard_code=r.standard_code,
            code_section=r.code_section,
            label=r.label,
            type=r.type,
            default_rate=float(r.default_rate),
            source_type=r.source_type,
            description=r.description,
        )
        for r in rows
    ]


def _questions_from_catalog(standard_code: Optional[str] = None) -> List[SurveyQuestionOut]:
    rows = SURVEY_QUESTIONS
    if standard_code:
        rows = [q for q in rows if q.standard_code == standard_code]
    return [
        SurveyQuestionOut(
            id=q.id,
            standard_code=q.standard_code,
            question_text=q.question_text,
            trigger_condition=q.trigger_condition,
            mapped_rule_id=q.mapped_rule_id,
        )
        for q in rows
    ]


@router.get("/rules", response_model=List[MDRuleOut])
def list_md_rules(
    standard_code: Optional[str] = Query(None, description="familyCode 필터"),
    source_type: Optional[str] = Query(None, description="AUTO_MAPPED|MANUAL_ONLY"),
    db: Session = Depends(get_db),
):
    q = db.query(MdAdjustmentRule).filter(MdAdjustmentRule.is_active.is_(True))
    if standard_code:
        q = q.filter(MdAdjustmentRule.standard_code == standard_code)
    if source_type:
        q = q.filter(MdAdjustmentRule.source_type == source_type)
    rows = q.order_by(
        MdAdjustmentRule.standard_code.asc(),
        MdAdjustmentRule.sort_order.asc(),
        MdAdjustmentRule.id.asc(),
    ).all()
    if rows:
        return [_rule_out(r) for r in rows]
    return _rules_from_catalog(standard_code)


@router.get("/questions", response_model=List[SurveyQuestionOut])
def list_survey_questions(
    standard_code: Optional[str] = Query(None, description="familyCode 필터"),
    db: Session = Depends(get_db),
):
    q = db.query(MdSurveyQuestion).filter(MdSurveyQuestion.is_active.is_(True))
    if standard_code:
        q = q.filter(MdSurveyQuestion.standard_code == standard_code)
    rows = q.order_by(
        MdSurveyQuestion.standard_code.asc(),
        MdSurveyQuestion.sort_order.asc(),
        MdSurveyQuestion.id.asc(),
    ).all()
    if rows:
        return [_question_out(r) for r in rows]
    return _questions_from_catalog(standard_code)


@router.get("/catalog", response_model=MdCatalogBundle)
def get_md_catalog(
    standard_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    rules = list_md_rules(standard_code=standard_code, source_type=None, db=db)
    questions = list_survey_questions(standard_code=standard_code, db=db)
    meta = MdCatalogMeta(
        rule_count=len(rules),
        question_count=len(questions),
        rule_target=MD_RULE_TARGET_COUNT,
        question_target=SURVEY_QUESTION_TARGET_COUNT,
        ready=(
            len(rules) == MD_RULE_TARGET_COUNT
            and len(questions) == SURVEY_QUESTION_TARGET_COUNT
        ),
    )
    return MdCatalogBundle(meta=meta, rules=rules, questions=questions)


def _load_defs_from_db(db: Session) -> tuple[List[MDRuleDef], List]:
    from app.data.md_rules_catalog import SurveyQuestionDef

    rule_rows = (
        db.query(MdAdjustmentRule)
        .filter(MdAdjustmentRule.is_active.is_(True))
        .all()
    )
    q_rows = (
        db.query(MdSurveyQuestion)
        .filter(MdSurveyQuestion.is_active.is_(True))
        .all()
    )
    if not rule_rows:
        return list(MD_RULES), list(SURVEY_QUESTIONS)

    rules = [
        MDRuleDef(
            id=r.id,
            standard_code=r.standard_code,  # type: ignore[arg-type]
            code_section=r.code_section or "",
            label=r.label,
            type=r.adjustment_type,  # type: ignore[arg-type]
            default_rate=float(r.default_rate),
            source_type=r.source_type,  # type: ignore[arg-type]
            description=r.description or "",
        )
        for r in rule_rows
    ]
    questions = [
        SurveyQuestionDef(
            id=q.id,
            standard_code=q.standard_code,  # type: ignore[arg-type]
            question_text=q.question_text,
            trigger_condition=bool(q.trigger_condition),
            mapped_rule_id=q.mapped_rule_id,
        )
        for q in q_rows
    ]
    return rules, questions


@router.post("/calculate", response_model=MDCalculationResultOut)
def calculate_md_net_rate(
    payload: MDCalculationInput,
    db: Session = Depends(get_db),
):
    """설문 AUTO_MAPPED + 수동 요인을 합산해 순 가/감률(±30% 캡)을 반환."""
    rules, questions = _load_defs_from_db(db)
    result = calculate_net_md_rate(
        selected_standards=list(payload.selected_standards),
        survey_answers=payload.survey_answers,
        manual_rule_ids=payload.manual_rule_ids,
        rules=rules,
        questions=questions,
    )
    return MDCalculationResultOut(
        applied_rules=[
            MDRuleOut(
                id=r.id,
                standard_code=r.standard_code,
                code_section=r.code_section,
                label=r.label,
                type=r.type,
                default_rate=float(r.default_rate),
                source_type=r.source_type,
                description=r.description,
            )
            for r in result.applied_rules
        ],
        auto_mapped_rule_ids=result.auto_mapped_rule_ids,
        manual_rule_ids=result.manual_rule_ids,
        total_surcharge=result.total_surcharge,
        total_discount=result.total_discount,
        raw_net_rate=result.raw_net_rate,
        final_net_rate=result.final_net_rate,
        active_categories=result.active_categories,
    )
