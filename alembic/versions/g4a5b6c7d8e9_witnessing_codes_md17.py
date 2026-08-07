"""witnessing_schemes + technical_clusters + witnessing_codes (KAB-AR-MD17 / IAF MD 17)

Revision ID: g4a5b6c7d8e9
Revises: f3a4b5c6d7e8
Create Date: 2026-08-07

Additive only — CREATE IF NOT EXISTS style. Preserves companies/CBs (1134/70).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
from sqlalchemy.dialects import mysql

revision = "g4a5b6c7d8e9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


# IAF MD 17–style cluster seeds (scheme_code → list of (cluster_code, name_kr, [(iaf, critical)]))
_CLUSTER_SEEDS = {
    "QMS": [
        ("QMS-A", "농·수·축산", [("01", 1), ("03", 1)]),
        ("QMS-B", "광업·석유·가스", [("02", 1), ("09", 0)]),
        ("QMS-C", "식품·음료", [("03", 1)]),
        ("QMS-D", "섬유·가죽", [("04", 0), ("05", 0)]),
        ("QMS-E", "목재·펄프·종이", [("06", 0), ("07", 0)]),
        ("QMS-F", "출판·인쇄", [("08", 0)]),
        ("QMS-G", "화학·의약품", [("12", 1), ("13", 1), ("14", 0), ("15", 0)]),
        ("QMS-H", "고무·플라스틱", [("14", 0)]),
        ("QMS-I", "비금속광물", [("15", 0), ("16", 0)]),
        ("QMS-J", "금속·기계", [("17", 1), ("18", 0), ("19", 1), ("20", 0)]),
        ("QMS-K", "전기·전자", [("19", 1), ("22", 0)]),
        ("QMS-L", "기타 제조", [("23", 0)]),
        ("QMS-M", "재활용", [("24", 0)]),
        ("QMS-N", "전력·가스·수도", [("25", 0), ("26", 0)]),
        ("QMS-O", "건설", [("28", 1)]),
        ("QMS-P", "도소매·수리", [("29", 0), ("30", 0)]),
        ("QMS-Q", "호텔·식당", [("30", 0)]),
        ("QMS-R", "운송·통신·정보", [("31", 0), ("32", 0), ("33", 0)]),
        ("QMS-S", "금융·부동산", [("32", 0), ("34", 0)]),
        ("QMS-T", "전문서비스", [("34", 0), ("35", 0)]),
        ("QMS-U", "공공·교육·보건", [("36", 0), ("37", 1), ("38", 1)]),
        ("QMS-V", "기타 서비스", [("39", 0)]),
    ],
    "EMS": [
        ("EMS-A", "농·수산·식품", [("01", 1), ("03", 1)]),
        ("EMS-B", "광업·에너지", [("02", 1), ("09", 1), ("25", 1), ("26", 0)]),
        ("EMS-C", "화학·위험물", [("12", 1), ("13", 1), ("14", 0), ("15", 0)]),
        ("EMS-D", "금속·기계·전자", [("17", 1), ("18", 0), ("19", 1), ("22", 0)]),
        ("EMS-E", "건설·폐기물", [("24", 1), ("28", 1)]),
        ("EMS-F", "운송·물류", [("31", 0)]),
        ("EMS-G", "서비스·기타", [("29", 0), ("30", 0), ("33", 0), ("34", 0), ("35", 0), ("36", 0), ("37", 0), ("38", 0), ("39", 0)]),
    ],
    "OHSMS": [
        ("OHS-A", "고위험 제조", [("02", 1), ("09", 1), ("12", 1), ("13", 1), ("17", 1), ("19", 1)]),
        ("OHS-B", "건설·토목", [("28", 1)]),
        ("OHS-C", "식품·화학 일반", [("03", 1), ("14", 0), ("15", 0)]),
        ("OHS-D", "기계·전자", [("18", 0), ("20", 0), ("22", 0)]),
        ("OHS-E", "서비스·기타", [("29", 0), ("30", 0), ("31", 0), ("33", 0), ("34", 0), ("35", 0), ("36", 0), ("37", 0), ("38", 1), ("39", 0)]),
    ],
}

_SCHEMES = [
    # code, name_kr, iso_ref, has_cluster_logic, sort_order
    ("QMS", "품질경영시스템", "ISO 9001:2015", 1, 10),
    ("EMS", "환경경영시스템", "ISO 14001:2015", 1, 20),
    ("OHSMS", "안전보건경영시스템", "ISO 45001:2018", 1, 30),
    ("ISMS", "정보보안경영시스템", "ISO/IEC 27001:2022", 0, 40),
    ("ABMS", "부패방지경영시스템", "ISO 37001:2016", 0, 50),
    ("CMS", "준법경영시스템", "ISO 37301:2021", 0, 60),
    ("EnMS", "에너지경영시스템", "ISO 50001:2018", 0, 70),
    ("FSMS", "식품안전경영시스템", "ISO 22000:2018", 0, 80),
    ("MDQMS", "의료기기 품질경영시스템", "ISO 13485:2016", 0, 90),
    ("NSMS", "원자력 공급망 품질경영시스템", "ISO 19443:2018", 0, 100),
    ("PIMS", "개인정보보호 경영시스템", "ISO/IEC 27701:2019", 0, 110),
    ("AIMS", "인공지능 경영시스템", "ISO/IEC 42001:2023", 0, 120),
]


def upgrade() -> None:
    if not _has_table("witnessing_schemes"):
        op.create_table(
            "witnessing_schemes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("name_kr", sa.String(length=100), nullable=False),
            sa.Column("iso_ref", sa.String(length=40), nullable=True),
            sa.Column(
                "has_cluster_logic",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "cycle_years_default",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("5"),
            ),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code", name="uk_witnessing_schemes_code"),
        )

    if not _has_table("technical_clusters"):
        op.create_table(
            "technical_clusters",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scheme_id", sa.Integer(), nullable=False),
            sa.Column("cluster_code", sa.String(length=20), nullable=False),
            sa.Column("name_kr", sa.String(length=100), nullable=False),
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.ForeignKeyConstraint(
                ["scheme_id"],
                ["witnessing_schemes.id"],
                name="fk_tech_clusters_scheme",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "scheme_id", "cluster_code", name="uk_tech_clusters_scheme_code"
            ),
        )

    if not _has_table("witnessing_iaf_templates"):
        op.create_table(
            "witnessing_iaf_templates",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("scheme_id", sa.Integer(), nullable=False),
            sa.Column("cluster_id", sa.Integer(), nullable=True),
            sa.Column("iaf_code", sa.String(length=10), nullable=False),
            sa.Column("description", sa.String(length=200), nullable=True),
            sa.Column(
                "is_critical",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "eligible_for_coverage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "cycle_years",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("5"),
            ),
            sa.ForeignKeyConstraint(
                ["scheme_id"],
                ["witnessing_schemes.id"],
                name="fk_wit_tmpl_scheme",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["cluster_id"],
                ["technical_clusters.id"],
                name="fk_wit_tmpl_cluster",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "scheme_id", "iaf_code", name="uk_wit_tmpl_scheme_iaf"
            ),
        )

    if not _has_table("witnessing_codes"):
        op.create_table(
            "witnessing_codes",
            sa.Column(
                "id",
                mysql.INTEGER(unsigned=True),
                autoincrement=True,
                nullable=False,
            ),
            sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("scheme_id", sa.Integer(), nullable=False),
            sa.Column("cluster_id", sa.Integer(), nullable=True),
            sa.Column("iaf_code", sa.String(length=10), nullable=False),
            sa.Column("description", sa.String(length=200), nullable=True),
            sa.Column(
                "is_critical",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "eligible_for_coverage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
            sa.Column(
                "cycle_years",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("5"),
            ),
            sa.Column("last_witness_date", sa.Date(), nullable=True),
            sa.Column("next_due_date", sa.Date(), nullable=True),
            sa.Column(
                "is_auto",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
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
                name="fk_wit_codes_cb",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["scheme_id"],
                ["witnessing_schemes.id"],
                name="fk_wit_codes_scheme",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["cluster_id"],
                ["technical_clusters.id"],
                name="fk_wit_codes_cluster",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "cb_id", "scheme_id", "iaf_code", name="uk_wit_codes_cb_scheme_iaf"
            ),
        )

    bind = op.get_bind()

    # Seed schemes
    for code, name_kr, iso_ref, has_cluster, sort_order in _SCHEMES:
        exists = bind.execute(
            text("SELECT id FROM witnessing_schemes WHERE code = :c LIMIT 1"),
            {"c": code},
        ).fetchone()
        if not exists:
            bind.execute(
                text(
                    "INSERT INTO witnessing_schemes "
                    "(code, name_kr, iso_ref, has_cluster_logic, cycle_years_default, sort_order, is_active) "
                    "VALUES (:code, :name_kr, :iso_ref, :has_cluster, 5, :sort_order, 1)"
                ),
                {
                    "code": code,
                    "name_kr": name_kr,
                    "iso_ref": iso_ref,
                    "has_cluster": has_cluster,
                    "sort_order": sort_order,
                },
            )

    # Resolve scheme ids
    scheme_ids = {
        r[0]: r[1]
        for r in bind.execute(text("SELECT code, id FROM witnessing_schemes")).fetchall()
    }

    # Seed clusters + templates for QMS/EMS/OHSMS
    for scheme_code, clusters in _CLUSTER_SEEDS.items():
        sid = scheme_ids.get(scheme_code)
        if not sid:
            continue
        for idx, (ccode, cname, iaf_list) in enumerate(clusters):
            crow = bind.execute(
                text(
                    "SELECT id FROM technical_clusters "
                    "WHERE scheme_id = :sid AND cluster_code = :cc LIMIT 1"
                ),
                {"sid": sid, "cc": ccode},
            ).fetchone()
            if crow:
                cluster_id = crow[0]
            else:
                bind.execute(
                    text(
                        "INSERT INTO technical_clusters "
                        "(scheme_id, cluster_code, name_kr, sort_order, is_active) "
                        "VALUES (:sid, :cc, :cn, :so, 1)"
                    ),
                    {"sid": sid, "cc": ccode, "cn": cname, "so": (idx + 1) * 10},
                )
                cluster_id = bind.execute(
                    text(
                        "SELECT id FROM technical_clusters "
                        "WHERE scheme_id = :sid AND cluster_code = :cc LIMIT 1"
                    ),
                    {"sid": sid, "cc": ccode},
                ).fetchone()[0]

            for iaf, critical in iaf_list:
                iaf_n = str(iaf).zfill(2) if str(iaf).isdigit() else str(iaf)
                trow = bind.execute(
                    text(
                        "SELECT id FROM witnessing_iaf_templates "
                        "WHERE scheme_id = :sid AND iaf_code = :iaf LIMIT 1"
                    ),
                    {"sid": sid, "iaf": iaf_n},
                ).fetchone()
                if trow:
                    continue
                # Prefer critical assignment if same IAF appears in multiple clusters
                eligible = 0 if critical else 1
                desc = None
                if _has_table("master_iaf_codes"):
                    try:
                        m = bind.execute(
                            text(
                                "SELECT name_kr FROM master_iaf_codes "
                                "WHERE iaf_code = :iaf OR LPAD(iaf_code, 2, '0') = :iaf "
                                "LIMIT 1"
                            ),
                            {"iaf": iaf_n},
                        ).fetchone()
                        if m:
                            desc = m[0]
                    except Exception:
                        pass
                bind.execute(
                    text(
                        "INSERT INTO witnessing_iaf_templates "
                        "(scheme_id, cluster_id, iaf_code, description, is_critical, "
                        "eligible_for_coverage, cycle_years) "
                        "VALUES (:sid, :cid, :iaf, :desc, :crit, :elig, 5)"
                    ),
                    {
                        "sid": sid,
                        "cid": cluster_id,
                        "iaf": iaf_n,
                        "desc": desc,
                        "crit": critical,
                        "elig": eligible,
                    },
                )

    # Soft-fail seed remaining IAF codes from master for cluster schemes + all for non-cluster
    if _has_table("master_iaf_codes"):
        try:
            iaf_rows = bind.execute(
                text(
                    "SELECT iaf_code, name_kr FROM master_iaf_codes "
                    "WHERE is_active = 1 OR is_active IS NULL"
                )
            ).fetchall()
        except Exception:
            iaf_rows = []
        for scheme_code, sid in scheme_ids.items():
            has_cluster = scheme_code in _CLUSTER_SEEDS
            for iaf_code, name_kr in iaf_rows:
                iaf_n = str(iaf_code).strip()
                if not iaf_n:
                    continue
                if iaf_n.isdigit():
                    iaf_n = iaf_n.zfill(2)
                exists = bind.execute(
                    text(
                        "SELECT id FROM witnessing_iaf_templates "
                        "WHERE scheme_id = :sid AND iaf_code = :iaf LIMIT 1"
                    ),
                    {"sid": sid, "iaf": iaf_n},
                ).fetchone()
                if exists:
                    continue
                # Non-cluster schemes: flat list, no coverage
                # Cluster schemes: leftover codes without cluster (no auto-coverage)
                bind.execute(
                    text(
                        "INSERT INTO witnessing_iaf_templates "
                        "(scheme_id, cluster_id, iaf_code, description, is_critical, "
                        "eligible_for_coverage, cycle_years) "
                        "VALUES (:sid, NULL, :iaf, :desc, 0, 0, 5)"
                    ),
                    {
                        "sid": sid,
                        "iaf": iaf_n,
                        "desc": name_kr,
                    },
                )


def downgrade() -> None:
    # Additive policy: do not drop production tables on downgrade.
    pass
