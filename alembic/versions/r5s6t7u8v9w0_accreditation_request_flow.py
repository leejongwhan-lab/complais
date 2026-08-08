"""accreditation request flow — record scopes + matrix FK to SoT

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-08-08

- Ensure cb_accreditation_record_scopes exists (child of request envelope)
- Add per-scope status / reject_reason
- Add nullable cb_scope_matrix.standard_accreditation_id FK → cb_standard_accreditations
- Backfill FK from (cb_id, standard_code); NO DROP/TRUNCATE; no cb_accredited_scopes dual-SoT
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "r5s6t7u8v9w0"
down_revision = "q4r5s6t7u8v9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    # 1) Request child scopes table (missing locally even when parent exists)
    if not _has_table("cb_accreditation_record_scopes"):
        op.create_table(
            "cb_accreditation_record_scopes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cb_accreditation_id", sa.Integer(), nullable=False),
            sa.Column("iso_standard_id", sa.Integer(), nullable=False),
            sa.Column("iaf_code", sa.String(length=50), nullable=False),
            sa.Column("is_approved", sa.Boolean(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=True),
            sa.Column("reject_reason", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["cb_accreditation_id"],
                ["cb_accreditation_records.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(["iso_standard_id"], ["standard_masters.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_cb_accreditation_record_scopes_id"),
            "cb_accreditation_record_scopes",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_cb_accreditation_record_scopes_cb_accreditation_id"),
            "cb_accreditation_record_scopes",
            ["cb_accreditation_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_cb_accreditation_record_scopes_iso_standard_id"),
            "cb_accreditation_record_scopes",
            ["iso_standard_id"],
            unique=False,
        )
        op.execute(
            text(
                "UPDATE cb_accreditation_record_scopes "
                "SET status = 'PENDING' WHERE status IS NULL"
            )
        )
    else:
        if not _has_column("cb_accreditation_record_scopes", "status"):
            op.add_column(
                "cb_accreditation_record_scopes",
                sa.Column("status", sa.String(length=20), nullable=True),
            )
            op.execute(
                text(
                    "UPDATE cb_accreditation_record_scopes "
                    "SET status = CASE WHEN is_approved = 1 THEN 'APPROVED' ELSE 'PENDING' END "
                    "WHERE status IS NULL"
                )
            )
        if not _has_column("cb_accreditation_record_scopes", "reject_reason"):
            op.add_column(
                "cb_accreditation_record_scopes",
                sa.Column("reject_reason", sa.Text(), nullable=True),
            )

    # 2) Subordinate matrix → SoT (nullable FK; backfill where possible)
    if _has_table("cb_scope_matrix") and _has_table("cb_standard_accreditations"):
        if not _has_column("cb_scope_matrix", "standard_accreditation_id"):
            op.add_column(
                "cb_scope_matrix",
                sa.Column(
                    "standard_accreditation_id",
                    sa.BigInteger(),
                    nullable=True,
                ),
            )
            op.create_index(
                "ix_cb_scope_matrix_standard_accreditation_id",
                "cb_scope_matrix",
                ["standard_accreditation_id"],
                unique=False,
            )
            op.create_foreign_key(
                "fk_cb_scope_matrix_std_acc",
                "cb_scope_matrix",
                "cb_standard_accreditations",
                ["standard_accreditation_id"],
                ["id"],
                ondelete="SET NULL",
            )
        # Backfill exact standard_code match, then leave unmatched NULL
        op.execute(
            text(
                """
                UPDATE cb_scope_matrix m
                INNER JOIN cb_standard_accreditations a
                  ON a.cb_id = m.cb_id
                 AND a.standard_code = m.standard_code
                SET m.standard_accreditation_id = a.id
                WHERE m.standard_accreditation_id IS NULL
                """
            )
        )


def downgrade() -> None:
    # Soft downgrade only — do not drop request scopes table (may hold history)
    if _has_table("cb_scope_matrix") and _has_column(
        "cb_scope_matrix", "standard_accreditation_id"
    ):
        try:
            op.drop_constraint("fk_cb_scope_matrix_std_acc", "cb_scope_matrix", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index(
                "ix_cb_scope_matrix_standard_accreditation_id", table_name="cb_scope_matrix"
            )
        except Exception:
            pass
        op.drop_column("cb_scope_matrix", "standard_accreditation_id")
