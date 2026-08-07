"""iso_clauses_master + audit_note_clauses.kpi_json

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-08-07

스토리보드 조항 마스터(iso_clauses_master)와 조항별 선택 KPI JSON 컬럼을
additive 방식으로 추가한다. DROP/TRUNCATE 없음.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
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
    bind = op.get_bind()
    if not _has_table("iso_clauses_master"):
        op.create_table(
            "iso_clauses_master",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("standard_key", sa.String(40), nullable=False),
            sa.Column("family_code", sa.String(20), nullable=True),
            sa.Column("clause_no", sa.String(30), nullable=False),
            sa.Column("clause_title", sa.String(255), nullable=False, server_default=""),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("default_kpi_list", sa.Text(), nullable=True),
            sa.Column("checkpoints", sa.Text(), nullable=True),
            sa.Column("group_name", sa.String(100), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_standard_code", sa.String(10), nullable=True),
            sa.Column("source_clause_id", sa.Integer(), nullable=True),
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
            sa.UniqueConstraint(
                "standard_key", "clause_no", name="uq_iso_clauses_std_clause"
            ),
        )
        op.create_index(
            "ix_iso_clauses_master_standard_key",
            "iso_clauses_master",
            ["standard_key"],
        )

    if _has_table("audit_note_clauses") and not _has_column(
        "audit_note_clauses", "kpi_json"
    ):
        op.add_column(
            "audit_note_clauses",
            sa.Column("kpi_json", sa.Text(), nullable=True),
        )

    # Best-effort seed from standard_clauses (storyboard checklist). Safe if empty.
    if _has_table("iso_clauses_master") and _has_table("standard_clauses"):
        n = bind.execute(text("SELECT COUNT(*) FROM iso_clauses_master")).scalar() or 0
        if int(n) == 0:
            # Seed is performed by app.services.iso_clauses_master.ensure_iso_clauses_master
            pass


def downgrade() -> None:
    # Additive-only policy: do not drop master data tables in downgrade.
    if _has_table("audit_note_clauses") and _has_column("audit_note_clauses", "kpi_json"):
        op.drop_column("audit_note_clauses", "kpi_json")
