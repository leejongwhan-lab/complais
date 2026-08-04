"""Add updated_at to standard_masters/standard_clause_masters and add standard_process_masters / process_clause_mappings

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-08-04 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 기존 표준/조항 마스터에 updated_at 추가 ---
    op.add_column("standard_masters", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.add_column("standard_clause_masters", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # --- 표준 프로세스 마스터 (레거시 standard_processes(JSON clause_ids)와 별개 정규화 테이블) ---
    op.create_table(
        "standard_process_masters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("process_code", sa.String(length=30), nullable=False, comment="예: PRC_MGMT, PRC_RISK"),
        sa.Column("process_name_kr", sa.String(length=100), nullable=False, comment="예: 경영 및 전략 프로세스"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_code"),
    )
    op.create_index(op.f("ix_standard_process_masters_id"), "standard_process_masters", ["id"], unique=False)
    op.create_index(op.f("ix_standard_process_masters_process_code"), "standard_process_masters", ["process_code"], unique=True)

    # --- 프로세스 - 조항 N:M 매핑 ---
    op.create_table(
        "process_clause_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("clause_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["process_id"], ["standard_process_masters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["clause_id"], ["standard_clause_masters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("process_id", "clause_id", name="uix_process_clause_mapping"),
    )
    op.create_index(op.f("ix_process_clause_mappings_id"), "process_clause_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_process_clause_mappings_process_id"), "process_clause_mappings", ["process_id"], unique=False)
    op.create_index(op.f("ix_process_clause_mappings_clause_id"), "process_clause_mappings", ["clause_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_process_clause_mappings_clause_id"), table_name="process_clause_mappings")
    op.drop_index(op.f("ix_process_clause_mappings_process_id"), table_name="process_clause_mappings")
    op.drop_index(op.f("ix_process_clause_mappings_id"), table_name="process_clause_mappings")
    op.drop_table("process_clause_mappings")

    op.drop_index(op.f("ix_standard_process_masters_process_code"), table_name="standard_process_masters")
    op.drop_index(op.f("ix_standard_process_masters_id"), table_name="standard_process_masters")
    op.drop_table("standard_process_masters")

    op.drop_column("standard_clause_masters", "updated_at")
    op.drop_column("standard_masters", "updated_at")
