"""CB portal dashboard additive columns

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-08-07

- contracts.cancelled_at
- auditor_cb_memberships qualification / CPD columns (if missing from skipped n4o5)

Safe additive ALTER only. No DROP/TRUNCATE.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "c0d1e2f3a4b5"
down_revision = "b9c0d1e2f3a4"
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
    if _has_table("contracts") and not _has_column("contracts", "cancelled_at"):
        op.add_column(
            "contracts",
            sa.Column(
                "cancelled_at",
                sa.DateTime(),
                nullable=True,
                comment="인증/계약 취소 시각",
            ),
        )

    if not _has_table("auditor_cb_memberships"):
        return

    if not _has_column("auditor_cb_memberships", "qualification_granted_at"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "qualification_granted_at",
                sa.Date(),
                nullable=True,
                comment="자격 부여일",
            ),
        )
    if not _has_column("auditor_cb_memberships", "qualification_expires_at"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "qualification_expires_at",
                sa.Date(),
                nullable=True,
                comment="자격 갱신/만료일",
            ),
        )
    if not _has_column("auditor_cb_memberships", "knowledge_eval_score"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "knowledge_eval_score",
                sa.Integer(),
                nullable=True,
                comment="지식/규격 평가 점수",
            ),
        )
    if not _has_column("auditor_cb_memberships", "cpd_hours_completed"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "cpd_hours_completed",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="당해년도 CPD 이수 시간",
            ),
        )
    if not _has_column("auditor_cb_memberships", "conflict_of_interest_cleared"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "conflict_of_interest_cleared",
                sa.Boolean(),
                nullable=False,
                server_default="0",
                comment="이해상충 선언 완료 여부",
            ),
        )
    if not _has_column("auditor_cb_memberships", "extra_metadata"):
        op.add_column(
            "auditor_cb_memberships",
            sa.Column(
                "extra_metadata",
                mysql.JSON(),
                nullable=True,
                comment="가변 JSON 메타데이터",
            ),
        )


def downgrade() -> None:
    if _has_table("contracts") and _has_column("contracts", "cancelled_at"):
        op.drop_column("contracts", "cancelled_at")
    # Membership columns may have been intended by n4o5 — do not drop on downgrade
    # to avoid destroying data if n4o5 is later applied independently.
