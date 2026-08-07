"""MD design exclusion columns + company_certificates

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-08-07

Additive only — no DROP/TRUNCATE. Preserves companies/CBs (1134/70).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
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
    if _has_table("certification_applications"):
        if not _has_column("certification_applications", "is_design_excluded"):
            op.add_column(
                "certification_applications",
                sa.Column(
                    "is_design_excluded",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                    comment="QMS/MDMS design exclusion applied",
                ),
            )
        if not _has_column("certification_applications", "exclusion_note"):
            op.add_column(
                "certification_applications",
                sa.Column(
                    "exclusion_note",
                    sa.Text(),
                    nullable=True,
                    comment="Other exclusions (partial mfg, outsourced process, etc.)",
                ),
            )

    if _has_table("certification_application_md_reviews"):
        if not _has_column("certification_application_md_reviews", "is_design_excluded"):
            op.add_column(
                "certification_application_md_reviews",
                sa.Column(
                    "is_design_excluded",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                    comment="Design exclusion flag mirrored from review",
                ),
            )
        if not _has_column("certification_application_md_reviews", "exclusion_note"):
            op.add_column(
                "certification_application_md_reviews",
                sa.Column(
                    "exclusion_note",
                    sa.Text(),
                    nullable=True,
                    comment="Other exclusion notes from MD review",
                ),
            )

    if not _has_table("company_certificates"):
        op.create_table(
            "company_certificates",
            sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
            sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column(
                "standard_code",
                sa.String(50),
                nullable=False,
                comment="ISO code or family initial e.g. 9001 / QMS",
            ),
            sa.Column(
                "ab_code",
                sa.String(30),
                nullable=True,
                comment="인정기관 이니셜 (KAB 등)",
            ),
            sa.Column(
                "cb_id",
                mysql.INTEGER(unsigned=True),
                nullable=True,
                comment="인증기관 certification_bodies.id",
            ),
            sa.Column("cert_no", sa.String(80), nullable=True),
            sa.Column("status", sa.String(30), nullable=True),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_until", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_company_certificates_company_id",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_company_certificates_company_id",
            "company_certificates",
            ["company_id"],
        )
        op.create_index(
            "ix_company_certificates_cb_id",
            "company_certificates",
            ["cb_id"],
        )


def downgrade() -> None:
    # Additive-only policy: intentionally no destructive downgrade.
    pass
