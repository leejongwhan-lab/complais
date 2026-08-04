"""Add audit_note_records and audit_ncr_records tables

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-08-04 18:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ncr_grade_enum = sa.Enum("major", "minor", "obs", name="ncrgrade")


def upgrade() -> None:
    # --- 심사노트: 계약(Contract) + 표준조항(Clause) 단위 현장 관찰 기록 ---
    op.create_table(
        "audit_note_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.BigInteger(), nullable=False),
        sa.Column("clause_id", sa.Integer(), nullable=False),
        # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("audit_findings", sa.Text(), nullable=False, comment="심사 발견사항 및 확인 기록"),
        sa.Column("compliance_status", sa.String(length=20), nullable=False, server_default="conform", comment="conform/nc/obs"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["audit_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clause_id"], ["standard_clause_masters.id"]),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_note_records_id"), "audit_note_records", ["id"], unique=False)
    op.create_index(op.f("ix_audit_note_records_contract_id"), "audit_note_records", ["contract_id"], unique=False)
    op.create_index(op.f("ix_audit_note_records_clause_id"), "audit_note_records", ["clause_id"], unique=False)

    # --- 부적합 관리: 부적합 조항 매핑 및 시정조치(CA) 추적 ---
    op.create_table(
        "audit_ncr_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("contract_id", sa.BigInteger(), nullable=False),
        sa.Column("clause_id", sa.Integer(), nullable=False),
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("grade", ncr_grade_enum, nullable=False, comment="major/minor/obs"),
        sa.Column("nc_description", sa.Text(), nullable=False, comment="부적합 내용 (요구사항 대비 미흡 사항)"),
        sa.Column("corrective_action", sa.Text(), nullable=True, comment="피심사 기업이 제출한 시정조치 내용"),
        sa.Column("root_cause", sa.Text(), nullable=True, comment="근본 원인 분석"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="issued", comment="issued/ca_submitted/ca_accepted/closed"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["audit_contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clause_id"], ["standard_clause_masters.id"]),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_ncr_records_id"), "audit_ncr_records", ["id"], unique=False)
    op.create_index(op.f("ix_audit_ncr_records_contract_id"), "audit_ncr_records", ["contract_id"], unique=False)
    op.create_index(op.f("ix_audit_ncr_records_clause_id"), "audit_ncr_records", ["clause_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_ncr_records_clause_id"), table_name="audit_ncr_records")
    op.drop_index(op.f("ix_audit_ncr_records_contract_id"), table_name="audit_ncr_records")
    op.drop_index(op.f("ix_audit_ncr_records_id"), table_name="audit_ncr_records")
    op.drop_table("audit_ncr_records")

    op.drop_index(op.f("ix_audit_note_records_clause_id"), table_name="audit_note_records")
    op.drop_index(op.f("ix_audit_note_records_contract_id"), table_name="audit_note_records")
    op.drop_index(op.f("ix_audit_note_records_id"), table_name="audit_note_records")
    op.drop_table("audit_note_records")

    ncr_grade_enum.drop(op.get_bind(), checkfirst=True)
