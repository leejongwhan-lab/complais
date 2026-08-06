"""Sync StandardMaster/StandardClause from Excel and link StandardProcess<->StandardClause mappings.

기존 scripts/seed_standards.py 시딩 결과에 더해, 아이콘 없는 표준 프로세스 프레임워크
(PROCESS_DEFINITIONS)를 Upsert하고 조항 번호 규칙에 따라 ProcessClauseMapping을 동기화한다.
"""
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
from app.models.standard import ProcessClauseMapping, StandardClause, StandardMaster, StandardProcess

# 엑셀 파일은 backend 프로젝트 루트가 아닌 상위(워크스페이스) 루트에 위치.
_CANDIDATE_PATHS = [
    BASE_DIR / "표준 별 조항번호 및 조항제목.xlsx",
    BASE_DIR.parent.parent / "표준 별 조항번호 및 조항제목.xlsx",
]
DEFAULT_EXCEL = next((p for p in _CANDIDATE_PATHS if p.exists()), _CANDIDATE_PATHS[0])

# 아이콘 제거된 순수 표준 프로세스 프레임워크 (언제든지 수정 가능)
PROCESS_DEFINITIONS = [
    {"code": "PRC_MGMT", "name": "경영 및 전략 프로세스", "desc": "리더십, 방침, 전략, 조직 상황, 경영검토", "clauses": ["4.1", "4.2", "4.3", "5.1", "5.2", "5.3", "9.1", "9.3"]},
    {"code": "PRC_RISK", "name": "기획 및 리스크 관리 프로세스", "desc": "리스크 및 기회 평가, 목표 수립, 준수의무", "clauses": ["6.1", "6.2", "6.3"]},
    {"code": "PRC_SUPPORT", "name": "지원 및 자원 관리 프로세스", "desc": "인적자원, 역량, 인프라, 문서화된 정보, 의사소통", "clauses": ["7.1", "7.2", "7.3", "7.4", "7.5"]},
    {"code": "PRC_OPERATION", "name": "운용 통제 및 실현 프로세스", "desc": "기획, 요구사항 검토, 설계, 구매, 생산 및 서비스 제공", "clauses": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.6", "8.7"]},
    {"code": "PRC_SAFETY_ENV", "name": "환경 및 안전보건 특화 프로세스", "desc": "환경측면, 위험성평가, 비상대응, 근로자 협의", "clauses": ["5.4", "6.1.2", "6.1.3", "8.1.1", "8.1.2", "8.1.3", "8.1.4", "8.2"]},
    {"code": "PRC_EVAL_IMPROVE", "name": "성과 평가 및 개선 프로세스", "desc": "모니터링, 내부심사, 부적합 및 시정조치, 지속적 개선", "clauses": ["9.1", "9.2", "9.3", "10.1", "10.2", "10.3"]},
]


def sync_standards_from_excel(excel_path: str | Path = DEFAULT_EXCEL) -> None:
    excel_path = Path(excel_path)
    if not excel_path.exists():
        print(f"[ERROR] 엑셀 파일 부재: {excel_path}")
        return

    db: Session = SessionLocal()
    try:
        # 1. 프로세스 마스터 동기화 (Upsert)
        print("[1/3] 프로세스 마스터 동기화 중 (아이콘 제거)...")
        proc_map = {}
        for idx, p_def in enumerate(PROCESS_DEFINITIONS, 1):
            proc = db.query(StandardProcess).filter_by(process_code=p_def["code"]).first()
            if not proc:
                proc = StandardProcess(
                    process_code=p_def["code"],
                    process_name_kr=p_def["name"],
                    description=p_def["desc"],
                    sort_order=idx,
                )
                db.add(proc)
                db.flush()
            else:
                proc.process_name_kr = p_def["name"]
                proc.description = p_def["desc"]
                proc.sort_order = idx
            proc_map[p_def["code"]] = proc

        # 2. 엑셀 파싱 및 표준/조항 동기화
        print("[2/3] 엑셀 15개 표준 정식 조항 파싱 및 DB 동기화...")
        df = pd.read_excel(excel_path)
        clean_df = df.iloc[2:].copy().drop(columns=["Unnamed: 0"])
        raw_standards = df.iloc[1, 2:].values
        clean_df.columns = ["clause_number"] + list(raw_standards)
        clean_df = clean_df.dropna(subset=["clause_number"]).reset_index(drop=True)

        for std_text in raw_standards:
            std_text_str = str(std_text).strip()
            m = re.match(r"^(ISO(?:/IEC)?\s+[\d\-:]+)\s+(.+)$", std_text_str)
            code, name = (m.group(1), m.group(2)) if m else (std_text_str, std_text_str)
            year_match = re.search(r":(\d{4})", code)
            year = int(year_match.group(1)) if year_match else 2026

            std_master = db.query(StandardMaster).filter_by(standard_code=code).first()
            if not std_master:
                std_master = StandardMaster(
                    standard_code=code,
                    standard_name=name,
                    version_year=year,
                    is_active=True,
                )
                db.add(std_master)
                db.flush()

            clause_rows = clean_df[["clause_number", std_text]].dropna()
            clause_rows = clause_rows[clause_rows[std_text] != "-"]

            print(f"[3/3] {code}: 조항/프로세스 매핑 동기화 중 (아이콘 제거)...")
            for idx, row in clause_rows.iterrows():
                c_num = str(row["clause_number"]).strip()
                c_title = str(row[std_text]).strip()

                clause_obj = db.query(StandardClause).filter_by(
                    standard_id=std_master.id,
                    clause_number=c_num,
                ).first()

                if not clause_obj:
                    clause_obj = StandardClause(
                        standard_id=std_master.id,
                        clause_number=c_num,
                        clause_title_kr=c_title,
                        depth=len(c_num.split(".")),
                        sort_order=idx + 1,
                    )
                    db.add(clause_obj)
                    db.flush()
                else:
                    # 기존 데이터가 있으면 엑셀 원본 내용으로 수정/갱신
                    clause_obj.clause_title_kr = c_title
                    clause_obj.depth = len(c_num.split("."))

                # 3. 프로세스 연계 동기화
                for p_def in PROCESS_DEFINITIONS:
                    proc_obj = proc_map[p_def["code"]]
                    if any(c_num == target_c or c_num.startswith(target_c + ".") for target_c in p_def["clauses"]):
                        mapping = db.query(ProcessClauseMapping).filter_by(
                            process_id=proc_obj.id,
                            clause_id=clause_obj.id,
                        ).first()
                        if not mapping:
                            db.add(ProcessClauseMapping(process_id=proc_obj.id, clause_id=clause_obj.id))

        db.commit()
        print("[DONE] 15개 표준 조항 엑셀 정확 매핑 및 수정 가능 DB 시딩 완료!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] 오류 발생: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync StandardProcess<->StandardClause mappings from Excel")
    parser.add_argument(
        "excel_path",
        nargs="?",
        default=str(DEFAULT_EXCEL),
        help="Path to 표준 별 조항번호 및 조항제목.xlsx",
    )
    args = parser.parse_args()
    sync_standards_from_excel(args.excel_path)
