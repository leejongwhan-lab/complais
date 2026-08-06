"""add_admin_cb_contract_and_accreditation

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4o5
Create Date: 2026-08-05

CB 연간 계약/과금 정책(cb_contracts), 플랫폼 동적 계산식 마스터(platform_calculation_rules),
CB 인정서 워크플로우(cb_accreditation_records) 및 승인 범위(cb_accreditation_record_scopes)를 추가한다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "k1l2m3n4o5p6"
down_revision = "j0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cb_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("contract_year", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=True),
        sa.Column("annual_base_fee", sa.Numeric(precision=12, scale=0), nullable=False),
        sa.Column("price_per_md", sa.Numeric(precision=10, scale=0), nullable=False),
        sa.Column("contract_start_date", sa.DateTime(), nullable=False),
        sa.Column("contract_end_date", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cb_contracts_id"), "cb_contracts", ["id"], unique=False)
    op.create_index(op.f("ix_cb_contracts_cb_id"), "cb_contracts", ["cb_id"], unique=False)

    op.create_table(
        "platform_calculation_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("rule_code", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("formula_expression", sa.Text(), nullable=True),
        sa.Column("variables_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_platform_calculation_rules_id"), "platform_calculation_rules", ["id"], unique=False)
    op.create_index(
        op.f("ix_platform_calculation_rules_rule_code"),
        "platform_calculation_rules",
        ["rule_code"],
        unique=True,
    )

    op.create_table(
        "cb_accreditation_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("accreditation_body", sa.String(length=100), nullable=False),
        sa.Column("certificate_number", sa.String(length=100), nullable=False),
        sa.Column("certificate_file_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cb_accreditation_records_id"), "cb_accreditation_records", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_cb_accreditation_records_cb_id"), "cb_accreditation_records", ["cb_id"], unique=False
    )

    op.create_table(
        "cb_accreditation_record_scopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cb_accreditation_id", sa.Integer(), nullable=False),
        sa.Column("iso_standard_id", sa.Integer(), nullable=False),
        sa.Column("iaf_code", sa.String(length=50), nullable=False),
        sa.Column("is_approved", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["cb_accreditation_id"], ["cb_accreditation_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iso_standard_id"], ["standard_masters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cb_accreditation_record_scopes_id"),
        "cb_accreditation_record_scopes",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cb_accreditation_record_scopes_cb_accreditation_id"),
        "cb_accreditation_record_scopes",
        ["cb_accreditation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cb_accreditation_record_scopes_iso_standard_id"),
        "cb_accreditation_record_scopes",
        ["iso_standard_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("cb_accreditation_record_scopes")
    op.drop_table("cb_accreditation_records")
    op.drop_table("platform_calculation_rules")
    op.drop_table("cb_contracts")
