"""audit_note_clauses.note_seq — 프로세스심사 추가 노트

Revision ID: m0n1o2p3q4r5
Revises: a9b0c1d2e3f4
Create Date: 2026-08-07

Additive ALTER only. Allows multiple 심사노트 rows per
(note_id, standard, clause_id) via note_seq (1=기본, 2+=추가).
Does NOT drop/truncate masters / companies / CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "m0n1o2p3q4r5"
down_revision = "a9b0c1d2e3f4"
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


def upgrade() -> None:
    if not _has_table("audit_note_clauses") or _has_column(
        "audit_note_clauses", "note_seq"
    ):
        return
    op.execute(
        sa.text(
            "ALTER TABLE `audit_note_clauses` ADD COLUMN `note_seq` INT NOT NULL "
            "DEFAULT 1 COMMENT '1=기본 조항노트, 2+=프로세스심사 추가노트'"
        )
    )


def downgrade() -> None:
    # Keep column (additive-only policy).
    pass
