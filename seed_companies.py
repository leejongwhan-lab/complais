"""기업 마스터 시드 스크립트.

Usage:
  python seed_companies.py
  python seed_companies.py --file companies.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.company import Companies

# 기본 내장 시드 (파일 미지정 시)
SEED_COMPANIES = [
    {
        "name": "㈜ 앨파스",
        "name_en": "ALFAS Co., Ltd.",
        "biz_no": "609-81-57236",
        "ceo_name": "김원수",
        "biz_type": "제조, 부동산업",
        "biz_class": "볼트, 스크류",
        "ksic_code": "2594",
        "iaf_code": "17B",
        "address": "경상남도 함안군...",
        "status": "정상",
        "employee_count": 0,
        "is_active": True,
    },
]

FIELD_ALIASES = {
    "company_name_kr": "name",
    "company_name_en": "name_en",
    "biz_reg_num": "biz_no",
    "business_type": "biz_type",
    "business_item": "biz_class",
    "address_kr": "address",
}


def _normalize_row(raw: dict) -> dict:
    data: dict = {}
    for key, value in raw.items():
        if value is None or value == "":
            continue
        mapped = FIELD_ALIASES.get(key, key)
        data[mapped] = value

    # 배열 코드 → 콤마 문자열
    if isinstance(data.get("ksic_codes"), list):
        data["ksic_code"] = ",".join(str(x) for x in data.pop("ksic_codes"))
    if isinstance(data.get("iaf_codes"), list):
        data["iaf_code"] = ",".join(str(x) for x in data.pop("iaf_codes"))
    data.pop("ksic_codes", None)
    data.pop("iaf_codes", None)

    # 문자열로 들어온 배열 처리: '["2594"]'
    for src, dest in (("ksic_code", "ksic_code"), ("iaf_code", "iaf_code")):
        val = data.get(src)
        if isinstance(val, str) and val.startswith("["):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    data[dest] = ",".join(str(x) for x in parsed)
            except json.JSONDecodeError:
                pass

    data.setdefault("employee_count", 0)
    data.setdefault("is_active", True)
    data.setdefault("status", "정상")

    allowed = {
        "company_no", "cert_no", "name", "name_en", "biz_no", "corp_no", "ceo_name",
        "biz_type", "biz_class", "address", "detail_address", "address_en", "tel",
        "email", "website", "iaf_code", "ksic_code", "employee_count", "scope_kr",
        "scope_en", "is_active", "entity_type", "headcount_regular",
        "headcount_non_regular", "headcount_outsourced", "headcount_certified",
        "status", "tax_contact_name", "tax_email",
    }
    return {k: v for k, v in data.items() if k in allowed}


def _load_rows(file_path: Path | None) -> list[dict]:
    if file_path is None:
        return SEED_COMPANIES

    if not file_path.exists():
        raise FileNotFoundError(f"시드 파일을 찾을 수 없습니다: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("companies", [])
        return [_normalize_row(r) for r in rows]

    if suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [_normalize_row(r) for r in reader]

    raise ValueError("지원 형식: .json, .csv")


def _upsert_company(db: Session, data: dict) -> bool:
    """biz_no(또는 name) 기준 upsert. True=신규, False=업데이트."""
    now = datetime.utcnow()
    existing = None
    if data.get("biz_no"):
        existing = db.query(Companies).filter(Companies.biz_no == data["biz_no"]).first()
    if existing is None and data.get("name"):
        existing = db.query(Companies).filter(Companies.name == data["name"]).first()

    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = now
        return False

    company = Companies(**data, created_at=now, updated_at=now)
    db.add(company)
    return True


def seed_companies(file_path: Path | None = None) -> None:
    rows = _load_rows(file_path)
    db: Session = SessionLocal()
    created = 0
    updated = 0
    try:
        print("[...] Companies seed starting...")
        for row in rows:
            if not row.get("name"):
                continue
            is_new = _upsert_company(db, row)
            if is_new:
                created += 1
            else:
                updated += 1
        db.commit()
        total = created + updated
        print(f"✅ DB 입고 완료! 신규 등록: {created}건, 기존 업데이트: {updated}건 (총 {total}건)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="기업 마스터 DB 시드")
    parser.add_argument("--file", type=Path, default=None, help="companies.json 또는 companies.csv")
    args = parser.parse_args()
    seed_companies(args.file)
