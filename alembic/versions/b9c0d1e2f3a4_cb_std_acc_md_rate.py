"""cb_standard_accreditations.md_rate — 표준(Scope)별 MD 단가

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-08-07

CB 보유 표준 행마다 MD 단가(KRW)를 둔다. nullable — 미설정 시
cb_contracts.price_per_md → 0 순으로 fallback.
Additive ALTER only. No DROP/TRUNCATE of master tables.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "b9c0d1e2f3a4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_table("cb_standard_accreditations"):
        return
    if not _has_column("cb_standard_accreditations", "md_rate"):
        op.add_column(
            "cb_standard_accreditations",
            sa.Column(
                "md_rate",
                sa.Numeric(precision=12, scale=0),
                nullable=True,
                comment="표준별 MD 단가(KRW)",
            ),
        )


def downgrade() -> None:
    if _has_column("cb_standard_accreditations", "md_rate"):
        op.drop_column("cb_standard_accreditations", "md_rate")
