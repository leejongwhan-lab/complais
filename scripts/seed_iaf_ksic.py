"""Seed IAF / KSIC master data from storyboard Excel."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 프로젝트 루트 디렉터리를 sys.path에 자동 추가
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import pandas as pd
from sqlalchemy.orm import Session

# 이후 app 모듈 import
from app.core.database import Base, SessionLocal, engine
from app.models.master_data import IafCode, KsicCode, KsicIafMapping

DEFAULT_EXCEL = BASE_DIR / "스토리보드_0721.xlsx"


def seed_iaf_ksic_data(excel_path: str | Path = DEFAULT_EXCEL) -> None:
    excel_path = Path(excel_path)
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # 1. IAF/KSIC 관련 테이블만 생성 (전체 모델 메타데이터와 충돌 방지)
    Base.metadata.create_all(
        bind=engine,
        tables=[
            IafCode.__table__,
            KsicCode.__table__,
            KsicIafMapping.__table__,
        ],
    )
    db: Session = SessionLocal()

    try:
        # 2. 엑셀 두 번째 시트 읽기
        df = pd.read_excel(excel_path, sheet_name=1, skiprows=1)
        df.columns = [
            "iaf_code",
            "iaf_name_kr",
            "iaf_name_en",
            "sub_code",
            "ksic_list",
            "qms_complexity",
            "ems_complexity",
            "ohsms_complexity",
        ]
        df_clean = df.dropna(subset=["iaf_code"]).copy()

        print("[...] IAF / KSIC data seed starting...")

        iaf_cache: dict[str, IafCode] = {}
        ksic_cache: dict[str, KsicCode] = {}
        seen_mappings: set[tuple[int, int]] = set()

        for _, row in df_clean.iterrows():
            try:
                iaf_num = int(row["iaf_code"])
            except (ValueError, TypeError):
                continue

            iaf_code_str = f"{iaf_num:02d}"
            sub_code = str(row["sub_code"]).strip() if pd.notna(row["sub_code"]) else f"{iaf_code_str}A"
            iaf_name_kr = str(row["iaf_name_kr"]).strip()
            iaf_name_en = str(row["iaf_name_en"]).strip()

            qms_comp = str(row["qms_complexity"]).strip() if pd.notna(row["qms_complexity"]) else None
            ems_comp = str(row["ems_complexity"]).strip() if pd.notna(row["ems_complexity"]) else None
            ohsms_comp = str(row["ohsms_complexity"]).strip() if pd.notna(row["ohsms_complexity"]) else None

            # 1) IAF 마스터 데이터 get-or-create (code = sub_code, 예: '01A')
            iaf_obj = iaf_cache.get(sub_code)
            if iaf_obj is None:
                iaf_obj = db.query(IafCode).filter(IafCode.code == sub_code).first()
                if not iaf_obj:
                    iaf_obj = IafCode(code=sub_code, name_ko=iaf_name_kr, name_en=iaf_name_en)
                    db.add(iaf_obj)
                    db.flush()
                iaf_cache[sub_code] = iaf_obj

            # 2) KSIC 코드 파싱 및 매핑 생성
            raw_ksic = str(row["ksic_list"]) if pd.notna(row["ksic_list"]) else ""
            cleaned_ksic = raw_ksic.replace("\n", " ").replace(".", ",").replace(" ", "")
            raw_items = [k.strip() for k in cleaned_ksic.split(",") if k.strip()]

            # 셀에 "20129(핵연료가공업과관련된산업은제외)"처럼 콤마 없이 괄호 설명이
            # 붙은 경우가 있어, 앞쪽 숫자 코드만 추출하고 나머지는 버린다.
            ksic_items: list[str] = []
            for raw_item in raw_items:
                m = re.match(r"^(\d{2,10})", raw_item)
                if not m:
                    print(f"[WARN] KSIC 코드로 인식할 수 없어 건너뜀: '{raw_item}'")
                    continue
                ksic_items.append(m.group(1))

            for k_code in ksic_items:
                # KSIC 마스터 get-or-create
                ksic_obj = ksic_cache.get(k_code)
                if ksic_obj is None:
                    ksic_obj = db.query(KsicCode).filter(KsicCode.code == k_code).first()
                    if not ksic_obj:
                        ksic_obj = KsicCode(code=k_code, name_ko="", digit_level=len(k_code))
                        db.add(ksic_obj)
                        db.flush()
                    ksic_cache[k_code] = ksic_obj

                # 매핑 저장 (KSIC <-> IAF, 심사 복잡도 포함)
                map_key = (ksic_obj.id, iaf_obj.id)
                if map_key not in seen_mappings:
                    mapping_obj = (
                        db.query(KsicIafMapping)
                        .filter(
                            KsicIafMapping.ksic_id == ksic_obj.id,
                            KsicIafMapping.iaf_id == iaf_obj.id,
                        )
                        .first()
                    )
                    if not mapping_obj:
                        mapping_obj = KsicIafMapping(
                            ksic_id=ksic_obj.id,
                            iaf_id=iaf_obj.id,
                            qms_complexity=qms_comp,
                            ems_complexity=ems_comp,
                            ohsms_complexity=ohsms_comp,
                        )
                        db.add(mapping_obj)
                    seen_mappings.add(map_key)

        db.commit()
        print("[OK] IAF-KSIC master data and mapping seed completed.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed IAF/KSIC master data from Excel")
    parser.add_argument(
        "excel_path",
        nargs="?",
        default=str(DEFAULT_EXCEL),
        help="Path to 스토리보드_0721.xlsx",
    )
    args = parser.parse_args()
    seed_iaf_ksic_data(args.excel_path)
