"""cb_standard_accreditations + drop company_standard_accreditations

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "u1v2w3x4y5z6"
down_revision = "t0u1v2w3x4y5"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has_table("company_standard_accreditations"):
        op.drop_table("company_standard_accreditations")

    if not _has_table("cb_standard_accreditations"):
        op.create_table(
            "cb_standard_accreditations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("standard_code", sa.String(50), nullable=False, comment="ISO 9001:2015 등"),
            sa.Column("ab_code", sa.String(30), nullable=True, comment="인정기관 이니셜 KAB 등"),
            sa.Column("registration_no", sa.String(100), nullable=True, comment="표준별 등록번호"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["cb_id"],
                ["certification_bodies.id"],
                name="fk_cb_std_acc_cb",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("cb_id", "standard_code", name="uq_cb_standard_acc"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_cb_std_acc_cb", "cb_standard_accreditations", ["cb_id"])


def downgrade() -> None:
    if _has_table("cb_standard_accreditations"):
        op.drop_table("cb_standard_accreditations")
