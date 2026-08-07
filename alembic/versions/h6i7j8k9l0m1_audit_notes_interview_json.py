"""Add audit_notes interview_json + note_method (면담 / 심사방식)

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-08-07

Additive ALTER only — no DROP of masters / companies / CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "h6i7j8k9l0m1"
down_revision = "g5h6i7j8k9l0"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    row = bind.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c "
            "LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return bool(row)


def _add_column(table: str, ddl: str) -> None:
    # ddl starts with column name, e.g. "`interview_json` LONGTEXT NULL ..."
    col = ddl.split("`")[1] if "`" in ddl else ddl.split()[0]
    if not _has_table(table) or _has_column(table, col):
        return
    op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))


def upgrade() -> None:
    _add_column(
        "audit_notes",
        "`interview_json` LONGTEXT NULL "
        "COMMENT '면담(interview) 기록 JSON — v15 navInterviewData'",
    )
    _add_column(
        "audit_notes",
        "`note_method` VARCHAR(20) NULL DEFAULT 'process' "
        "COMMENT '심사방식: clause=조항심사 | process=프로세스심사'",
    )
    _add_column(
        "audit_note_clauses",
        "`audit_method` VARCHAR(20) NULL "
        "COMMENT '작성 시 심사방식 (clause|process) — 매트릭스 집계는 clause_id'",
    )


def downgrade() -> None:
    # Keep columns (no DROP) — additive-only policy for audit note storage.
    pass
