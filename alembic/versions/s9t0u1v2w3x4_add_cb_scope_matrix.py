"""add cb_scope_matrix for CB ISO×IAF accreditation scopes

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "s9t0u1v2w3x4"
down_revision = "r8s9t0u1v2w3"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has_table("cb_scope_matrix"):
        return
    op.create_table(
        "cb_scope_matrix",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("standard_code", sa.String(50), nullable=False),
        sa.Column("iaf_code", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("granted_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["cb_id"],
            ["certification_bodies.id"],
            name="fk_cb_scope_matrix_cb",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("cb_id", "standard_code", "iaf_code", name="uk_cb_scope_matrix"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_cb_scope_matrix_cb_id", "cb_scope_matrix", ["cb_id"])


def downgrade() -> None:
    if _has_table("cb_scope_matrix"):
        op.drop_table("cb_scope_matrix")
