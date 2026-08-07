"""Seed process-group / HLS / standard-map / audit KPI masters from Excel."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.db.session import SessionLocal
from app.services.process_group_masters import DEFAULT_EXCEL, seed_process_group_masters


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed process-group / HLS / audit KPI masters from Excel"
    )
    parser.add_argument(
        "--excel",
        type=Path,
        default=DEFAULT_EXCEL,
        help="Path to ISO process-group seed xlsx",
    )
    parser.add_argument(
        "--no-replace",
        action="store_true",
        help="Upsert only; do not DELETE existing seed rows first",
    )
    args = parser.parse_args()

    if not args.excel.exists():
        print(f"[ERROR] Excel not found: {args.excel}")
        sys.exit(1)

    db = SessionLocal()
    try:
        counts = seed_process_group_masters(
            db, args.excel, replace=not args.no_replace
        )
        print(f"[OK] excel={args.excel}")
        for table, n in counts.items():
            print(f"[OK] {table}={n}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
