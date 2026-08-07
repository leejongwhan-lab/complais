"""Add audit_note_clauses master terminology columns

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-08-07

Additive ALTER only — maps UI fields to master DB terms:
standard_code, process_group_id, hls_code, clause_topic.
No DROP of masters / companies / CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "i7j8k9l0m1n2"
down_revision = "h6i7j8k9l0m1"
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
    col = ddl.split("`")[1] if "`" in ddl else ddl.split()[0]
    if not _has_table(table) or _has_column(table, col):
        return
    op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))


def upgrade() -> None:
    _add_column(
        "audit_note_clauses",
        "`standard_code` VARCHAR(30) NULL "
        "COMMENT 'standard_master.standard_code (ISO9001…)'",
    )
    _add_column(
        "audit_note_clauses",
        "`process_group_id` VARCHAR(10) NULL "
        "COMMENT 'process_group_master.process_group_id'",
    )
    _add_column(
        "audit_note_clauses",
        "`hls_code` VARCHAR(20) NULL "
        "COMMENT 'hls_master.hls_code'",
    )
    _add_column(
        "audit_note_clauses",
        "`clause_topic` VARCHAR(255) NULL "
        "COMMENT 'standard_process_clause_map.clause_topic / HLS title'",
    )


def downgrade() -> None:
    # Keep columns (no DROP) — additive-only policy.
    pass
