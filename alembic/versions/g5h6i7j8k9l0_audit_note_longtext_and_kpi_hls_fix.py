"""Audit note LONGTEXT + document KPI HLS normalize path

Revision ID: g5h6i7j8k9l0
Revises: f4a5b6c7d8e9
Create Date: 2026-08-07

Additive ALTER only. Does not DROP ESG kpi_master / companies / CBs / iso_clauses.
KPI HLS normalization (8.2~8.10 → 8.6~8.10) is applied by
`scripts/seed_process_group_masters.py` / `app.services.process_group_masters`.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


revision = "g5h6i7j8k9l0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _col_type(table: str, column: str):
    bind = op.get_bind()
    row = bind.execute(
        text(
            "SELECT DATA_TYPE FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).first()
    return (row[0] if row else None)


def _to_longtext(table: str, column: str, nullable: bool = True) -> None:
    if not _has_table(table):
        return
    dt = _col_type(table, column)
    if not dt:
        return
    if str(dt).lower() == "longtext":
        return
    null_sql = "NULL" if nullable else "NOT NULL"
    op.execute(sa.text(f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` LONGTEXT {null_sql}"))


def upgrade() -> None:
    _to_longtext("audit_note_clauses", "finding")
    _to_longtext("audit_note_clauses", "evidence")
    _to_longtext("audit_note_clauses", "kpi_json")
    _to_longtext("audit_note_ncr", "description")
    _to_longtext("audit_note_ncr", "requirement")
    _to_longtext("audit_note_ncr", "evidence")
    _to_longtext("audit_notes", "content")
    _to_longtext("audit_notes", "summary")
    _to_longtext("hls_master", "checkpoints_summary")

    # Normalize any already-seeded bad KPI HLS codes (idempotent)
    if _has_table("audit_kpi_master") and _has_table("hls_master"):
        # ensure canonical parent exists
        op.execute(
            sa.text(
                "INSERT IGNORE INTO hls_master (hls_code, checkpoints_summary) "
                "VALUES ('8.6~8.10', "
                "'37001/22000/22301 등 세부단계 다수 보유 표준 전용 — CLAUSE_MAP 참조')"
            )
        )
        op.execute(
            sa.text(
                "UPDATE audit_kpi_master SET hls_code = '8.6~8.10' "
                "WHERE hls_code = '8.2~8.10'"
            )
        )
        # drop obsolete stub if unused
        op.execute(
            sa.text(
                "DELETE FROM hls_master WHERE hls_code = '8.2~8.10' "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM audit_kpi_master k WHERE k.hls_code = '8.2~8.10'"
                ") AND NOT EXISTS ("
                "  SELECT 1 FROM process_group_hls_map m WHERE m.hls_code = '8.2~8.10'"
                ") AND NOT EXISTS ("
                "  SELECT 1 FROM standard_clause_map c WHERE c.hls_code = '8.2~8.10'"
                ")"
            )
        )


def downgrade() -> None:
    # Keep LONGTEXT (safe); no destructive downgrade
    pass
