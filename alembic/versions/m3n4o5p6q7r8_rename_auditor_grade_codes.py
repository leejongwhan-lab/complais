"""rename_auditor_grade_codes

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-08-05

심사원 등급 코드 표준화:
- senior / 선임심사원 → lead_auditor
- verifier / 검증원 / 검증심사원 → verified_auditor
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "m3n4o5p6q7r8"
down_revision = "l2m3n4o5p6q7"
branch_labels = None
depends_on = None

NEW_AUDITOR_GRADE = (
    "ENUM('trainee','auditor','senior','verifier','lead_auditor','verified_auditor')"
)
FINAL_AUDITOR_GRADE = "ENUM('trainee','auditor','lead_auditor','verified_auditor')"


def upgrade() -> None:
    # 1) ENUM에 신규 코드 추가 (기존 값 유지)
    op.execute(
        f"ALTER TABLE auditors MODIFY grade {NEW_AUDITOR_GRADE} NOT NULL DEFAULT 'trainee'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY apply_grade {NEW_AUDITOR_GRADE} NULL DEFAULT 'auditor'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY approved_grade {NEW_AUDITOR_GRADE} NULL"
    )

    # 2) 데이터 일괄 변경
    op.execute(
        """
        UPDATE auditors
        SET grade = 'lead_auditor'
        WHERE grade IN ('senior', '선임심사원')
        """
    )
    op.execute(
        """
        UPDATE auditors
        SET grade = 'verified_auditor'
        WHERE grade IN ('verifier', '검증원', '검증심사원')
        """
    )

    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET apply_grade = 'lead_auditor'
        WHERE apply_grade IN ('senior', '선임심사원')
        """
    )
    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET apply_grade = 'verified_auditor'
        WHERE apply_grade IN ('verifier', '검증원', '검증심사원')
        """
    )
    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET approved_grade = 'lead_auditor'
        WHERE approved_grade IN ('senior', '선임심사원')
        """
    )
    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET approved_grade = 'verified_auditor'
        WHERE approved_grade IN ('verifier', '검증원', '검증심사원')
        """
    )
    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET grade_at_cb = 'lead_auditor'
        WHERE grade_at_cb IN ('senior', '선임심사원')
        """
    )
    op.execute(
        """
        UPDATE auditor_cb_memberships
        SET grade_at_cb = 'verified_auditor'
        WHERE grade_at_cb IN ('verifier', '검증원', '검증심사원')
        """
    )

    # 3) 구 코드 제거한 최종 ENUM
    op.execute(
        f"ALTER TABLE auditors MODIFY grade {FINAL_AUDITOR_GRADE} NOT NULL DEFAULT 'trainee'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY apply_grade {FINAL_AUDITOR_GRADE} NULL DEFAULT 'auditor'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY approved_grade {FINAL_AUDITOR_GRADE} NULL"
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE auditors MODIFY grade {NEW_AUDITOR_GRADE} NOT NULL DEFAULT 'trainee'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY apply_grade {NEW_AUDITOR_GRADE} NULL DEFAULT 'auditor'"
    )
    op.execute(
        f"ALTER TABLE auditor_cb_memberships "
        f"MODIFY approved_grade {NEW_AUDITOR_GRADE} NULL"
    )

    op.execute("UPDATE auditors SET grade = 'senior' WHERE grade = 'lead_auditor'")
    op.execute("UPDATE auditors SET grade = 'verifier' WHERE grade = 'verified_auditor'")
    op.execute(
        "UPDATE auditor_cb_memberships SET apply_grade = 'senior' WHERE apply_grade = 'lead_auditor'"
    )
    op.execute(
        "UPDATE auditor_cb_memberships SET apply_grade = 'verifier' WHERE apply_grade = 'verified_auditor'"
    )
    op.execute(
        "UPDATE auditor_cb_memberships SET approved_grade = 'senior' WHERE approved_grade = 'lead_auditor'"
    )
    op.execute(
        "UPDATE auditor_cb_memberships SET approved_grade = 'verifier' WHERE approved_grade = 'verified_auditor'"
    )
    op.execute(
        "UPDATE auditor_cb_memberships SET grade_at_cb = 'senior' WHERE grade_at_cb = 'lead_auditor'"
    )
    op.execute(
        "UPDATE auditor_cb_memberships SET grade_at_cb = 'verifier' WHERE grade_at_cb = 'verified_auditor'"
    )

    old = "ENUM('trainee','auditor','senior','verifier')"
    op.execute(f"ALTER TABLE auditors MODIFY grade {old} NOT NULL DEFAULT 'trainee'")
    op.execute(
        f"ALTER TABLE auditor_cb_memberships MODIFY apply_grade {old} NULL DEFAULT 'auditor'"
    )
    op.execute(f"ALTER TABLE auditor_cb_memberships MODIFY approved_grade {old} NULL")
