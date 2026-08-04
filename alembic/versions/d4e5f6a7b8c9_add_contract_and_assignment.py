"""Add audit_contracts and audit_application_assignments tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-04 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 심사 계약 (audit_applications 정규화 참조) ---
    op.create_table(
        "audit_contracts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_no", sa.String(length=50), nullable=True, comment="계약 번호"),
        sa.Column("audit_type", sa.String(length=50), nullable=False, comment="INITIAL/SURVEILLANCE1/SURVEILLANCE2/RENEWAL 등"),
        sa.Column("standards", sa.Text(), nullable=True, comment="적용 표준 목록 (콤마구분 또는 JSON)"),
        sa.Column("scope_kr", sa.Text(), nullable=True),
        sa.Column("scope_en", sa.Text(), nullable=True),
        sa.Column("audit_period_start", sa.Date(), nullable=True),
        sa.Column("audit_period_end", sa.Date(), nullable=True),
        sa.Column("total_md", sa.Float(), nullable=True, comment="계약 확정 총 MD (AuditMdReview.final_md 스냅샷)"),
        sa.Column("agreed_amount", sa.Numeric(15, 2), nullable=True, comment="계약 확정 금액"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT", comment="DRAFT/SENT/SIGNED/CANCELLED 등"),
        sa.Column("signed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["audit_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_no"),
    )
    op.create_index(op.f("ix_audit_contracts_id"), "audit_contracts", ["id"], unique=False)
    op.create_index(op.f("ix_audit_contracts_application_id"), "audit_contracts", ["application_id"], unique=False)

    # --- 심사 신청건별 심사원 배정 (audit_applications / auditors 정규화 참조) ---
    op.create_table(
        "audit_application_assignments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.BigInteger(), nullable=False),
        # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("contract_id", sa.BigInteger(), nullable=True, comment="배정이 귀속된 계약 (선택)"),
        sa.Column("role", sa.String(length=30), nullable=False, server_default="MEMBER", comment="LEAD/MEMBER/OBSERVER/WITNESS"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ASSIGNED", comment="ASSIGNED/CONFIRMED/DECLINED/COMPLETED"),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["audit_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["audit_contracts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_application_assignments_id"), "audit_application_assignments", ["id"], unique=False)
    op.create_index(op.f("ix_audit_application_assignments_application_id"), "audit_application_assignments", ["application_id"], unique=False)
    op.create_index(op.f("ix_audit_application_assignments_auditor_id"), "audit_application_assignments", ["auditor_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_application_assignments_auditor_id"), table_name="audit_application_assignments")
    op.drop_index(op.f("ix_audit_application_assignments_application_id"), table_name="audit_application_assignments")
    op.drop_index(op.f("ix_audit_application_assignments_id"), table_name="audit_application_assignments")
    op.drop_table("audit_application_assignments")

    op.drop_index(op.f("ix_audit_contracts_application_id"), table_name="audit_contracts")
    op.drop_index(op.f("ix_audit_contracts_id"), table_name="audit_contracts")
    op.drop_table("audit_contracts")
