"""company_certificates audit status fields + certificate PDF URL

Revision ID: c1d2e3f4a5b6
Revises: l9m0n1o2p3q4
Create Date: 2026-08-07

Enterprise 인증현황: 최근심사일 / 최근심사유형 / 이번심사유형 / PDF URL.
Additive ALTER only. No DROP/TRUNCATE of master tables.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "c1d2e3f4a5b6"
down_revision = "l9m0n1o2p3q4"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def _add_col(table: str, column: str, col: sa.Column) -> None:
    if _has_table(table) and not _has_column(table, column):
        op.add_column(table, col)


def upgrade() -> None:
    _add_col(
        "company_certificates",
        "last_audit_date",
        sa.Column("last_audit_date", sa.Date(), nullable=True, comment="최근심사일"),
    )
    _add_col(
        "company_certificates",
        "last_audit_type",
        sa.Column(
            "last_audit_type",
            sa.String(50),
            nullable=True,
            comment="최근심사유형 (initial/surveillance1/…)",
        ),
    )
    _add_col(
        "company_certificates",
        "current_audit_type",
        sa.Column(
            "current_audit_type",
            sa.String(50),
            nullable=True,
            comment="이번(예정) 심사유형",
        ),
    )
    _add_col(
        "company_certificates",
        "certificate_file_url",
        sa.Column(
            "certificate_file_url",
            sa.String(500),
            nullable=True,
            comment="인증서 PDF/파일 URL",
        ),
    )
    _add_col(
        "certificates",
        "certificate_file_url",
        sa.Column(
            "certificate_file_url",
            sa.String(500),
            nullable=True,
            comment="인증서 PDF/파일 URL",
        ),
    )

    bind = op.get_bind()

    # Backfill from company_audit_history_records (company-level → all held certs)
    if _has_table("company_audit_history_records") and _has_table("company_certificates"):
        bind.execute(
            text(
                """
                UPDATE company_certificates cc
                JOIN (
                  SELECT company_id,
                    CASE
                      WHEN renewal_date IS NOT NULL THEN renewal_date
                      WHEN surveillance_2_date IS NOT NULL THEN surveillance_2_date
                      WHEN surveillance_1_date IS NOT NULL THEN surveillance_1_date
                      WHEN initial_cert_date IS NOT NULL THEN initial_cert_date
                      ELSE NULL
                    END AS lad,
                    CASE
                      WHEN renewal_date IS NOT NULL THEN 'recertification'
                      WHEN surveillance_2_date IS NOT NULL THEN 'surveillance2'
                      WHEN surveillance_1_date IS NOT NULL THEN 'surveillance1'
                      WHEN initial_cert_date IS NOT NULL THEN 'initial'
                      ELSE NULL
                    END AS lat
                  FROM company_audit_history_records
                ) h ON h.company_id = cc.company_id
                SET
                  cc.last_audit_date = COALESCE(cc.last_audit_date, h.lad),
                  cc.last_audit_type = COALESCE(cc.last_audit_type, h.lat),
                  cc.current_audit_type = COALESCE(
                    cc.current_audit_type,
                    CASE h.lat
                      WHEN 'initial' THEN 'surveillance1'
                      WHEN 'surveillance1' THEN 'surveillance2'
                      WHEN 'surveillance2' THEN 'recertification'
                      WHEN 'recertification' THEN 'surveillance1'
                      ELSE NULL
                    END
                  )
                WHERE h.lad IS NOT NULL
                """
            )
        )

    # Fallback: use valid_from as initial audit when still empty
    if _has_table("company_certificates"):
        bind.execute(
            text(
                """
                UPDATE company_certificates
                SET
                  last_audit_date = COALESCE(last_audit_date, valid_from),
                  last_audit_type = COALESCE(last_audit_type, 'initial'),
                  current_audit_type = COALESCE(
                    current_audit_type,
                    CASE
                      WHEN valid_until IS NOT NULL
                        AND DATEDIFF(valid_until, CURDATE()) <= 180
                      THEN 'recertification'
                      ELSE 'surveillance1'
                    END
                  )
                WHERE last_audit_date IS NULL AND valid_from IS NOT NULL
                """
            )
        )

    # Upcoming/current type from open contracts (prefer non-closed)
    if _has_table("contracts") and _has_table("company_certificates"):
        bind.execute(
            text(
                """
                UPDATE company_certificates cc
                JOIN contracts c ON c.company_id = cc.company_id
                SET cc.current_audit_type = COALESCE(cc.current_audit_type, c.audit_type)
                WHERE c.status NOT IN ('closed', 'cancelled', 'completed', 'expired')
                  AND (
                    c.standards LIKE CONCAT('%', cc.standard_code, '%')
                    OR c.applied_standards LIKE CONCAT('%', cc.standard_code, '%')
                    OR c.standards IS NULL
                  )
                """
            )
        )


def downgrade() -> None:
    # Additive migration — keep columns on downgrade to avoid data loss.
    pass
