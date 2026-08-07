#!/usr/bin/env python3
"""Seed iso_audit_kpi_master from ComplAIs_인증심사_KPI목록.xlsx.

Safe: does NOT touch kpi_master (ESG), audit_kpi_master, companies, CBs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.db.session import SessionLocal  # noqa: E402
from app.services.iso_audit_kpis import (  # noqa: E402
    DEFAULT_EXCEL,
    seed_iso_audit_kpis,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed ISO audit KPI master from Excel")
    ap.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL,
        help=f"Excel path (default: {DEFAULT_EXCEL})",
    )
    ap.add_argument(
        "--no-replace",
        action="store_true",
        help="Upsert without DELETE (default replaces seed rows)",
    )
    args = ap.parse_args()
    if not args.excel.exists():
        print(f"ERROR: Excel not found: {args.excel}", file=sys.stderr)
        return 1
    db = SessionLocal()
    try:
        counts = seed_iso_audit_kpis(
            db, args.excel, replace=not args.no_replace
        )
        print("seeded:", counts)
        if counts.get("companies") not in (None, 1134):
            print("WARN companies count:", counts.get("companies"), "(expected 1134)")
        if counts.get("certification_bodies") not in (None, 71):
            print(
                "WARN certification_bodies count:",
                counts.get("certification_bodies"),
                "(expected 71)",
            )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
