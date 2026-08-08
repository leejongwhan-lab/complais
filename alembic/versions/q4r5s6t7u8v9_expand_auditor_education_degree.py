"""expand auditor_educations.degree enum + sync

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-08-08

ADDITIVE: high_school / associate for 고졸·전문학사.
"""
from alembic import op
from sqlalchemy import inspect, text

revision = "q4r5s6t7u8v9"
down_revision = "p3q4r5s6t7u8"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("auditor_educations"):
        return
    op.execute(
        text(
            """
            ALTER TABLE auditor_educations
            MODIFY COLUMN degree ENUM(
              'high_school','associate','bachelor','master','doctor','other'
            ) NOT NULL DEFAULT 'bachelor'
            """
        )
    )


def downgrade() -> None:
    if not _has_table("auditor_educations"):
        return
    # Map new values back before shrinking enum
    op.execute(
        text(
            """
            UPDATE auditor_educations
            SET degree='other'
            WHERE degree IN ('high_school','associate')
            """
        )
    )
    op.execute(
        text(
            """
            ALTER TABLE auditor_educations
            MODIFY COLUMN degree ENUM(
              'bachelor','master','doctor','other'
            ) NOT NULL DEFAULT 'bachelor'
            """
        )
    )
