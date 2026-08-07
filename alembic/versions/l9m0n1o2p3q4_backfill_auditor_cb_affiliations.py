"""Backfill multi CB affiliations + ensure ESG runtime tables

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-08-07

Additive / idempotent:
- Ensure auditor_cb_memberships unique (auditor_id, cb_id) — multi-affiliation source
- Backfill missing affiliation rows from:
  * auditors.primary_cb_id
  * pre_registered_auditors.cb_id (matched → auditors.user_id)
  * contracts.lead_auditor_id / verifier_auditor_id (+ member_auditor_ids JSON)
- Re-ensure company_esg_kpi_* tables if missing (no DROP)

Does NOT truncate companies / certification_bodies.
Contract fee/terms are not copied into affiliation rows beyond required NOT NULL defaults.
"""
from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import mysql

revision = "l9m0n1o2p3q4"
down_revision = "k8l9m0n1o2p3"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return any(ix["name"] == index_name for ix in inspect(op.get_bind()).get_indexes(table))


def _ensure_esg_runtime() -> None:
    """Idempotent ensure for company ESG runtime tables (same as k8)."""
    if not _has_table("esg_master_kpis"):
        return

    company_id_col = mysql.INTEGER(unsigned=True)

    if not _has_table("company_esg_kpi_goals"):
        op.create_table(
            "company_esg_kpi_goals",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("target_year", sa.Integer(), nullable=False),
            sa.Column("target_value", sa.String(length=100), nullable=False),
            sa.Column("unit", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", "target_year", name="uq_company_esg_kpi_goal_year"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_kpi_goals_company_id",
            "company_esg_kpi_goals",
            ["company_id"],
        )

    if not _has_table("company_esg_kpi_values"):
        op.create_table(
            "company_esg_kpi_values",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("value", sa.String(length=100), nullable=False),
            sa.Column(
                "source_mode",
                sa.String(length=20),
                nullable=False,
                server_default="company",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", "year", name="uq_company_esg_kpi_value_year"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_kpi_values_company_id",
            "company_esg_kpi_values",
            ["company_id"],
        )

    if not _has_table("company_esg_audit_notes"):
        op.create_table(
            "company_esg_audit_notes",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("company_id", company_id_col, nullable=False),
            sa.Column("kpi_id", sa.BigInteger(), nullable=False),
            sa.Column("note", mysql.MEDIUMTEXT(), nullable=False),
            sa.Column("auditor_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["kpi_id"], ["esg_master_kpis.kpi_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "company_id", "kpi_id", name="uq_company_esg_audit_note_kpi"
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index(
            "ix_company_esg_audit_notes_company_id",
            "company_esg_audit_notes",
            ["company_id"],
        )


def _insert_affiliation(conn, auditor_id: int, cb_id: int, *, is_primary: bool = False) -> int:
    """Insert affiliation if missing. Returns 1 if inserted, 0 otherwise."""
    exists = conn.execute(
        text(
            """
            SELECT 1 FROM auditor_cb_memberships
            WHERE auditor_id = :aid AND cb_id = :cid
            LIMIT 1
            """
        ),
        {"aid": auditor_id, "cid": cb_id},
    ).first()
    if exists:
        return 0
    # Required NOT NULL cols use DB defaults where possible; set explicitly for safety.
    conn.execute(
        text(
            """
            INSERT INTO auditor_cb_memberships
              (auditor_id, cb_id, employment_type, is_freelance, status, is_primary,
               created_at, updated_at)
            VALUES
              (:aid, :cid, 'parttime', 0, 'approved', :is_primary, NOW(), NOW())
            """
        ),
        {"aid": auditor_id, "cid": cb_id, "is_primary": 1 if is_primary else 0},
    )
    return 1


def _parse_member_ids(raw) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        out = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    s = str(raw).strip()
    if not s or s in ("[]", "null", "None"):
        return []
    try:
        data = json.loads(s)
    except Exception:
        # comma-separated fallback
        out = []
        for part in s.replace("[", "").replace("]", "").split(","):
            part = part.strip().strip('"').strip("'")
            if part.isdigit():
                out.append(int(part))
        return out
    if isinstance(data, list):
        out = []
        for x in data:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    return []


def _backfill_affiliations() -> dict:
    if not _has_table("auditor_cb_memberships") or not _has_table("auditors"):
        return {"skipped": True}

    conn = op.get_bind()
    inserted = {
        "from_primary_cb": 0,
        "from_pre_registered": 0,
        "from_contracts": 0,
    }

    # 1) primary_cb_id → affiliation
    if _has_column("auditors", "primary_cb_id"):
        rows = conn.execute(
            text(
                """
                SELECT a.id AS auditor_id, a.primary_cb_id AS cb_id
                FROM auditors a
                WHERE a.primary_cb_id IS NOT NULL
                  AND EXISTS (
                    SELECT 1 FROM certification_bodies cb WHERE cb.id = a.primary_cb_id
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM auditor_cb_memberships m
                    WHERE m.auditor_id = a.id AND m.cb_id = a.primary_cb_id
                  )
                """
            )
        ).mappings().all()
        for r in rows:
            inserted["from_primary_cb"] += _insert_affiliation(
                conn, int(r["auditor_id"]), int(r["cb_id"]), is_primary=True
            )

    # 2) pre_registered matched → affiliation
    if _has_table("pre_registered_auditors") and _has_column("auditors", "user_id"):
        rows = conn.execute(
            text(
                """
                SELECT a.id AS auditor_id, p.cb_id AS cb_id
                FROM pre_registered_auditors p
                INNER JOIN auditors a ON a.user_id = p.matched_user_id
                WHERE p.matched_user_id IS NOT NULL
                  AND p.cb_id IS NOT NULL
                  AND (p.is_active IS NULL OR p.is_active = 1)
                  AND EXISTS (
                    SELECT 1 FROM certification_bodies cb WHERE cb.id = p.cb_id
                  )
                  AND NOT EXISTS (
                    SELECT 1 FROM auditor_cb_memberships m
                    WHERE m.auditor_id = a.id AND m.cb_id = p.cb_id
                  )
                """
            )
        ).mappings().all()
        for r in rows:
            inserted["from_pre_registered"] += _insert_affiliation(
                conn, int(r["auditor_id"]), int(r["cb_id"]), is_primary=False
            )

    # 3) contracts lead / verifier / members → affiliation (CB link only, no fee terms)
    if _has_table("contracts") and _has_column("contracts", "cb_id"):
        pairs: set[tuple[int, int]] = set()
        lead_rows = conn.execute(
            text(
                """
                SELECT lead_auditor_id AS auditor_id, cb_id
                FROM contracts
                WHERE lead_auditor_id IS NOT NULL AND cb_id IS NOT NULL
                """
            )
        ).mappings().all()
        for r in lead_rows:
            pairs.add((int(r["auditor_id"]), int(r["cb_id"])))

        if _has_column("contracts", "verifier_auditor_id"):
            ver_rows = conn.execute(
                text(
                    """
                    SELECT verifier_auditor_id AS auditor_id, cb_id
                    FROM contracts
                    WHERE verifier_auditor_id IS NOT NULL AND cb_id IS NOT NULL
                    """
                )
            ).mappings().all()
            for r in ver_rows:
                pairs.add((int(r["auditor_id"]), int(r["cb_id"])))

        if _has_column("contracts", "member_auditor_ids"):
            mem_rows = conn.execute(
                text(
                    """
                    SELECT member_auditor_ids, cb_id
                    FROM contracts
                    WHERE cb_id IS NOT NULL
                      AND member_auditor_ids IS NOT NULL
                      AND member_auditor_ids <> ''
                      AND member_auditor_ids <> '[]'
                    """
                )
            ).mappings().all()
            for r in mem_rows:
                for aid in _parse_member_ids(r["member_auditor_ids"]):
                    pairs.add((aid, int(r["cb_id"])))

        # Only insert for auditors that exist
        for auditor_id, cb_id in sorted(pairs):
            aud_ok = conn.execute(
                text("SELECT 1 FROM auditors WHERE id = :aid LIMIT 1"),
                {"aid": auditor_id},
            ).first()
            cb_ok = conn.execute(
                text("SELECT 1 FROM certification_bodies WHERE id = :cid LIMIT 1"),
                {"cid": cb_id},
            ).first()
            if not aud_ok or not cb_ok:
                continue
            inserted["from_contracts"] += _insert_affiliation(
                conn, auditor_id, cb_id, is_primary=False
            )

    return inserted


def upgrade() -> None:
    if _has_table("auditor_cb_memberships") and not _has_index(
        "auditor_cb_memberships", "uq_auditor_cb"
    ):
        # Unique multi-affiliation key (skip if duplicate rows already exist)
        dup = (
            op.get_bind()
            .execute(
                text(
                    """
                    SELECT 1 FROM auditor_cb_memberships
                    GROUP BY auditor_id, cb_id HAVING COUNT(*) > 1 LIMIT 1
                    """
                )
            )
            .first()
        )
        if not dup:
            op.create_index(
                "uq_auditor_cb",
                "auditor_cb_memberships",
                ["auditor_id", "cb_id"],
                unique=True,
            )

    _backfill_affiliations()
    _ensure_esg_runtime()

    if _has_table("esg_master_kpis") and not _has_column(
        "esg_master_kpis", "criteria_mapping"
    ):
        op.add_column(
            "esg_master_kpis",
            sa.Column(
                "criteria_mapping",
                sa.String(length=150),
                nullable=True,
                comment="ISO/기준 매핑 · 데이터 경로 표시용",
            ),
        )


def downgrade() -> None:
    # Keep affiliation rows and ESG tables — data-preserving migration.
    pass
