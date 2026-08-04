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
from app.models.standard import StandardClause, StandardMaster

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

        # Row 1에서 15개 표준 헤더 추출
        raw_standards = df.iloc[1, 2:].values
        clean_df.columns = ["clause_number"] + list(raw_standards)
        clean_df = clean_df.dropna(subset=["clause_number"]).reset_index(drop=True)

        print(f"[START] 총 {len(raw_standards)}개 표준 데이터 시딩 시작...\n")

        for std_text in raw_standards:
            std_text_str = str(std_text).strip()

            # 표준 코드 및 이름 분리 (예: 'ISO 9001:2015 품질경영시스템' -> 'ISO 9001:2015', '품질경영시스템')
            m = re.match(r"^(ISO(?:/IEC)?\s+[\d\-:]+)\s+(.+)$", std_text_str)
            if m:
                code, name = m.group(1), m.group(2)
            else:
                code, name = std_text_str, std_text_str

            # 연도 추출
            year_match = re.search(r":(\d{4})", code)
            year = int(year_match.group(1)) if year_match else 2026

            # 1. StandardMaster 생성 또는 조회 (Upsert)
            std_master = db.query(StandardMaster).filter_by(standard_code=code).first()
            if not std_master:
                std_master = StandardMaster(
                    standard_code=code,
                    standard_name=name,
                    version_year=year,
                    is_active=True,
                    description="2026년 신규 발행 예정 표준 (조항 대기)" if "2026" in code else None,
                )
                db.add(std_master)
                db.flush()
                print(f"[NEW] StandardMaster 신규 등록: {code} ({name})")

            # 2. 해당 표준의 세부 조항 파싱 & 저장
            clause_rows = clean_df[["clause_number", std_text]].dropna()
            clause_rows = clause_rows[clause_rows[std_text] != "-"]

            added_count = 0
            for idx, row in clause_rows.iterrows():
                c_num = str(row["clause_number"]).strip()
                c_title = str(row[std_text]).strip()

                # 뎁스 계산 (예: 4 -> 1, 4.1 -> 2, 4.4.1 -> 3)
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
            print(f"  -> {code}: 총 {added_count}개 조항 저장 완료.")

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
