"""Seed IAF / KSIC master data from storyboard Excel."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.models.iaf_ksic import IafCode, KsicCode, KsicIafLink

DEFAULT_EXCEL = Path(__file__).resolve().parent.parent / "스토리보드_0721.xlsx"


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
            KsicIafLink.__table__,
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

        seen_sub_codes: set[str] = set()
        seen_ksic_codes: set[str] = set()
        seen_mappings: set[tuple[str, str]] = set()

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

            # 1) IAF 마스터 데이터 Insert / Update
            if sub_code not in seen_sub_codes:
                iaf_obj = db.query(IafCode).filter(IafCode.sub_code == sub_code).first()
                if not iaf_obj:
                    iaf_obj = IafCode(
                        sub_code=sub_code,
                        iaf_code=iaf_code_str,
                        name_kr=iaf_name_kr,
                        name_en=iaf_name_en,
                        qms_complexity=qms_comp,
                        ems_complexity=ems_comp,
                        ohsms_complexity=ohsms_comp,
                    )
                    db.add(iaf_obj)
                seen_sub_codes.add(sub_code)

            # 2) KSIC 코드 파싱 및 매핑 생성
            raw_ksic = str(row["ksic_list"]) if pd.notna(row["ksic_list"]) else ""
            cleaned_ksic = raw_ksic.replace("\n", " ").replace(".", ",").replace(" ", "")
            ksic_items = [k.strip() for k in cleaned_ksic.split(",") if k.strip()]

            for k_code in ksic_items:
                # KSIC 마스터 저장
                if k_code not in seen_ksic_codes:
                    ksic_obj = db.query(KsicCode).filter(KsicCode.ksic_code == k_code).first()
                    if not ksic_obj:
                        ksic_obj = KsicCode(ksic_code=k_code, name_kr="")
                        db.add(ksic_obj)
                    seen_ksic_codes.add(k_code)

                # 매핑 저장
                map_key = (k_code, sub_code)
                if map_key not in seen_mappings:
                    mapping_obj = (
                        db.query(KsicIafLink)
                        .filter(
                            KsicIafLink.ksic_code == k_code,
                            KsicIafLink.sub_code == sub_code,
                        )
                        .first()
                    )
                    if not mapping_obj:
                        mapping_obj = KsicIafLink(
                            ksic_code=k_code,
                            sub_code=sub_code,
                            is_primary=True,
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
