"""Create md_adjustment_rules / md_survey_questions and upsert from catalog."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy import text

from app.data.md_rules_catalog import (
    MD_RULE_TARGET_COUNT,
    MD_RULES,
    SURVEY_QUESTION_TARGET_COUNT,
    SURVEY_QUESTIONS,
    validate_catalog,
)
from app.db.session import SessionLocal, engine
from app.models.md_adjustment import MdAdjustmentRule, MdSurveyQuestion

DDL_RULES = """
CREATE TABLE IF NOT EXISTS md_adjustment_rules (
  id VARCHAR(40) NOT NULL,
  standard_code VARCHAR(20) NOT NULL,
  code_section VARCHAR(80) NOT NULL DEFAULT '',
  label VARCHAR(255) NOT NULL,
  adjustment_type VARCHAR(20) NOT NULL,
  default_rate DECIMAL(6,2) NOT NULL,
  source_type VARCHAR(20) NOT NULL,
  description TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_md_rule_std (standard_code),
  KEY idx_md_rule_source (source_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

DDL_QUESTIONS = """
CREATE TABLE IF NOT EXISTS md_survey_questions (
  id VARCHAR(40) NOT NULL,
  standard_code VARCHAR(20) NOT NULL,
  question_text TEXT NOT NULL,
  trigger_condition TINYINT(1) NOT NULL DEFAULT 1,
  mapped_rule_id VARCHAR(40) NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  KEY idx_md_q_std (standard_code),
  KEY idx_md_q_rule (mapped_rule_id),
  CONSTRAINT fk_md_q_rule
    FOREIGN KEY (mapped_rule_id) REFERENCES md_adjustment_rules(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def ensure_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text(DDL_RULES))
        conn.execute(text(DDL_QUESTIONS))


def seed_md_adjustments() -> None:
    validate_catalog()
    ensure_schema()
    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        if not MD_RULES:
            print(
                f"[WARN] MD_RULES 비어 있음 — 테이블만 생성 "
                f"(목표 {MD_RULE_TARGET_COUNT}/{SURVEY_QUESTION_TARGET_COUNT})"
            )
            db.commit()
            return

        for i, r in enumerate(MD_RULES):
            row = db.get(MdAdjustmentRule, r.id)
            if row is None:
                row = MdAdjustmentRule(id=r.id)
                db.add(row)
            row.standard_code = r.standard_code
            row.code_section = r.code_section
            row.label = r.label
            row.adjustment_type = r.type
            row.default_rate = r.default_rate
            row.source_type = r.source_type
            row.description = r.description
            row.sort_order = i
            row.is_active = True
            row.updated_at = now

        db.flush()

        for i, q in enumerate(SURVEY_QUESTIONS):
            row = db.get(MdSurveyQuestion, q.id)
            if row is None:
                row = MdSurveyQuestion(id=q.id)
                db.add(row)
            row.standard_code = q.standard_code
            row.question_text = q.question_text
            row.trigger_condition = q.trigger_condition
            row.mapped_rule_id = q.mapped_rule_id
            row.sort_order = i
            row.is_active = True
            row.updated_at = now

        db.commit()
        rc = db.query(MdAdjustmentRule).filter(MdAdjustmentRule.is_active.is_(True)).count()
        qc = db.query(MdSurveyQuestion).filter(MdSurveyQuestion.is_active.is_(True)).count()
        print(f"[OK] md_adjustment_rules={rc} (target {MD_RULE_TARGET_COUNT})")
        print(f"[OK] md_survey_questions={qc} (target {SURVEY_QUESTION_TARGET_COUNT})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_md_adjustments()
