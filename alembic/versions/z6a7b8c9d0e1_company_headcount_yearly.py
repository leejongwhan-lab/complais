"""company_headcount_yearly — 인원현황 연도별 스냅샷

Revision ID: z6a7b8c9d0e1
Revises: y5z6a7b8c9d0
Create Date: 2026-08-05

매년 심사 때 바뀌는 인원현황을 연도별로 보관한다.
companies.* headcount 컬럼은 최신(현재) 값 캐시로 유지한다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "z6a7b8c9d0e1"
down_revision = "y5z6a7b8c9d0"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _has_table("company_headcount_yearly"):
        return
    op.create_table(
        "company_headcount_yearly",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False, comment="심사/기준 연도"),
        sa.Column("employee_count", sa.Integer(), nullable=True, comment="본사 인원수"),
        sa.Column("headcount_regular", sa.Integer(), nullable=True),
        sa.Column("headcount_non_regular", sa.Integer(), nullable=True),
        sa.Column("headcount_outsourced", sa.Integer(), nullable=True),
        sa.Column("headcount_certified", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "year", name="uq_company_headcount_yearly_company_year"),
    )
    op.create_index(
        "ix_company_headcount_yearly_company_id",
        "company_headcount_yearly",
        ["company_id"],
        unique=False,
    )


def downgrade() -> None:
    if not _has_table("company_headcount_yearly"):
        return
    op.drop_index("ix_company_headcount_yearly_company_id", table_name="company_headcount_yearly")
    op.drop_table("company_headcount_yearly")
