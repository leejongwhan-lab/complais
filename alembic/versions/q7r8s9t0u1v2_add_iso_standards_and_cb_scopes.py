"""extend iaf_codes + create iso_standards + cb_accredited_scopes

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-08-05

IAF/ISO 마스터를 정규화하고 CB 인정 Scope를
(CB × 표준 1개 × IAF 1개) 행 단위로 관리한다.

- iaf_codes: description / is_active / updated_at 보강 (기존 테이블 유지)
- iso_standards: 인증 표준 마스터 (신규)
- cb_accredited_scopes: CB 인정 범위 (신규, certification_bodies.id 참조)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "q7r8s9t0u1v2"
down_revision = "p6q7r8s9t0u1"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    # 1) IAF 마스터 보강 (이미 a1b2c3d4e5f6 에서 생성됨)
    if _has_table("iaf_codes"):
        if not _has_column("iaf_codes", "description"):
            op.add_column("iaf_codes", sa.Column("description", sa.Text(), nullable=True))
        if not _has_column("iaf_codes", "is_active"):
            op.add_column(
                "iaf_codes",
                sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            )
        if not _has_column("iaf_codes", "updated_at"):
            op.add_column(
                "iaf_codes",
                sa.Column(
                    "updated_at",
                    sa.TIMESTAMP(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
                ),
            )

    # 2) ISO 인증 표준 마스터
    if not _has_table("iso_standards"):
        op.create_table(
            "iso_standards",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(
                "standard_code",
                sa.String(length=50),
                nullable=False,
                comment="예: ISO 9001:2015",
            ),
            sa.Column(
                "standard_name_ko",
                sa.String(length=255),
                nullable=False,
                comment="표준명(국문)",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("standard_code", name="uk_iso_standards_code"),
        )

        # standard_masters 가 있으면 초기 이관 (있으면 무시)
        if _has_table("standard_masters"):
            op.execute(
                """
                INSERT IGNORE INTO iso_standards (standard_code, standard_name_ko, is_active)
                SELECT standard_code, standard_name, is_active
                FROM standard_masters
                """
            )

    # 3) CB 인정 Scope (1행 = CB + 표준1 + IAF1)
    if not _has_table("cb_accredited_scopes"):
        op.create_table(
            "cb_accredited_scopes",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("standard_id", sa.Integer(), nullable=False),
            sa.Column("iaf_code_id", sa.BigInteger(), nullable=False),
            sa.Column(
                "accreditation_body",
                sa.String(length=100),
                nullable=False,
                server_default="KAB",
            ),
            sa.Column("approval_date", sa.Date(), nullable=True),
            sa.Column("expiry_date", sa.Date(), nullable=True),
            sa.Column(
                "status",
                sa.Enum("active", "suspended", "withdrawn", name="cb_accredited_scope_status"),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["cb_id"],
                ["certification_bodies.id"],
                name="fk_cb_accredited_scopes_cb",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["standard_id"],
                ["iso_standards.id"],
                name="fk_cb_accredited_scopes_standard",
            ),
            sa.ForeignKeyConstraint(
                ["iaf_code_id"],
                ["iaf_codes.id"],
                name="fk_cb_accredited_scopes_iaf",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "cb_id",
                "standard_id",
                "iaf_code_id",
                name="uk_cb_standard_iaf",
            ),
        )
        op.create_index(
            "ix_cb_accredited_scopes_cb_id",
            "cb_accredited_scopes",
            ["cb_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("cb_accredited_scopes"):
        op.drop_index("ix_cb_accredited_scopes_cb_id", table_name="cb_accredited_scopes")
        op.drop_table("cb_accredited_scopes")
    if _has_table("iso_standards"):
        op.drop_table("iso_standards")
    if _has_table("iaf_codes"):
        if _has_column("iaf_codes", "updated_at"):
            op.drop_column("iaf_codes", "updated_at")
        if _has_column("iaf_codes", "is_active"):
            op.drop_column("iaf_codes", "is_active")
        if _has_column("iaf_codes", "description"):
            op.drop_column("iaf_codes", "description")
