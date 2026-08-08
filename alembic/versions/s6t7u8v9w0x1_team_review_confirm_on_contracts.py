"""contracts.team_review_confirmed_* for NCR team-meeting gate

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-08-08

ADDITIVE only — no DROP/TRUNCATE.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "s6t7u8v9w0x1"
down_revision = "r5s6t7u8v9w0"
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
    if not _has_table("contracts"):
        return
    if not _has_column("contracts", "team_review_confirmed_at"):
        op.add_column(
            "contracts",
            sa.Column(
                "team_review_confirmed_at",
                sa.DateTime(),
                nullable=True,
                comment="심사팀장 팀검토(회의) 확인 시각",
            ),
        )
    if not _has_column("contracts", "team_review_confirmed_by"):
        op.add_column(
            "contracts",
            sa.Column(
                "team_review_confirmed_by",
                sa.Integer(),
                nullable=True,
                comment="팀검토 확인 user_id",
            ),
        )


def downgrade() -> None:
    if not _has_table("contracts"):
        return
    if _has_column("contracts", "team_review_confirmed_by"):
        op.drop_column("contracts", "team_review_confirmed_by")
    if _has_column("contracts", "team_review_confirmed_at"):
        op.drop_column("contracts", "team_review_confirmed_at")
