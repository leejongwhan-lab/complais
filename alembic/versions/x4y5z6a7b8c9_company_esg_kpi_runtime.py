"""Add company ESG KPI runtime tables + criteria_mapping

Revision ID: x4y5z6a7b8c9
Revises: w3x4y5z6a7b8
Create Date: 2026-08-05

company_esg_kpi_goals / company_esg_kpi_values / company_esg_audit_notes
align company_id with companies.id (INT).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "x4y5z6a7b8c9"
down_revision = "w3x4y5z6a7b8"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if _has_table("esg_master_kpis") and not _has_column("esg_master_kpis", "criteria_mapping"):
        op.add_column(
            "esg_master_kpis",
            sa.Column(
                "criteria_mapping",
                sa.String(length=150),
                nullable=True,
                comment="ISO/기준 매핑 · 데이터 경로 표시용",
            ),
        )

    # companies.id is INT UNSIGNED — FK columns must match exactly.
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
            sa.ForeignKeyConstraint(["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"),
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
                comment="company | auditor | public",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"),
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
            sa.ForeignKeyConstraint(["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"),
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
    if _has_table("company_esg_audit_notes"):
        op.drop_index(
            "ix_company_esg_audit_notes_company_id",
            table_name="company_esg_audit_notes",
        )
        op.drop_table("company_esg_audit_notes")
    if _has_table("company_esg_kpi_values"):
        op.drop_index(
            "ix_company_esg_kpi_values_company_id",
            table_name="company_esg_kpi_values",
        )
        op.drop_table("company_esg_kpi_values")
    if _has_table("company_esg_kpi_goals"):
        op.drop_index(
            "ix_company_esg_kpi_goals_company_id",
            table_name="company_esg_kpi_goals",
        )
        op.drop_table("company_esg_kpi_goals")
    if _has_table("esg_master_kpis") and _has_column("esg_master_kpis", "criteria_mapping"):
        op.drop_column("esg_master_kpis", "criteria_mapping")
