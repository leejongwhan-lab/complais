"""한국 CB 마스터 시드 — data/cb_korea_seed.json → certification_bodies

ORM 모델에만 있고 DB에 없는 컬럼(phone 등)은 건드리지 않고,
실제 MySQL 컬럼만 INSERT/UPDATE 한다.

Usage:
  python scripts/seed_cb_korea.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal

DEFAULT_FILE = BASE_DIR / "data" / "cb_korea_seed.json"

# 실제 MySQL certification_bodies 컬럼 (SHOW COLUMNS 기준)
ALLOWED = {
    "code",
    "name",
    "cb_initial",
    "cb_type",
    "name_en",
    "accreditation",
    "address",
    "tel",
    "email",
    "website",
    "logo_path",
    "is_active",
    "activated_at",
    "created_at",
    "updated_at",
    "ceo_name",
    "biz_no",
    "corp_no",
    "personal_no",
    "fax",
    "bank_name",
    "account_no",
    "account_holder",
    "doc_rule_contract",
    "doc_rule_report",
    "doc_rule_ncr",
    "fee_per_md",
    "fee_travel",
    "fee_cert",
    "max_consecutive",
    "impartiality_cycle_months",
    "reg_no",
}


def _scopes_text(scopes) -> str | None:
    if not scopes:
        return None
    if isinstance(scopes, str):
        return scopes[:300]
    if isinstance(scopes, list):
        parts = []
        for s in scopes:
            if isinstance(s, dict):
                parts.append(
                    str(
                        s.get("standard_code")
                        or s.get("iaf_code")
                        or s.get("code")
                        or s.get("name")
                        or ""
                    )
                )
            else:
                parts.append(str(s))
        joined = ", ".join(p for p in parts if p)
        return joined[:300] if joined else None
    return str(scopes)[:300]


def _row_payload(row: dict) -> dict | None:
    now = datetime.utcnow()
    code = (row.get("cb_code") or row.get("code") or "").strip()
    name = (row.get("cb_name") or row.get("name") or "").strip()
    if not name:
        return None
    if not code:
        code = f"CB-{abs(hash(name)) % 10_000_000:07d}"

    status_raw = (row.get("status") or "정상").strip()
    is_active = 1 if status_raw not in {"정지", "취소", "inactive", "suspended"} else 0

    # accreditation 컬럼에 인정기구+등록번호 요약 저장 (확장 컬럼 없음)
    accred_bits = [
        row.get("accreditation_body") or row.get("accreditation"),
        row.get("reg_no"),
        _scopes_text(row.get("scopes")),
    ]
    accreditation = " | ".join(str(x) for x in accred_bits if x)

    payload = {
        "code": code[:50],
        "name": name[:200],
        "cb_initial": (row.get("cb_initial") or None),
        "cb_type": "certification",
        "name_en": (row.get("cb_name_en") or row.get("name_en") or None),
        "accreditation": accreditation[:100] if accreditation else None,
        "address": (row.get("address") or None),
        "tel": (row.get("tel") or row.get("phone") or None),
        "email": (row.get("email") or None),
        "website": (row.get("website") or None),
        "is_active": is_active,
        "activated_at": now if is_active else None,
        "created_at": now,
        "updated_at": now,
        "ceo_name": (row.get("ceo_name") or None),
        "biz_no": (row.get("biz_reg_no") or row.get("biz_no") or None),
        "reg_no": (row.get("reg_no") or None),
        "fee_per_md": Decimal("0"),
        "fee_travel": Decimal("0"),
        "fee_cert": Decimal("0"),
        "max_consecutive": 3,
        "impartiality_cycle_months": 12,
    }
    if payload["cb_initial"]:
        payload["cb_initial"] = str(payload["cb_initial"])[:20]
    for key in ("tel", "email", "website", "ceo_name", "biz_no", "reg_no", "address", "name_en"):
        if payload.get(key):
            # soft length guard via column sizes
            limits = {
                "tel": 50,
                "email": 200,
                "website": 300,
                "ceo_name": 100,
                "biz_no": 30,
                "reg_no": 50,
                "address": 500,
                "name_en": 200,
            }
            payload[key] = str(payload[key])[: limits[key]]
    return {k: v for k, v in payload.items() if k in ALLOWED}


def seed_cb_korea(file_path: Path | None = None) -> None:
    source = file_path or DEFAULT_FILE
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else data.get("cbs") or []

    print("[...] CB Korea seed starting...")
    print(
        f"    DATABASE_URL host/db <- "
        f"{settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}"
    )
    print(f"    source: {source} ({len(rows)} rows)")

    db = SessionLocal()
    created = updated = 0
    try:
        for row in rows:
            payload = _row_payload(row)
            if not payload:
                continue
            existing = db.execute(
                text(
                    "SELECT id FROM certification_bodies "
                    "WHERE code = :code OR name = :name "
                    "OR (:biz_no IS NOT NULL AND biz_no = :biz_no) LIMIT 1"
                ),
                {
                    "code": payload["code"],
                    "name": payload["name"],
                    "biz_no": payload.get("biz_no"),
                },
            ).first()

            if existing:
                sets = ", ".join(
                    f"{k} = :{k}"
                    for k in payload
                    if k not in {"code", "created_at"}
                )
                params = {**payload, "id": existing[0]}
                db.execute(
                    text(f"UPDATE certification_bodies SET {sets} WHERE id = :id"),
                    params,
                )
                updated += 1
            else:
                cols = ", ".join(payload.keys())
                binds = ", ".join(f":{k}" for k in payload.keys())
                db.execute(
                    text(
                        f"INSERT INTO certification_bodies ({cols}) VALUES ({binds})"
                    ),
                    payload,
                )
                created += 1
        db.commit()
        print(f"✅ CB 입고 완료! 신규 {created}건, 업데이트 {updated}건 (총 {created + updated}건)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=None)
    args = parser.parse_args()
    seed_cb_korea(args.file)
