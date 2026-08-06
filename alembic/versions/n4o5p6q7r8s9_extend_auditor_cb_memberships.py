"""extend_auditor_cb_memberships

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-08-05

CB별 심사원 전속 자격/평가 관리 컬럼 확장.
기존 auditor_cb_memberships 테이블에 신규 컬럼만 추가한다 (테이블 재생성 없음).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # status: suspended / expired 추가
    op.execute(
        """
        ALTER TABLE auditor_cb_memberships
        MODIFY status ENUM(
            'requested','under_review','approved','rejected','terminated','suspended','expired'
        ) NOT NULL DEFAULT 'requested'
        """
    )

    op.add_column(
        "auditor_cb_memberships",
        sa.Column("qualification_granted_at", sa.Date(), nullable=True, comment="자격 부여일"),
    )
    op.add_column(
        "auditor_cb_memberships",
        sa.Column("qualification_expires_at", sa.Date(), nullable=True, comment="자격 갱신/만료일"),
    )
    op.add_column(
        "auditor_cb_memberships",
        sa.Column("knowledge_eval_score", sa.Integer(), nullable=True, comment="지식/규격 평가 점수"),
    )
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
    op.drop_column("auditor_cb_memberships", "extra_metadata")
    op.drop_column("auditor_cb_memberships", "conflict_of_interest_cleared")
    op.drop_column("auditor_cb_memberships", "cpd_hours_completed")
    op.drop_column("auditor_cb_memberships", "knowledge_eval_score")
    op.drop_column("auditor_cb_memberships", "qualification_expires_at")
    op.drop_column("auditor_cb_memberships", "qualification_granted_at")
    op.execute(
        """
        ALTER TABLE auditor_cb_memberships
        MODIFY status ENUM(
            'requested','under_review','approved','rejected','terminated'
        ) NOT NULL DEFAULT 'requested'
        """
    )
