"""audit_doc_data contract_id/is_demo + master seeds for doc demo

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-08-07

ADDITIVE only:
- audit_doc_data.contract_id, is_demo
- standard_master ISO13485 (if missing)
- standard_masters BCMS_2019 (if missing)
No DROP/TRUNCATE of companies / CBs / masters.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "n1o2p3q4r5s6"
down_revision = "m0n1o2p3q4r5"
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
    if _has_table("audit_doc_data"):
        if not _has_column("audit_doc_data", "contract_id"):
            op.add_column(
                "audit_doc_data",
                sa.Column("contract_id", sa.Integer(), nullable=True, comment="contracts.id"),
            )
        if not _has_column("audit_doc_data", "is_demo"):
            op.add_column(
                "audit_doc_data",
                sa.Column(
                    "is_demo",
                    sa.SmallInteger(),
                    nullable=False,
                    server_default="0",
                    comment="1=demo/sample row",
                ),
            )

    if _has_table("standard_master"):
        row = bind.execute(
            text("SELECT 1 FROM standard_master WHERE standard_code='ISO13485' LIMIT 1")
        ).first()
        if not row:
            bind.execute(
                text(
                    "INSERT INTO standard_master "
                    "(standard_code, standard_name, hls_adopted, native_structure_note) "
                    "VALUES ('ISO13485', 'ISO 13485:2016 (의료기기 품질경영시스템)', 'Y', "
                    "'MDQMS_2016')"
                )
            )

    if _has_table("standard_masters"):
        row = bind.execute(
            text(
                "SELECT 1 FROM standard_masters "
                "WHERE standard_key='BCMS_2019' "
                "   OR standard_code IN ('ISO 22301:2019','ISO22301','22301') "
                "   OR display_code='ISO 22301:2019' "
                "LIMIT 1"
            )
        ).first()
        if not row:
            bind.execute(
                text(
                    "INSERT INTO standard_masters "
                    "(standard_key, family_code, edition_year, iso_number, display_code, "
                    " standard_code, standard_name, version_year, clauses_status, role, is_active) "
                    "VALUES "
                    "('BCMS_2019','BCMS',2019,'ISO 22301','ISO 22301:2019',"
                    " 'ISO 22301:2019','사업연속성경영시스템',2019,'READY','CERTIFIABLE',1)"
                )
            )


def downgrade() -> None:
    # Additive migration — leave columns/rows in place (safe for shared masters).
    pass
