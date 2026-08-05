"""extend accreditation_bodies + company_standard_accreditations

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-08-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "t0u1v2w3x4y5"
down_revision = "s9t0u1v2w3x4"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if _has_table("accreditation_bodies"):
        if not _has_column("accreditation_bodies", "code"):
            op.add_column("accreditation_bodies", sa.Column("code", sa.String(30), nullable=True))
        if not _has_column("accreditation_bodies", "name_en"):
            op.add_column("accreditation_bodies", sa.Column("name_en", sa.String(300), nullable=True))
        if not _has_column("accreditation_bodies", "continent"):
            op.add_column("accreditation_bodies", sa.Column("continent", sa.String(50), nullable=True))
        if not _has_column("accreditation_bodies", "country_code"):
            op.add_column("accreditation_bodies", sa.Column("country_code", sa.String(10), nullable=True))
        # unique index on code (ignore if exists)
        try:
            op.create_index("uq_accreditation_bodies_code", "accreditation_bodies", ["code"], unique=True)
        except Exception:
            pass

    if not _has_table("company_standard_accreditations"):
        op.create_table(
            "company_standard_accreditations",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("standard_code", sa.String(50), nullable=False, comment="ISO 9001:2015 등"),
            sa.Column("ab_code", sa.String(30), nullable=True, comment="인정기관 이니셜 (KAB 등)"),
            sa.Column("registration_no", sa.String(100), nullable=True, comment="표준별 등록번호"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_company_std_acc_company",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("company_id", "standard_code", name="uq_company_standard_acc"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_company_std_acc_company", "company_standard_accreditations", ["company_id"])


def downgrade() -> None:
    if _has_table("company_standard_accreditations"):
        op.drop_table("company_standard_accreditations")
    if _has_table("accreditation_bodies"):
        for col in ("country_code", "continent", "name_en", "code"):
            if _has_column("accreditation_bodies", col):
                op.drop_column("accreditation_bodies", col)
