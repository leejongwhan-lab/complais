"""Add high_value_threshold / high_value_deduction_rate to audit_contracts

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-04 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_contracts",
        sa.Column("high_value_threshold", sa.Float(), nullable=True, server_default="0", comment="고액 공제 기준 금액 (0 또는 NULL이면 미적용)"),
    )
    op.add_column(
        "audit_contracts",
        sa.Column("high_value_deduction_rate", sa.Float(), nullable=True, server_default="0", comment="고액 공제 비율 (5.0=5% 또는 0.05)"),
    )


def downgrade() -> None:
    op.drop_column("audit_contracts", "high_value_deduction_rate")
    op.drop_column("audit_contracts", "high_value_threshold")
