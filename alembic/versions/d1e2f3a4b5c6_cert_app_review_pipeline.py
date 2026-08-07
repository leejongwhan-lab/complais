"""certification application review pipeline columns/tables

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-08-07

Additive only (soft-fail):
- certification_applications.integrated_check_json
- certification_application_md_reviews
- company_ksic_codes

No DROP/TRUNCATE. Preserves companies / CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
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
    if _has_table("certification_applications") and not _has_column(
        "certification_applications", "integrated_check_json"
    ):
        op.add_column(
            "certification_applications",
            sa.Column(
                "integrated_check_json",
                sa.Text(),
                nullable=True,
                comment="IAF MD11 통합심사 7문항 yes/no JSON",
            ),
        )

    if not _has_table("certification_application_md_reviews"):
        op.create_table(
            "certification_application_md_reviews",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("application_id", sa.Integer(), nullable=False),
            sa.Column("base_md", sa.Float(), nullable=False, server_default="0"),
            sa.Column("base_md_detail_json", sa.Text(), nullable=True),
            sa.Column("base_md_calculated_at", sa.DateTime(), nullable=True),
            sa.Column("base_md_calculated_by", sa.String(length=50), nullable=True),
            sa.Column("add_pct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("subtract_pct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("add_md", sa.Float(), nullable=False, server_default="0"),
            sa.Column("subtract_md", sa.Float(), nullable=False, server_default="0"),
            sa.Column("final_md", sa.Float(), nullable=False, server_default="0"),
            sa.Column("calculation_note", sa.Text(), nullable=True),
            sa.Column("reviewer_user_id", sa.Integer(), nullable=True),
            sa.Column("reviewer_role", sa.String(length=50), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("application_id", name="uq_cert_app_md_reviews_app_id"),
        )
        op.create_index(
            "ix_cert_app_md_reviews_application_id",
            "certification_application_md_reviews",
            ["application_id"],
            unique=True,
        )

    if not _has_table("company_ksic_codes"):
        op.create_table(
            "company_ksic_codes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("company_id", sa.Integer(), nullable=False),
            sa.Column("ksic_code", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_company_ksic_codes_company_id",
            "company_ksic_codes",
            ["company_id"],
            unique=False,
        )


def downgrade() -> None:
    # Additive-only policy: intentionally no destructive downgrade.
    pass
