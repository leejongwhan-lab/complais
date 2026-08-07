"""add zip_code to companies and company_sites

Revision ID: h5i6j7k8l9m0
Revises: g4a5b6c7d8e9
Create Date: 2026-08-07

Daum/Kakao postcode zonecode persistence (additive, nullable).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "h5i6j7k8l9m0"
down_revision = "g4a5b6c7d8e9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if _has_table("companies") and not _has_column("companies", "zip_code"):
        op.add_column(
            "companies",
            sa.Column("zip_code", sa.String(length=10), nullable=True, comment="우편번호"),
        )
    if _has_table("company_sites") and not _has_column("company_sites", "zip_code"):
        op.add_column(
            "company_sites",
            sa.Column("zip_code", sa.String(length=10), nullable=True, comment="우편번호"),
        )


def downgrade() -> None:
    if _has_table("company_sites") and _has_column("company_sites", "zip_code"):
        op.drop_column("company_sites", "zip_code")
    if _has_table("companies") and _has_column("companies", "zip_code"):
        op.drop_column("companies", "zip_code")
