"""Add standard_masters and standard_clause_masters tables

Revision ID: g7h8i9j0k1l2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-04 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 표준 마스터 (예: ISO 9001:2015, ISO 9001:2026 등) ---
    op.create_table(
        "standard_masters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_code", sa.String(length=50), nullable=False, comment="예: ISO 9001:2015"),
        sa.Column("standard_name", sa.String(length=100), nullable=False, comment="예: 품질경영시스템"),
        sa.Column("version_year", sa.Integer(), nullable=False, comment="예: 2015, 2026"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), comment="사용 여부"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standard_code"),
    )
    op.create_index(op.f("ix_standard_masters_id"), "standard_masters", ["id"], unique=False)
    op.create_index(op.f("ix_standard_masters_standard_code"), "standard_masters", ["standard_code"], unique=True)

    # --- 표준별 세부 조항 (레거시 checklist형 standard_clauses(master.py)와는 별개의 정규화 참조 테이블) ---
    op.create_table(
        "standard_clause_masters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=False),
        sa.Column("clause_number", sa.String(length=30), nullable=False, comment="예: 4.1, 6.1.2, 8.5.1"),
        sa.Column("clause_title_kr", sa.String(length=255), nullable=False, comment="한글 조항 제목"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="1", comment="뎁스 (4 -> 1, 4.1 -> 2, 4.4.1 -> 3)"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="정렬 순서"),
        sa.Column("requirements_summary", sa.Text(), nullable=True, comment="AI 조항 요구사항 요약"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["standard_id"], ["standard_masters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standard_id", "clause_number", name="uix_standard_clause_number"),
    )
    op.create_index(op.f("ix_standard_clause_masters_id"), "standard_clause_masters", ["id"], unique=False)
    op.create_index(op.f("ix_standard_clause_masters_standard_id"), "standard_clause_masters", ["standard_id"], unique=False)
    op.create_index(op.f("ix_standard_clause_masters_clause_number"), "standard_clause_masters", ["clause_number"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_standard_clause_masters_clause_number"), table_name="standard_clause_masters")
    op.drop_index(op.f("ix_standard_clause_masters_standard_id"), table_name="standard_clause_masters")
    op.drop_index(op.f("ix_standard_clause_masters_id"), table_name="standard_clause_masters")
    op.drop_table("standard_clause_masters")

    op.drop_index(op.f("ix_standard_masters_standard_code"), table_name="standard_masters")
    op.drop_index(op.f("ix_standard_masters_id"), table_name="standard_masters")
    op.drop_table("standard_masters")
