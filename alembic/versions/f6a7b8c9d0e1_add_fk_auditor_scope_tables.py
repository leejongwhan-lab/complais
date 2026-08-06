"""Add FK constraints to auditor_scope_grants / auditor_scope_requests

기존에는 auditor_scope_grants / auditor_scope_requests 테이블의 auditor_id, cb_id가
단순 정수 컬럼(인덱스만 존재)이었고 실제 FK 제약이 없었다. 이 마이그레이션은
auditor_id -> auditors.id, cb_id -> certification_bodies.id 로 정식 FK 제약을 추가해
정규화한다 (배정 사전 검증(_validate_auditor_qualification) 등에서 무결성 보장 필요).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-04 17:57:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_auditor_scope_grants_auditor_id",
        "auditor_scope_grants",
        "auditors",
        ["auditor_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_auditor_scope_grants_cb_id",
        "auditor_scope_grants",
        "certification_bodies",
        ["cb_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_auditor_scope_requests_auditor_id",
        "auditor_scope_requests",
        "auditors",
        ["auditor_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_auditor_scope_requests_cb_id",
        "auditor_scope_requests",
        "certification_bodies",
        ["cb_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_auditor_scope_requests_cb_id", "auditor_scope_requests", type_="foreignkey")
    op.drop_constraint("fk_auditor_scope_requests_auditor_id", "auditor_scope_requests", type_="foreignkey")
    op.drop_constraint("fk_auditor_scope_grants_cb_id", "auditor_scope_grants", type_="foreignkey")
    op.drop_constraint("fk_auditor_scope_grants_auditor_id", "auditor_scope_grants", type_="foreignkey")
