"""Ensure esg_master_kpis + company ESG runtime tables exist

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-08-07

Additive / idempotent — creates tables only if missing.
Preserves companies/CBs (1134/70). Earlier w3/x4 revisions may be
stamped without tables having been created on this DB.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "k8l9m0n1o2p3"
down_revision = "j7k8l9m0n1o2"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_table("esg_master_kpis"):
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
                comment="세부 조항 번호",
            ),
            sa.Column(
                "is_iso_auditable",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("1"),
            ),
            sa.Column("source_type_code", sa.String(length=20), nullable=False),
            sa.Column("extraction_detail_method", sa.String(length=100), nullable=False),
            sa.Column(
                "is_public_api_available",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "criteria_mapping",
                sa.String(length=150),
                nullable=True,
                comment="ISO/기준 매핑 · 데이터 경로 표시용",
            ),
            sa.Column("description", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("kpi_id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_esg_master_kpis_esg_category", "esg_master_kpis", ["esg_category"]
        )
        op.create_index(
            "ix_esg_master_kpis_managed_standard_name",
            "esg_master_kpis",
            ["managed_standard_name"],
        )
    elif not _has_column("esg_master_kpis", "criteria_mapping"):
        op.add_column(
            "esg_master_kpis",
            sa.Column(
                "criteria_mapping",
                sa.String(length=150),
                nullable=True,
                comment="ISO/기준 매핑 · 데이터 경로 표시용",
            ),
        )

    company_id_col = mysql.INTEGER(unsigned=True)

    if not _has_table("company_esg_kpi_goals"):
        op.create_table(
            "company_esg_kpi_goals",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("target_year", sa.Integer(), nullable=False),
            sa.Column("target_value", sa.String(length=100), nullable=False),
            sa.Column("unit", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", "target_year", name="uq_company_esg_kpi_goal_year"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_kpi_goals_company_id",
            "company_esg_kpi_goals",
            ["company_id"],
        )

    if not _has_table("company_esg_kpi_values"):
        op.create_table(
            "company_esg_kpi_values",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("value", sa.String(length=100), nullable=False),
            sa.Column(
                "source_mode",
                sa.String(length=20),
                nullable=False,
                server_default="company",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", "year", name="uq_company_esg_kpi_value_year"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_kpi_values_company_id",
            "company_esg_kpi_values",
            ["company_id"],
        )

    if not _has_table("company_esg_audit_notes"):
        op.create_table(
            "company_esg_audit_notes",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("note", mysql.MEDIUMTEXT(), nullable=False),
            sa.Column("auditor_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", name="uq_company_esg_audit_note_kpi"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_audit_notes_company_id",
            "company_esg_audit_notes",
            ["company_id"],
        )


def downgrade() -> None:
    # Keep tables — additive ensure migration; do not drop live data.
    pass
