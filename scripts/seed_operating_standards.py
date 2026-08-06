"""Seed operating 14 standards (+ META) into standard_masters and iso_standards."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy import text

from app.data.standards_catalog import OPERATING_STANDARDS, STANDARD_CATALOG
from app.db.session import SessionLocal, engine
from app.models.master_data import IsoStandard
from app.models.standard import StandardMaster


DDL_STANDARD_MASTERS = """
CREATE TABLE IF NOT EXISTS standard_masters (
  id INT NOT NULL AUTO_INCREMENT,
  standard_key VARCHAR(40) NOT NULL,
  family_code VARCHAR(20) NOT NULL,
  edition_year INT NULL,
  iso_number VARCHAR(40) NOT NULL,
  display_code VARCHAR(60) NOT NULL,
  standard_code VARCHAR(60) NOT NULL,
  standard_name VARCHAR(100) NOT NULL,
  version_year INT NULL,
  clauses_status VARCHAR(20) NOT NULL DEFAULT 'READY',
  clauses_note VARCHAR(255) NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'CERTIFIABLE',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  description VARCHAR(255) NULL,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_standard_key (standard_key),
  UNIQUE KEY uq_standard_code (standard_code),
  KEY idx_family (family_code),
  KEY idx_edition (edition_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

DDL_CLAUSE_MASTERS = """
CREATE TABLE IF NOT EXISTS standard_clause_masters (
  id INT NOT NULL AUTO_INCREMENT,
  standard_id INT NOT NULL,
  clause_number VARCHAR(30) NOT NULL,
  clause_title_kr VARCHAR(255) NOT NULL DEFAULT '',
  depth INT NOT NULL DEFAULT 1,
  sort_order INT NOT NULL DEFAULT 0,
  requirements_summary TEXT NULL,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uix_standard_clause_number (standard_id, clause_number),
  KEY idx_clause_standard (standard_id),
  CONSTRAINT fk_clause_standard
    FOREIGN KEY (standard_id) REFERENCES standard_masters(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

DDL_ISO_STANDARDS = """
CREATE TABLE IF NOT EXISTS iso_standards (
  id INT NOT NULL AUTO_INCREMENT,
  standard_key VARCHAR(40) NULL,
  standard_code VARCHAR(50) NOT NULL,
  standard_name_ko VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NULL,
  updated_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_iso_standard_code (standard_code),
  UNIQUE KEY uq_iso_standard_key (standard_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def _ensure_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        conn.execute(text(DDL_STANDARD_MASTERS))
        # migrate older standard_masters (minimal columns) if needed
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name='standard_masters'"
                )
            )
        }
        alters = []
        wanted = {
            "standard_key": "VARCHAR(40) NULL",
            "family_code": "VARCHAR(20) NULL",
            "edition_year": "INT NULL",
            "iso_number": "VARCHAR(40) NULL",
            "display_code": "VARCHAR(60) NULL",
            "clauses_status": "VARCHAR(20) NOT NULL DEFAULT 'READY'",
            "clauses_note": "VARCHAR(255) NULL",
            "role": "VARCHAR(20) NOT NULL DEFAULT 'CERTIFIABLE'",
        }
        for name, typ in wanted.items():
            if name not in cols:
                alters.append(f"ADD COLUMN {name} {typ}")
        if alters:
            conn.execute(text(f"ALTER TABLE standard_masters {', '.join(alters)}"))
        conn.execute(text(DDL_CLAUSE_MASTERS))
        conn.execute(text(DDL_ISO_STANDARDS))
        iso_cols = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT COLUMN_NAME FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name='iso_standards'"
                )
            )
        }
        if iso_cols and "standard_key" not in iso_cols:
            conn.execute(
                text("ALTER TABLE iso_standards ADD COLUMN standard_key VARCHAR(40) NULL")
            )
            try:
                conn.execute(
                    text(
                        "ALTER TABLE iso_standards "
                        "ADD UNIQUE KEY uq_iso_standard_key (standard_key)"
                    )
                )
            except Exception:
                pass
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def seed_standard_masters(include_meta: bool = True) -> None:
    _ensure_schema()
    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        rows = STANDARD_CATALOG if include_meta else OPERATING_STANDARDS
        for s in rows:
            row = (
                db.query(StandardMaster)
                .filter(StandardMaster.standard_key == s.standard_key)
                .first()
            )
            if row is None:
                # legacy match by display/standard_code
                row = (
                    db.query(StandardMaster)
                    .filter(StandardMaster.standard_code == s.display_code)
                    .first()
                )
            if row is None:
                row = StandardMaster(standard_key=s.standard_key)
                db.add(row)

            row.standard_key = s.standard_key
            row.family_code = s.family_code
            row.edition_year = s.edition_year
            row.iso_number = s.iso_number
            row.display_code = s.display_code
            row.standard_code = s.display_code
            row.standard_name = s.name_ko
            row.version_year = s.edition_year
            row.clauses_status = s.clauses_status
            row.clauses_note = s.clauses_note
            row.role = s.role
            row.is_active = True
            row.description = s.clauses_note
            if row.created_at is None:
                row.created_at = now
            row.updated_at = now

            # iso_standards (CB scope용) — CERTIFIABLE only
            if s.role == "CERTIFIABLE":
                iso = (
                    db.query(IsoStandard)
                    .filter(IsoStandard.standard_code == s.display_code)
                    .first()
                )
                if iso is None and hasattr(IsoStandard, "standard_key"):
                    iso = (
                        db.query(IsoStandard)
                        .filter(IsoStandard.standard_key == s.standard_key)
                        .first()
                    )
                if iso is None:
                    iso = IsoStandard(
                        standard_code=s.display_code,
                        standard_name_ko=s.name_ko,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(iso)
                iso.standard_name_ko = s.name_ko
                iso.standard_code = s.display_code
                if hasattr(iso, "standard_key"):
                    iso.standard_key = s.standard_key
                iso.is_active = True
                iso.updated_at = now

        # 운영 14 밖 표준(예: ISO 22301)은 iso_standards 비활성
        operating_codes = {s.display_code for s in OPERATING_STANDARDS}
        for iso in db.query(IsoStandard).all():
            if iso.standard_code not in operating_codes:
                iso.is_active = False
                iso.updated_at = now

        db.commit()
        cert = db.query(StandardMaster).filter(StandardMaster.role == "CERTIFIABLE").count()
        meta = db.query(StandardMaster).filter(StandardMaster.role == "META").count()
        print(f"[OK] standard_masters CERTIFIABLE={cert} META={meta}")
        active_iso = (
            db.query(IsoStandard).filter(IsoStandard.is_active.is_(True)).count()
        )
        print(f"[OK] iso_standards active={active_iso}")
        pending = (
            db.query(StandardMaster)
            .filter(StandardMaster.clauses_status == "PENDING")
            .all()
        )
        for p in pending:
            print(f"  [PENDING clauses] {p.standard_key} — {p.clauses_note}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_standard_masters()
