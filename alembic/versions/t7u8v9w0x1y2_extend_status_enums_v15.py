"""Extend status ENUMs for v14/v15 gates

Revision ID: t7u8v9w0x1y2
Revises: s6t7u8v9w0x1
Create Date: 2026-08-08

ADDITIVE ENUM values only — no DROP/TRUNCATE.
- audit_note_ncr.status += waiting_team_review (NCR team-review gate)
- certification_applications.status += company_revision_requested
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect, text

revision = "t7u8v9w0x1y2"
down_revision = "s6t7u8v9w0x1"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _enum_has_value(table: str, column: str, value: str) -> bool:
    bind = op.get_bind()
    row = bind.execute(
        text(
            "SELECT COLUMN_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).first()
    if not row:
        return False
    col_type = (row[0] or "").lower()
    return f"'{value.lower()}'" in col_type


def upgrade() -> None:
    # 1) NCR team-review gate status
    if _has_table("audit_note_ncr") and not _enum_has_value(
        "audit_note_ncr", "status", "waiting_team_review"
    ):
        op.execute(
            """
            ALTER TABLE audit_note_ncr
            MODIFY status ENUM(
                'open','client_response','cb_review',
                'waiting_team_review','closed','overdue'
            ) NOT NULL DEFAULT 'open'
            """
        )

    # 2) Enterprise company-revision status
    if _has_table("certification_applications") and not _enum_has_value(
        "certification_applications", "status", "company_revision_requested"
    ):
        op.execute(
            """
            ALTER TABLE certification_applications
            MODIFY status ENUM(
                'draft','submitted','under_review','need_fix',
                'approved','company_revision_requested','rejected',
                'contracted','withdrawn'
            ) NOT NULL DEFAULT 'draft'
            """
        )


def downgrade() -> None:
    # Safe shrink only when no rows use the new values.
    bind = op.get_bind()
    if _has_table("audit_note_ncr") and _enum_has_value(
        "audit_note_ncr", "status", "waiting_team_review"
    ):
        n = bind.execute(
            text(
                "SELECT COUNT(*) FROM audit_note_ncr "
                "WHERE status = 'waiting_team_review'"
            )
        ).scalar()
        if not n:
            op.execute(
                """
                ALTER TABLE audit_note_ncr
                MODIFY status ENUM(
                    'open','client_response','cb_review','closed','overdue'
                ) NOT NULL DEFAULT 'open'
                """
            )

    if _has_table("certification_applications") and _enum_has_value(
        "certification_applications", "status", "company_revision_requested"
    ):
        n = bind.execute(
            text(
                "SELECT COUNT(*) FROM certification_applications "
                "WHERE status = 'company_revision_requested'"
            )
        ).scalar()
        if not n:
            op.execute(
                """
                ALTER TABLE certification_applications
                MODIFY status ENUM(
                    'draft','submitted','under_review','need_fix',
                    'approved','rejected','contracted','withdrawn'
                ) NOT NULL DEFAULT 'draft'
                """
            )
