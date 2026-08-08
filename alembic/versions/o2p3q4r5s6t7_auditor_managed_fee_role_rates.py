"""auditor managed companies + assignment fees + CB role rates

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-08-08

ADDITIVE only (no DROP/TRUNCATE of masters):
- auditor_managed_companies
- cb_auditor_role_rates
- audit_assignments fee_* columns
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "o2p3q4r5s6t7"
down_revision = "n1o2p3q4r5s6"
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
    bind = op.get_bind()

    if not _has_table("auditor_managed_companies"):
        op.create_table(
            "auditor_managed_companies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("auditor_id", sa.Integer(), nullable=False, index=True),
            sa.Column("company_id", sa.Integer(), nullable=False, index=True),
            sa.Column("cb_id", sa.Integer(), nullable=False, index=True),
            sa.Column(
                "assigned_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "status",
                sa.String(length=30),
                nullable=False,
                server_default="ACTIVE",
                comment="ACTIVE / TRANSFERRED / INACTIVE",
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "auditor_id",
                "company_id",
                "cb_id",
                name="uq_auditor_managed_company_cb",
            ),
        )

    if not _has_table("cb_auditor_role_rates"):
        op.create_table(
            "cb_auditor_role_rates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("cb_id", sa.Integer(), nullable=False, index=True),
            sa.Column(
                "role",
                sa.String(length=30),
                nullable=False,
                comment="lead / auditor / expert / observer / witness",
            ),
            sa.Column(
                "daily_rate",
                sa.Integer(),
                nullable=False,
                comment="일당 단가(원) — 하드코딩 금지, CB별 설정",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint("cb_id", "role", name="uq_cb_auditor_role_rate"),
        )

    if _has_table("audit_assignments"):
        cols = [
            ("fee_type", sa.Column("fee_type", sa.String(length=30), nullable=True, comment="PERCENTAGE / DAILY_RATE")),
            ("fee_ratio", sa.Column("fee_ratio", sa.Numeric(15, 4), nullable=True, comment="정률 시 적용비율")),
            ("daily_rate", sa.Column("daily_rate", sa.Integer(), nullable=True, comment="일당 단가(원)")),
            ("assigned_days", sa.Column("assigned_days", sa.Numeric(15, 4), nullable=True, comment="배정 일수(MD)")),
            ("calculated_fee", sa.Column("calculated_fee", sa.Numeric(15, 2), nullable=True, comment="산출 수수료(원)")),
        ]
        for name, col in cols:
            if not _has_column("audit_assignments", name):
                op.add_column("audit_assignments", col)


def downgrade() -> None:
    if _has_table("audit_assignments"):
        for name in ("calculated_fee", "assigned_days", "daily_rate", "fee_ratio", "fee_type"):
            if _has_column("audit_assignments", name):
                op.drop_column("audit_assignments", name)
    if _has_table("cb_auditor_role_rates"):
        op.drop_table("cb_auditor_role_rates")
    if _has_table("auditor_managed_companies"):
        op.drop_table("auditor_managed_companies")
