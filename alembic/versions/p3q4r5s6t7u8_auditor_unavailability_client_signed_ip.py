"""auditor_unavailability + contracts.client_signed_ip

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-08-08

ADDITIVE only.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "p3q4r5s6t7u8"
down_revision = "o2p3q4r5s6t7"
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
    if _has_table("contracts") and not _has_column("contracts", "client_signed_ip"):
        op.add_column(
            "contracts",
            sa.Column(
                "client_signed_ip",
                sa.String(length=45),
                nullable=True,
                comment="기업 확인(동의) 시 클라이언트 IP",
            ),
        )

    if not _has_table("auditor_unavailability"):
        op.create_table(
            "auditor_unavailability",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("auditor_id", sa.Integer(), nullable=False, index=True),
            sa.Column("start_date", sa.Date(), nullable=False),
            sa.Column("end_date", sa.Date(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True, comment="불가 사유"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_auditor_unavailability_range",
            "auditor_unavailability",
            ["auditor_id", "start_date", "end_date"],
        )


def downgrade() -> None:
    if _has_table("auditor_unavailability"):
        op.drop_table("auditor_unavailability")
    if _has_table("contracts") and _has_column("contracts", "client_signed_ip"):
        op.drop_column("contracts", "client_signed_ip")
