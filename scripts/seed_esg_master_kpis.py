"""Seed esg_master_kpis from ESG_KPI_최종통합본_353개.xlsx (idempotent reload)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.data.esg_master_kpis_seed import DEFAULT_EXCEL, reload_esg_master_kpis
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Reload esg_master_kpis from Excel")
    parser.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL,
        help="Path to ESG KPI master xlsx",
    )
    args = parser.parse_args()

    if not args.excel.exists():
        print(f"[ERROR] Excel not found: {args.excel}")
        sys.exit(1)

    db = SessionLocal()
    try:
        result = reload_esg_master_kpis(db, args.excel)
        print(f"[OK] excel={args.excel}")
        print(f"[OK] deleted={result['deleted']} inserted={result['inserted']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
