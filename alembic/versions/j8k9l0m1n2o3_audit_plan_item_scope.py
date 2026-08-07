"""Extend audit_plan_items for auditor/process/clause scope

Revision ID: j8k9l0m1n2o3
Revises: i7j8k9l0m1n2
Create Date: 2026-08-07

Additive ALTER only — enable 심사노트 plan scoping + NC autofill.
No DROP of masters / companies / CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "j8k9l0m1n2o3"
down_revision = "i7j8k9l0m1n2"
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
    if _has_column(table, col):
        return
    op.execute(sa.text(f"ALTER TABLE `{table}` ADD COLUMN {ddl}"))


def upgrade() -> None:
    if not _has_table("audit_plan_items"):
        return
    _add_column("audit_plan_items", "`auditor_id` INT NULL")
    _add_column("audit_plan_items", "`process_group_id` VARCHAR(50) NULL")
    _add_column("audit_plan_items", "`clause_no` VARCHAR(40) NULL")
    _add_column("audit_plan_items", "`dept` VARCHAR(120) NULL")
    _add_column("audit_plan_items", "`standard_code` VARCHAR(30) NULL")
    _add_column("audit_plan_items", "`standard_key` VARCHAR(40) NULL")
    # helpful indexes (ignore if exist)
    bind = op.get_bind()
    for name, ddl in [
        (
            "ix_audit_plan_items_auditor",
            "CREATE INDEX ix_audit_plan_items_auditor ON audit_plan_items (audit_plan_id, auditor_id)",
        ),
        (
            "ix_audit_plan_items_clause",
            "CREATE INDEX ix_audit_plan_items_clause ON audit_plan_items (audit_plan_id, clause_no)",
        ),
    ]:
        try:
            exists = bind.execute(
                text(
                    "SELECT 1 FROM information_schema.statistics "
                    "WHERE table_schema=DATABASE() AND table_name='audit_plan_items' "
                    "AND index_name=:n LIMIT 1"
                ),
                {"n": name},
            ).first()
            if not exists:
                op.execute(sa.text(ddl))
        except Exception:
            pass


def downgrade() -> None:
    # Additive-only policy: do not drop columns in downgrade
    pass
