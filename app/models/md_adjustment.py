"""M/D 가·감 규칙 · 동적 설문 마스터.

standard_code = familyCode (COMMON/QMS/…) — 판본 키(standard_key)와 분리.
시드 목표: md_adjustment_rules 70행, md_survey_questions 44행.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MdAdjustmentRule(Base):
    """M/D 가·감 요인 (MDRule)."""

    __tablename__ = "md_adjustment_rules"

    id = Column(String(40), primary_key=True, comment="RULE_OHS_01")
    standard_code = Column(String(20), nullable=False, index=True, comment="familyCode")
    code_section = Column(String(80), nullable=False, default="")
    label = Column(String(255), nullable=False)
    adjustment_type = Column(String(20), nullable=False, comment="ADD|SUBTRACT")
    default_rate = Column(Numeric(6, 2), nullable=False, comment="가/감 비율 %")
    source_type = Column(String(20), nullable=False, comment="AUTO_MAPPED|MANUAL_ONLY")
    description = Column(Text, nullable=False, default="")
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    survey_questions = relationship(
        "MdSurveyQuestion",
        back_populates="mapped_rule",
        foreign_keys="MdSurveyQuestion.mapped_rule_id",
    )


class MdSurveyQuestion(Base):
    """동적 설문 문항 (SurveyQuestion)."""

    __tablename__ = "md_survey_questions"

    id = Column(String(40), primary_key=True, comment="Q_OHS_01")
    standard_code = Column(String(20), nullable=False, index=True, comment="familyCode")
    question_text = Column(Text, nullable=False)
    trigger_condition = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="True='예' 선택 시 규칙 발동",
    )
    mapped_rule_id = Column(
        String(40),
        ForeignKey("md_adjustment_rules.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    mapped_rule = relationship(
        "MdAdjustmentRule",
        back_populates="survey_questions",
        foreign_keys=[mapped_rule_id],
    )
