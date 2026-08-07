"""iso_audit_kpi_master — ISO 인증심사 KPI (Excel 조항별)

Revision ID: a9b0c1d2e3f4
Revises: j8k9l0m1n2o3
Create Date: 2026-08-07

Additive only. Does NOT drop/truncate kpi_master (ESG),
audit_kpi_master (process/HLS), companies, or CBs.
Seed from ComplAIs_인증심사_KPI목록.xlsx via scripts/seed_iso_audit_kpis.py.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import mysql

revision = "a9b0c1d2e3f4"
down_revision = "j8k9l0m1n2o3"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has_table("iso_audit_kpi_master"):
        return
    op.create_table(
        "iso_audit_kpi_master",
        sa.Column("kpi_id", sa.String(length=40), nullable=False),
        sa.Column(
            "standard_code",
            sa.String(length=30),
            nullable=False,
            comment="ISO9001 / ISO14001 …",
        ),
        sa.Column(
            "standard_sheet",
            sa.String(length=20),
            nullable=True,
            comment="Excel sheet code e.g. 9001",
        ),
        sa.Column(
            "clause_chapter",
            sa.String(length=40),
            nullable=False,
            comment="장/조항 패밀리 (4, 5, … or specialty key)",
        ),
        sa.Column("clause_name", sa.String(length=255), nullable=True),
        sa.Column("kpi_name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column(
            "source",
            sa.String(length=40),
            nullable=False,
            server_default="excel_audit_kpi",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("kpi_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_iso_audit_kpi_std_chapter",
        "iso_audit_kpi_master",
        ["standard_code", "clause_chapter"],
    )
    op.create_index(
        "ix_iso_audit_kpi_std",
        "iso_audit_kpi_master",
        ["standard_code"],
    )


def downgrade() -> None:
    if not _has_table("iso_audit_kpi_master"):
        return
    op.drop_index("ix_iso_audit_kpi_std", table_name="iso_audit_kpi_master")
    op.drop_index("ix_iso_audit_kpi_std_chapter", table_name="iso_audit_kpi_master")
    op.drop_table("iso_audit_kpi_master")
