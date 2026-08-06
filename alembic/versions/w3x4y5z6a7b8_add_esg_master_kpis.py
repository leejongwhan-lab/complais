"""Add esg_master_kpis table (ESG master KPI catalog)

Revision ID: w3x4y5z6a7b8
Revises: v2w3x4y5z6a7
Create Date: 2026-08-05

MySQL DDL: ENUM E/S/G, BOOLEAN defaults, TEXT description.
managed_standard_name is VARCHAR (14대 공식명); no FK to standard_masters
(platform currently seeds 15 versioned ISO codes).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "w3x4y5z6a7b8"
down_revision = "v2w3x4y5z6a7"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has_table("esg_master_kpis"):
        return

    op.create_table(
        "esg_master_kpis",
        sa.Column("kpi_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "esg_category",
            mysql.ENUM("E", "S", "G", name="esg_master_kpi_category"),
            nullable=False,
        ),
        sa.Column("sub_category", sa.String(length=100), nullable=False),
        sa.Column("kpi_name", sa.String(length=200), nullable=False),
        sa.Column(
            "is_quantitative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("unit_format", sa.String(length=50), nullable=False),
        sa.Column(
            "managed_standard_name",
            sa.String(length=150),
            nullable=False,
            comment="14대 공식 관리 표준명",
        ),
        sa.Column(
            "iso_clause_detail",
            sa.String(length=150),
            nullable=False,
            comment="세부 조항 번호 (예: 6.1.2 환경측면)",
        ),
        sa.Column(
            "is_iso_auditable",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("1"),
            comment="ISO 심사 검증 가능 여부",
        ),
        sa.Column("source_type_code", sa.String(length=20), nullable=False),
        sa.Column(
            "extraction_detail_method",
            sa.String(length=100),
            nullable=False,
            comment="A-1 ~ C-2 7단계 상세 추출 방식",
        ),
        sa.Column(
            "is_public_api_available",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("0"),
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("kpi_id"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_esg_master_kpis_esg_category",
        "esg_master_kpis",
        ["esg_category"],
    )
    op.create_index(
        "ix_esg_master_kpis_managed_standard_name",
        "esg_master_kpis",
        ["managed_standard_name"],
    )


def downgrade() -> None:
    if not _has_table("esg_master_kpis"):
        return
    op.drop_index("ix_esg_master_kpis_managed_standard_name", table_name="esg_master_kpis")
    op.drop_index("ix_esg_master_kpis_esg_category", table_name="esg_master_kpis")
    op.drop_table("esg_master_kpis")
