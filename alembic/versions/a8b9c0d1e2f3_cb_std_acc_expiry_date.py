"""cb_standard_accreditations.expiry_date — 표준별 인정만료일

Revision ID: a8b9c0d1e2f3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-07

인정번호·인정만료일은 CB 단일값이 아니라 표준(QMS/EMS/…)별로 관리한다.
등록번호(registration_no)는 이미 존재. 만료일 컬럼만 additive ALTER.
기존 CB-level expire_date는 활성 표준행에 NULL일 때만 1회 시드(덮어쓰지 않음).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "a8b9c0d1e2f3"
down_revision = "a7b8c9d0e1f2"
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
    if not _has_table("cb_standard_accreditations"):
        return
    if not _has_column("cb_standard_accreditations", "expiry_date"):
        op.add_column(
            "cb_standard_accreditations",
            sa.Column(
                "expiry_date",
                sa.Date(),
                nullable=True,
                comment="표준별 인정만료일",
            ),
        )

    # Optional one-time seed (NULL only — never overwrite):
    # CB.expire_date → expiry_date, CB.reg_no/accreditation_no → registration_no
    if _has_table("certification_bodies"):
        if _has_column("certification_bodies", "expire_date"):
            op.execute(
                text(
                    """
                    UPDATE cb_standard_accreditations a
                    INNER JOIN certification_bodies c ON c.id = a.cb_id
                    SET a.expiry_date = STR_TO_DATE(NULLIF(TRIM(c.expire_date), ''), '%Y-%m-%d')
                    WHERE a.is_active = 1
                      AND a.expiry_date IS NULL
                      AND c.expire_date IS NOT NULL
                      AND TRIM(c.expire_date) <> ''
                      AND STR_TO_DATE(NULLIF(TRIM(c.expire_date), ''), '%Y-%m-%d') IS NOT NULL
                    """
                )
            )
        op.execute(
            text(
                """
                UPDATE cb_standard_accreditations a
                INNER JOIN certification_bodies c ON c.id = a.cb_id
                SET a.registration_no = COALESCE(
                    NULLIF(TRIM(c.reg_no), ''),
                    NULLIF(TRIM(c.accreditation_no), '')
                )
                WHERE a.is_active = 1
                  AND (a.registration_no IS NULL OR TRIM(a.registration_no) = '')
                  AND (
                    (c.reg_no IS NOT NULL AND TRIM(c.reg_no) <> '')
                    OR (c.accreditation_no IS NOT NULL AND TRIM(c.accreditation_no) <> '')
                  )
                """
            )
        )


def downgrade() -> None:
    if _has_column("cb_standard_accreditations", "expiry_date"):
        op.drop_column("cb_standard_accreditations", "expiry_date")
