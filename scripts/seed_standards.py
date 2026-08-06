"""Seed StandardMaster / StandardClause from '표준 별 조항번호 및 조항제목.xlsx'."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# 프로젝트 루트 디렉터리를 sys.path에 자동 추가 (단독 실행 지원)
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import pandas as pd
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.data.standards_catalog import STANDARD_CATALOG
from app.models.standard import StandardClause, StandardMaster


def _resolve_catalog(display_or_code: str):
    """display_code / ISO 문자열 → catalog row."""
    text = display_or_code.strip()
    for s in STANDARD_CATALOG:
        if s.display_code == text or s.standard_key == text:
            return s
    # ISO 9001:2015 형태
    for s in STANDARD_CATALOG:
        if s.display_code.upper() == text.upper():
            return s
    return None

# 엑셀 파일은 backend 프로젝트 루트가 아닌 상위(워크스페이스) 루트에 위치.
_CANDIDATE_PATHS = [
    BASE_DIR / "표준 별 조항번호 및 조항제목.xlsx",
    BASE_DIR.parent.parent / "표준 별 조항번호 및 조항제목.xlsx",
]
DEFAULT_EXCEL = next((p for p in _CANDIDATE_PATHS if p.exists()), _CANDIDATE_PATHS[0])


def seed_standards_and_clauses(excel_path: str | Path = DEFAULT_EXCEL) -> None:
    excel_path = Path(excel_path)
    if not excel_path.exists():
        print(f"[ERROR] 엑셀 파일을 찾을 수 없습니다: {excel_path}")
        return

    db: Session = SessionLocal()
    try:
        # NFD 파일명 대응 및 엑셀 읽기
        df = pd.read_excel(excel_path)
        clean_df = df.iloc[2:].copy().drop(columns=["Unnamed: 0"])

        # Row 1 표준 헤더 (운영 14 + META; QMS/EMS 2026은 PENDING)
        raw_standards = df.iloc[1, 2:].values
        clean_df.columns = ["clause_number"] + list(raw_standards)
        clean_df = clean_df.dropna(subset=["clause_number"]).reset_index(drop=True)

        print(f"[START] 총 {len(raw_standards)}개 표준 데이터 시딩 시작...\n")

        for std_text in raw_standards:
            std_text_str = str(std_text).strip()

            # 표준 코드 및 이름 분리 (예: 'ISO 9001:2015 품질경영시스템')
            m = re.match(r"^(ISO(?:/IEC)?\s+[\d\-:]+)\s+(.+)$", std_text_str)
            if m:
                code, name = m.group(1), m.group(2)
            else:
                code, name = std_text_str, std_text_str

            catalog = _resolve_catalog(code)
            year_match = re.search(r":(\d{4})", code)
            year = (
                catalog.edition_year
                if catalog and catalog.edition_year is not None
                else (int(year_match.group(1)) if year_match else None)
            )
            display = catalog.display_code if catalog else code
            name_ko = catalog.name_ko if catalog else name
            standard_key = catalog.standard_key if catalog else (
                f"UNK_{year}" if year else code[:40]
            )
            family = catalog.family_code if catalog else "UNK"
            iso_number = catalog.iso_number if catalog else re.sub(r":\d{4}$", "", code).strip()
            clauses_status = catalog.clauses_status if catalog else "READY"
            role = catalog.role if catalog else "CERTIFIABLE"

            std_master = (
                db.query(StandardMaster)
                .filter(
                    (StandardMaster.standard_key == standard_key)
                    | (StandardMaster.standard_code == display)
                )
                .first()
            )
            if not std_master:
                std_master = StandardMaster(standard_key=standard_key)
                db.add(std_master)
                db.flush()
                print(f"[NEW] StandardMaster 신규 등록: {standard_key} ({display})")

            std_master.standard_key = standard_key
            std_master.family_code = family
            std_master.edition_year = year
            std_master.iso_number = iso_number
            std_master.display_code = display
            std_master.standard_code = display
            std_master.standard_name = name_ko
            std_master.version_year = year
            std_master.clauses_status = clauses_status
            std_master.clauses_note = catalog.clauses_note if catalog else None
            std_master.role = role
            std_master.is_active = True
            if clauses_status == "PENDING":
                std_master.description = (
                    catalog.clauses_note if catalog else "조항 미확정"
                )
                db.commit()
                print(f"[PENDING] {standard_key} — 조항 시드 스킵")
                continue

            # 2. 세부 조항 파싱 & 저장
            clause_rows = clean_df[["clause_number", std_text]].dropna()
            clause_rows = clause_rows[clause_rows[std_text] != "-"]

            added_count = 0
            for idx, row in clause_rows.iterrows():
                c_num = str(row["clause_number"]).strip()
                c_title = str(row[std_text]).strip()
                depth = len(c_num.split("."))

                clause_obj = db.query(StandardClause).filter_by(
                    standard_id=std_master.id,
                    clause_number=c_num,
                ).first()

                if not clause_obj:
                    clause_obj = StandardClause(
                        standard_id=std_master.id,
                        clause_number=c_num,
                        clause_title_kr=c_title,
                        depth=depth,
                        sort_order=added_count + 1,
                    )
                    db.add(clause_obj)
                    added_count += 1
                else:
                    clause_obj.clause_title_kr = c_title
                    clause_obj.depth = depth

            db.commit()
            print(f"  -> {standard_key}: 총 {added_count}개 조항 저장 완료.")

        print("\n[DONE] 모든 표준 및 조항 데이터가 성공적으로 DB에 저장되었습니다!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed StandardMaster/StandardClause from Excel")
    parser.add_argument(
        "excel_path",
        nargs="?",
        default=str(DEFAULT_EXCEL),
        help="Path to 표준 별 조항번호 및 조항제목.xlsx",
    )
    args = parser.parse_args()
    seed_standards_and_clauses(args.excel_path)
