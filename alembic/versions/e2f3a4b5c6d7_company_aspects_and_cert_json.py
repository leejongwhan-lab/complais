"""company_aspects + cert app ksic_codes_json/snapshot_json

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-07

Additive only — no DROP/TRUNCATE. Preserves companies/CBs (1134/70).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "e2f3a4b5c6d7"
down_revision = "d1e2f3a4b5c6"
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
        if not _has_column("certification_applications", "ksic_codes_json"):
            op.add_column(
                "certification_applications",
                sa.Column(
                    "ksic_codes_json",
                    sa.Text(),
                    nullable=True,
                    comment="JSON array of KSIC codes; ksic_code keeps primary",
                ),
            )
        if not _has_column("certification_applications", "snapshot_json"):
            op.add_column(
                "certification_applications",
                sa.Column(
                    "snapshot_json",
                    sa.Text(),
                    nullable=True,
                    comment="Application-time snapshot (aspects + meta)",
                ),
            )

    if not _has_table("company_aspects"):
        # companies.id is INT UNSIGNED — match precisely for FK compatibility
        op.create_table(
            "company_aspects",
            sa.Column("id", mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
            sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("ems_json", sa.JSON(), nullable=True, comment="ISO 14001 EMS"),
            sa.Column("ohs_json", sa.JSON(), nullable=True, comment="ISO 45001 OHS"),
            sa.Column("enms_json", sa.JSON(), nullable=True, comment="ISO 50001 EnMS"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", name="uq_company_aspects_company_id"),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_company_aspects_company_id",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_company_aspects_company_id",
            "company_aspects",
            ["company_id"],
            unique=True,
        )


def downgrade() -> None:
    # Additive-only policy: intentionally no destructive downgrade.
    pass
