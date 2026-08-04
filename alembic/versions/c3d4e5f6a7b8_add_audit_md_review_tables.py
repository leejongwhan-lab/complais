"""Add audit MD review and review log tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-04 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 심사 신청건별 MD 산출 및 행정 가감 검토 ---
    op.create_table(
        "audit_md_reviews",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.BigInteger(), nullable=False),
        sa.Column("base_md", sa.Float(), nullable=False, server_default="0", comment="계산기 기준 자동 산정 기본 MD"),
        sa.Column("base_md_detail_json", sa.JSON(), nullable=True, comment="계산기 엔진 로그 스냅샷 (_lastCalcLog)"),
        sa.Column("base_md_calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("base_md_calculated_by", sa.BigInteger(), nullable=True, comment="계산 수행 유저 ID"),
        sa.Column("add_pct", sa.Integer(), nullable=False, server_default="0", comment="가산 비율 (%)"),
        sa.Column("subtract_pct", sa.Integer(), nullable=False, server_default="0", comment="감산 비율 (%)"),
        sa.Column("add_md", sa.Float(), nullable=False, server_default="0", comment="가산 MD"),
        sa.Column("subtract_md", sa.Float(), nullable=False, server_default="0", comment="감산 MD"),
        sa.Column("final_md", sa.Float(), nullable=False, server_default="0", comment="최종 확정 MD"),
        sa.Column("calculation_note", sa.Text(), nullable=True, comment="가감 사유 및 인용 조항 메모"),
        sa.Column("reviewer_user_id", sa.BigInteger(), nullable=True, comment="최종 검토/승인자 ID"),
        sa.Column("reviewer_role", sa.String(length=50), nullable=True, comment="검토자 역할"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["audit_applications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_md_reviews_id"), "audit_md_reviews", ["id"], unique=False)
    op.create_index(op.f("ix_audit_md_reviews_application_id"), "audit_md_reviews", ["application_id"], unique=True)

    # --- MD 검토 상태 변경 및 저장 히스토리 로그 ---
    op.create_table(
        "audit_md_review_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("md_review_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_role", sa.String(length=50), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False, comment="save_md, under_review, approved 등"),
        sa.Column("before_status", sa.String(length=50), nullable=True),
        sa.Column("after_status", sa.String(length=50), nullable=True),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["md_review_id"], ["audit_md_reviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_md_review_logs_id"), "audit_md_review_logs", ["id"], unique=False)
    op.create_index(op.f("ix_audit_md_review_logs_md_review_id"), "audit_md_review_logs", ["md_review_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_md_review_logs_md_review_id"), table_name="audit_md_review_logs")
    op.drop_index(op.f("ix_audit_md_review_logs_id"), table_name="audit_md_review_logs")
    op.drop_table("audit_md_review_logs")

    op.drop_index(op.f("ix_audit_md_reviews_application_id"), table_name="audit_md_reviews")
    op.drop_index(op.f("ix_audit_md_reviews_id"), table_name="audit_md_reviews")
    op.drop_table("audit_md_reviews")
