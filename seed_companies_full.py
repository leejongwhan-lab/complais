"""기업 마스터 전체 시드 (대량 입고).

Usage:
  # (선택) 외부 DB 사용 시 환경변수 설정
  # export DATABASE_URL="postgresql://user:pass@localhost:5432/complais"

  python seed_companies_full.py
  python seed_companies_full.py --file data/companies_full.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# DATABASE_URL이 셸에 export 되어 있으면 pydantic-settings가 우선 사용한다.
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.company import Companies


STRING_LIMITS = {
    "company_no": 50, "cert_no": 50, "name": 200, "name_en": 200, "biz_no": 30,
    "corp_no": 20, "ceo_name": 100, "biz_type": 100, "biz_class": 100,
    "address": 500, "detail_address": 255, "address_en": 500, "tel": 50,
    "email": 200, "website": 300, "iaf_code": 255, "ksic_code": 255,
    "scope_kr": 1000, "scope_en": 1000, "entity_type": 50, "status": 20,
    "tax_contact_name": 100, "tax_email": 100,
}


DEFAULT_CANDIDATES = [
    BASE_DIR / "data" / "companies_full.json",
    BASE_DIR / "data" / "companies_full.csv",
    BASE_DIR / "companies_full.json",
    BASE_DIR / "companies_full.csv",
    BASE_DIR / "스토리보드_0721.xlsx",
]

FIELD_ALIASES = {
    "company_name_kr": "name",
    "company_name_en": "name_en",
    "조직명(K)": "name",
    "조직명(E)": "name_en",
    "기업명(국문)": "name",
    "기업명(영문)": "name_en",
    "biz_reg_num": "biz_no",
    "사업자등록번호": "biz_no",
    "법인등록번호": "corp_no",
    "대표자명": "ceo_name",
    "business_type": "biz_type",
    "업태": "biz_type",
    "business_item": "biz_class",
    "종목": "biz_class",
    "address_kr": "address",
    "주소": "address",
    "상세주소": "detail_address",
    "KSIC": "ksic_code",
    "ksic_codes": "ksic_codes",
    "iaf_codes": "iaf_codes",
    "CODE(1)": "iaf_code",
    "전화번호": "tel",
    "이메일": "email",
    "홈페이지": "website",
    "상태": "status",
}


def _as_str(value) -> str | None:
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def _normalize_row(raw: dict) -> dict | None:
    data: dict = {}
    for key, value in raw.items():
        mapped = FIELD_ALIASES.get(str(key), str(key))
        text = _as_str(value)
        if text is None:
            continue
        data[mapped] = text

    if isinstance(data.get("ksic_codes"), list):
        data["ksic_code"] = ",".join(str(x) for x in data.pop("ksic_codes"))
    if isinstance(data.get("iaf_codes"), list):
        data["iaf_code"] = ",".join(str(x) for x in data.pop("iaf_codes"))

    for key in ("ksic_code", "iaf_code"):
        val = data.get(key)
        if isinstance(val, str) and val.startswith("["):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    data[key] = ",".join(str(x) for x in parsed)
            except json.JSONDecodeError:
                pass

    name = data.get("name")
    if not name or name in {"조직명(K)", "가져오기", "입력", "설명"}:
        return None

    data.setdefault("employee_count", 0)
    data.setdefault("is_active", True)
    data.setdefault("status", "정상")

    # employee_count / is_active 타입 보정
    try:
        data["employee_count"] = int(float(data["employee_count"]))
    except (TypeError, ValueError):
        data["employee_count"] = 0
    if isinstance(data["is_active"], str):
        data["is_active"] = data["is_active"].lower() in {"1", "true", "y", "yes", "활성", "정상"}

    allowed = {
        "company_no", "cert_no", "name", "name_en", "biz_no", "corp_no", "ceo_name",
        "biz_type", "biz_class", "address", "detail_address", "address_en", "tel",
        "email", "website", "iaf_code", "ksic_code", "employee_count", "scope_kr",
        "scope_en", "is_active", "entity_type", "headcount_regular",
        "headcount_non_regular", "headcount_outsourced", "headcount_certified",
        "status", "tax_contact_name", "tax_email",
    }
    cleaned = {k: v for k, v in data.items() if k in allowed}
    for k, lim in STRING_LIMITS.items():
        if k in cleaned and isinstance(cleaned[k], str):
            cleaned[k] = cleaned[k][:lim]
    return cleaned


def _load_from_excel(path: Path) -> list[dict]:
    import pandas as pd

    rows: list[dict] = []
    xl = pd.ExcelFile(path)
    # 고객리스트 시트 우선
    sheet = "기관 고객리스트 관리파일 예"
    if sheet not in xl.sheet_names:
        sheet = xl.sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet)
    for _, row in df.iterrows():
        normalized = _normalize_row(row.to_dict())
        if normalized:
            rows.append(normalized)
    return rows


def _load_rows(file_path: Path) -> list[dict]:
    suffix = file_path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return _load_from_excel(file_path)
    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        items = payload if isinstance(payload, list) else payload.get("companies", [])
        return [r for r in (_normalize_row(x) for x in items) if r]
    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            return [r for r in (_normalize_row(x) for x in csv.DictReader(f)) if r]
    raise ValueError(f"지원하지 않는 파일 형식: {suffix}")


def _resolve_source(explicit: Path | None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(f"시드 파일을 찾을 수 없습니다: {explicit}")
        return explicit
    for candidate in DEFAULT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "시드 파일이 없습니다. data/companies_full.csv|json 또는 스토리보드_0721.xlsx 를 준비하세요."
    )


def _upsert_company(db: Session, data: dict) -> bool:
    now = datetime.utcnow()
    existing = None
    if data.get("biz_no"):
        existing = db.query(Companies).filter(Companies.biz_no == data["biz_no"]).first()
    if existing is None:
        existing = db.query(Companies).filter(Companies.name == data["name"]).first()

    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = now
        return False

    db.add(Companies(**data, created_at=now, updated_at=now))
    return True


def seed_companies_full(file_path: Path | None = None) -> None:
    source = _resolve_source(file_path)
    rows = _load_rows(source)

    # 이름/사업자번호 기준 중복 제거 (마지막 행 우선)
    dedup: dict[str, dict] = {}
    for row in rows:
        key = row.get("biz_no") or f"name:{row['name']}"
        dedup[key] = row
    rows = list(dedup.values())

    print(f"[...] Companies full seed starting...")
    print(f"    DATABASE_URL host/db <- {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print(f"    source: {source} ({len(rows)} rows after dedupe)")

    db: Session = SessionLocal()
    created = 0
    updated = 0
    try:
        for idx, row in enumerate(rows, start=1):
            if _upsert_company(db, row):
                created += 1
            else:
                updated += 1
            if idx % 200 == 0:
                db.commit()
                print(f"    ... progress {idx}/{len(rows)}")
        db.commit()
        total = created + updated
        print(f"✅ DB 입고 완료! 신규 등록: {created}건, 기존 업데이트: {updated}건 (총 {total}건)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기업 마스터 전체 DB 시드")
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="companies_full.csv|json 또는 스토리보드 xlsx (미지정 시 기본 경로 탐색)",
    )
    args = parser.parse_args()
    if os.getenv("DATABASE_URL"):
        print(f"[env] DATABASE_URL override detected")
    seed_companies_full(args.file)
