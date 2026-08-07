"""Seed StandardMaster / StandardClause from 스토리보드 「표준별조항번호 및 제목」."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.db.session import SessionLocal
from app.services.standard_clause_titles import (
    resolve_clause_title_excel,
    seed_standard_clause_titles,
)


def seed_standards_and_clauses(excel_path: str | Path | None = None) -> None:
    path = Path(excel_path) if excel_path else resolve_clause_title_excel()
    if not path or not path.exists():
        print(f"[ERROR] 엑셀 파일을 찾을 수 없습니다: {path}")
        return

    db = SessionLocal()
    try:
        counts = seed_standard_clause_titles(db, path, force=True)
        print(f"[DONE] seeded from {path.name}")
        total = 0
        for sk, n in sorted(counts.items()):
            print(f"  {sk}: {n}")
            total += n
        print(f"[TOTAL] {total} clauses across {len(counts)} standards")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed standard_clause_masters from storyboard Excel"
    )
    parser.add_argument(
        "excel_path",
        nargs="?",
        default=None,
        help="Path to 스토리보드_0721.xlsx (sheet 표준별조항번호 및 제목)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-upsert even if rows already exist",
    )
    args = parser.parse_args()
    seed_standards_and_clauses(args.excel_path)
