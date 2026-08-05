"""enterprise company org tables + staff/site extensions

Revision ID: y5z6a7b8c9d0
Revises: x4y5z6a7b8c9
Create Date: 2026-08-05

기업 포털 기업정보 화면용:
- company_departments (부서 관리)
- company_staff_members.role / phone (담당자 권한·전화)
- company_sites.address_en / detail_address (추가사업장)
- audit_requests.preferred_start_date / process_step (인증현황 스테퍼)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "y5z6a7b8c9d0"
down_revision = "x4y5z6a7b8c9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_table("company_departments"):
        op.create_table(
            "company_departments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False, comment="부서명"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("company_id", "name", name="uq_company_departments_company_name"),
        )
        op.create_index("ix_company_departments_company_id", "company_departments", ["company_id"], unique=False)

    if _has_table("company_staff_members"):
        if not _has_column("company_staff_members", "role"):
            op.add_column(
                "company_staff_members",
                sa.Column("role", sa.String(length=50), nullable=True, comment="권한(인증담당/품질담당 등)"),
            )
        if not _has_column("company_staff_members", "phone"):
            op.add_column(
                "company_staff_members",
                sa.Column("phone", sa.String(length=30), nullable=True, comment="유선전화"),
            )
        if not _has_column("company_staff_members", "updated_at"):
            op.add_column("company_staff_members", sa.Column("updated_at", sa.DateTime(), nullable=True))

    if _has_table("company_sites"):
        if not _has_column("company_sites", "address_en"):
            op.add_column("company_sites", sa.Column("address_en", sa.String(length=500), nullable=True))
        if not _has_column("company_sites", "detail_address"):
            op.add_column("company_sites", sa.Column("detail_address", sa.String(length=500), nullable=True))

    if _has_table("audit_requests"):
        if not _has_column("audit_requests", "preferred_start_date"):
            op.add_column(
                "audit_requests",
                sa.Column("preferred_start_date", sa.Date(), nullable=True, comment="희망 심사 시작일"),
            )
        if not _has_column("audit_requests", "process_step"):
            op.add_column(
                "audit_requests",
                sa.Column(
                    "process_step",
                    sa.SmallInteger(),
                    nullable=False,
                    server_default="1",
                    comment="1제안서~7종료",
                ),
            )
        if not _has_column("audit_requests", "application_no"):
            op.add_column(
                "audit_requests",
                sa.Column("application_no", sa.String(length=50), nullable=True, comment="신청번호"),
            )


def downgrade() -> None:
    if _has_table("audit_requests"):
        for col in ("application_no", "process_step", "preferred_start_date"):
            if _has_column("audit_requests", col):
                op.drop_column("audit_requests", col)

    if _has_table("company_sites"):
        for col in ("detail_address", "address_en"):
            if _has_column("company_sites", col):
                op.drop_column("company_sites", col)

    if _has_table("company_staff_members"):
        for col in ("updated_at", "phone", "role"):
            if _has_column("company_staff_members", col):
                op.drop_column("company_staff_members", col)

    if _has_table("company_departments"):
        op.drop_index("ix_company_departments_company_id", table_name="company_departments")
        op.drop_table("company_departments")
