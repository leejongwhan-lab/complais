"""add_user_membership_status

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-08-05

users 테이블에 소속 승인/세부 권한 컬럼 추가:
membership_status, approved_by, approved_at
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {c["name"] for c in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("users", "membership_status"):
        op.add_column(
            "users",
            sa.Column(
                "membership_status",
                sa.String(length=20),
                nullable=False,
                server_default="approved",
                comment="approved, pending, rejected",
            ),
        )
    if not _has_column("users", "approved_by"):
        op.add_column(
            "users",
            sa.Column(
                "approved_by",
                sa.Integer(),
                nullable=True,
                comment="승인해 준 대표계정 user_id",
            ),
        )
    if not _has_column("users", "approved_at"):
        op.add_column(
            "users",
            sa.Column("approved_at", sa.DateTime(), nullable=True),
        )

    # 기존 계정은 승인 완료로 간주
    op.execute("UPDATE users SET membership_status = 'approved' WHERE membership_status IS NULL OR membership_status = ''")


def downgrade() -> None:
    if _has_column("users", "approved_at"):
        op.drop_column("users", "approved_at")
    if _has_column("users", "approved_by"):
        op.drop_column("users", "approved_by")
    if _has_column("users", "membership_status"):
        op.drop_column("users", "membership_status")
