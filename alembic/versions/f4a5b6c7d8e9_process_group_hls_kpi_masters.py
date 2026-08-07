"""Process-group / HLS / standard-map / audit KPI masters

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-07

Additive only — CREATE TABLE IF NOT EXISTS (InnoDB utf8mb4).
Does NOT drop/truncate existing masters (companies, CBs, esg, iso_clauses_master).

Name conflicts:
- kpi_master already holds ESG KPIs (264 rows) → use audit_kpi_master
- standard_masters (plural) is the platform operating-standards table →
  standard_master (singular) is free and matches the Excel DDL name
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("process_group_master"):
        op.create_table(
            "process_group_master",
            sa.Column("process_group_id", sa.String(10), primary_key=True),
            sa.Column("process_group_name", sa.String(100), nullable=False),
            sa.Column("hls_scope_desc", sa.String(255), nullable=True),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table("standard_master"):
        op.create_table(
            "standard_master",
            sa.Column("standard_code", sa.String(30), primary_key=True),
            sa.Column("standard_name", sa.String(200), nullable=False),
            sa.Column(
                "hls_adopted",
                sa.String(10),
                nullable=False,
                server_default="Y",
                comment="Y / N / Y* (extension)",
            ),
            sa.Column("native_structure_note", sa.Text(), nullable=True),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table("hls_master"):
        op.create_table(
            "hls_master",
            sa.Column("hls_code", sa.String(20), primary_key=True),
            sa.Column("checkpoints_summary", sa.Text(), nullable=True),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table("process_group_hls_map"):
        op.create_table(
            "process_group_hls_map",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("process_group_id", sa.String(10), nullable=False),
            sa.Column("hls_code", sa.String(20), nullable=False),
            sa.ForeignKeyConstraint(
                ["process_group_id"],
                ["process_group_master.process_group_id"],
                name="fk_pg_hls_map_pg",
            ),
            sa.ForeignKeyConstraint(
                ["hls_code"],
                ["hls_master.hls_code"],
                name="fk_pg_hls_map_hls",
            ),
            sa.UniqueConstraint(
                "process_group_id",
                "hls_code",
                name="uq_process_group_hls",
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

    if not _has_table("standard_process_clause_map"):
        op.create_table(
            "standard_process_clause_map",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("standard_code", sa.String(30), nullable=False),
            sa.Column("process_group_id", sa.String(10), nullable=False),
            sa.Column("actual_clause_no", sa.String(30), nullable=False),
            sa.Column("clause_topic", sa.String(255), nullable=True),
            sa.Column("guide_note", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["standard_code"],
                ["standard_master.standard_code"],
                name="fk_std_proc_clause_std",
            ),
            sa.ForeignKeyConstraint(
                ["process_group_id"],
                ["process_group_master.process_group_id"],
                name="fk_std_proc_clause_pg",
            ),
            sa.UniqueConstraint(
                "standard_code",
                "process_group_id",
                "actual_clause_no",
                name="uq_std_proc_clause",
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "ix_std_proc_clause_std",
            "standard_process_clause_map",
            ["standard_code"],
        )
        op.create_index(
            "ix_std_proc_clause_pg",
            "standard_process_clause_map",
            ["process_group_id"],
        )

    if not _has_table("standard_clause_map"):
        op.create_table(
            "standard_clause_map",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("standard_code", sa.String(30), nullable=False),
            sa.Column("hls_code", sa.String(20), nullable=False),
            sa.Column("actual_clause_no", sa.String(30), nullable=True),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="DIRECT",
                comment="DIRECT / INTEGRATED / RENUMBERED / …",
            ),
            sa.Column("integrated_into_hls_code", sa.String(20), nullable=True),
            sa.Column("guide_note", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["standard_code"],
                ["standard_master.standard_code"],
                name="fk_std_clause_map_std",
            ),
            sa.ForeignKeyConstraint(
                ["hls_code"],
                ["hls_master.hls_code"],
                name="fk_std_clause_map_hls",
            ),
            sa.UniqueConstraint(
                "standard_code",
                "hls_code",
                name="uq_std_clause_hls",
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "ix_std_clause_map_std",
            "standard_clause_map",
            ["standard_code"],
        )

    # Alias of Excel KPI_MASTER — do NOT reuse ESG kpi_master
    if not _has_table("audit_kpi_master"):
        op.create_table(
            "audit_kpi_master",
            sa.Column("kpi_id", sa.String(30), primary_key=True),
            sa.Column("hls_code", sa.String(20), nullable=False),
            sa.Column(
                "standard_code",
                sa.String(30),
                nullable=False,
                server_default="COMMON",
                comment="COMMON = shared across standards; else ISO####",
            ),
            sa.Column("kpi_name", sa.String(255), nullable=False),
            sa.Column(
                "kpi_type",
                mysql.ENUM(
                    "RATIO",
                    "COUNT",
                    "PERIOD",
                    "TREND",
                    name="audit_kpi_type",
                ),
                nullable=False,
            ),
            sa.Column("formula", sa.Text(), nullable=True),
            sa.Column("unit", sa.String(50), nullable=True),
            sa.ForeignKeyConstraint(
                ["hls_code"],
                ["hls_master.hls_code"],
                name="fk_audit_kpi_hls",
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "ix_audit_kpi_hls",
            "audit_kpi_master",
            ["hls_code"],
        )
        op.create_index(
            "ix_audit_kpi_std",
            "audit_kpi_master",
            ["standard_code"],
        )


def downgrade() -> None:
    # Additive-only policy: do not drop master data tables in downgrade.
    pass
