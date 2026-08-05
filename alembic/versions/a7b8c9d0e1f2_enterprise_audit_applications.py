"""enterprise_audit_applications — 기업 인증신청 MD 스냅샷

Revision ID: a7b8c9d0e1f2
Revises: z6a7b8c9d0e1
Create Date: 2026-08-05

사용자 DDL(audit_applications)을 구현하되, 기존 심사원 IAF 자격용
`audit_applications` 테이블과 이름 충돌을 피하기 위해
`enterprise_audit_applications` 로 생성한다.

enterprise_id → companies.id (INT UNSIGNED)
cb_id → certification_bodies.id (INT UNSIGNED)
audit_request_id → audit_requests.id (optional)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "z6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if _has_table("enterprise_audit_applications"):
        return

    op.create_table(
        "enterprise_audit_applications",
        sa.Column("application_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("enterprise_id", mysql.INTEGER(unsigned=True), nullable=False, comment="companies.id"),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("audit_request_id", sa.BigInteger(), nullable=True, comment="audit_requests.id optional"),
        sa.Column(
            "audit_type",
            sa.String(30),
            nullable=False,
            server_default="INITIAL",
            comment="INITIAL|SURVEILLANCE_1|SURVEILLANCE_2|RECERT|TRANSFER|SPECIAL",
        ),
        sa.Column("applied_standards", sa.JSON(), nullable=False, comment="신청 표준 목록"),
        sa.Column("ksic_code", sa.String(20), nullable=False),
        sa.Column("iaf_scope_code", sa.String(20), nullable=False),
        sa.Column("active_employee_count", sa.Integer(), nullable=False),
        sa.Column(
            "complexity_level",
            sa.Enum("HIGH", "MEDIUM", "LOW", "LIMITED", name="eaa_complexity_level"),
            nullable=False,
        ),
        sa.Column("base_stage1_md", sa.Numeric(4, 1), nullable=False),
        sa.Column("base_stage2_md", sa.Numeric(4, 1), nullable=False),
        sa.Column("base_surveillance_md", sa.Numeric(4, 1), nullable=False),
        sa.Column("base_recertification_md", sa.Numeric(4, 1), nullable=False),
        sa.Column("base_md_detail_json", sa.JSON(), nullable=True),
        sa.Column("cb_adjustment_ratio", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("cb_adjustment_reason", sa.Text(), nullable=True),
        sa.Column("final_audit_md", sa.Numeric(4, 1), nullable=True),
        sa.Column("is_witness_audit", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "witness_type",
            sa.Enum("NONE", "KAB_WITNESS", "INTERNAL_WITNESS", name="eaa_witness_type"),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("witness_auditor_name", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("SUBMITTED", "REVIEWING", "PROPOSED", "CONTRACTED", name="eaa_status"),
            nullable=False,
            server_default="SUBMITTED",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["enterprise_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"]),
        sa.ForeignKeyConstraint(["audit_request_id"], ["audit_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("application_id"),
    )
    op.create_index("ix_eaa_enterprise_id", "enterprise_audit_applications", ["enterprise_id"])
    op.create_index("ix_eaa_cb_id", "enterprise_audit_applications", ["cb_id"])
    op.create_index("ix_eaa_audit_request_id", "enterprise_audit_applications", ["audit_request_id"])
    op.create_index("ix_eaa_status", "enterprise_audit_applications", ["status"])
    op.create_index("ix_eaa_audit_type", "enterprise_audit_applications", ["audit_type"])


def downgrade() -> None:
    if not _has_table("enterprise_audit_applications"):
        return
    op.drop_index("ix_eaa_audit_type", table_name="enterprise_audit_applications")
    op.drop_index("ix_eaa_status", table_name="enterprise_audit_applications")
    op.drop_index("ix_eaa_audit_request_id", table_name="enterprise_audit_applications")
    op.drop_index("ix_eaa_cb_id", table_name="enterprise_audit_applications")
    op.drop_index("ix_eaa_enterprise_id", table_name="enterprise_audit_applications")
    op.drop_table("enterprise_audit_applications")
