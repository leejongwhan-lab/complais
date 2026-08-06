"""scope_code_masters + generalize cb_scope_matrix for non-IAF taxonomies

Revision ID: v2w3x4y5z6a7
Revises: u1v2w3x4y5z6
Create Date: 2026-08-05

스토리보드: IAF 1–39는 9001/14001/45001 전용.
기타 표준은 MDQMS/FSMS/NQMS/BCMS 전용 코드 또는 코드 없음.
cb_scope_matrix.iaf_code 컬럼은 범용 scope_code로 사용(컬럼명 유지, 주석 확장).
비-IAF 표준에 잘못 저장된 IAF 행은 비활성화.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "v2w3x4y5z6a7"
down_revision = "u1v2w3x4y5z6"
branch_labels = None
depends_on = None

IAF39_STANDARDS = (
    "ISO 9001:2015",
    "ISO 9001:2026",
    "ISO 14001:2015",
    "ISO 14001:2026",
    "ISO 45001:2018",
)


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("scope_code_masters"):
        op.create_table(
            "scope_code_masters",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("taxonomy", sa.String(20), nullable=False, comment="iaf39|mdqms|fsms|nqms|bcms"),
            sa.Column("code", sa.String(30), nullable=False, comment="01 / AI / C0 / A 등"),
            sa.Column("name_ko", sa.String(255), nullable=True),
            sa.Column("name_en", sa.String(255), nullable=True),
            sa.Column("parent_code", sa.String(30), nullable=True),
            sa.Column("group_label", sa.String(100), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("meta_json", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("taxonomy", "code", name="uq_scope_code_masters_tax_code"),
        )
        op.create_index("ix_scope_code_masters_taxonomy", "scope_code_masters", ["taxonomy"])

    if _has_table("cb_scope_matrix"):
        bind = op.get_bind()
        stds = ", ".join(f"'{s}'" for s in IAF39_STANDARDS)
        bind.execute(
            text(
                f"""
                UPDATE cb_scope_matrix
                SET is_active = 0, updated_at = UTC_TIMESTAMP()
                WHERE is_active = 1
                  AND standard_code NOT IN ({stds})
                  AND iaf_code REGEXP '^[0-9]{{1,2}}$'
                """
            )
        )


def downgrade() -> None:
    if _has_table("scope_code_masters"):
        op.drop_table("scope_code_masters")
