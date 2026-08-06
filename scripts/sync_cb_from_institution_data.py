"""Sync certification_bodies from institutionData master (UPDATE only).

- Does NOT DROP/TRUNCATE/DELETE certification_bodies or companies.
- Maps institutionData.idx → certification_bodies.id (both 70 rows).
- Optionally expands legacy cb_accreditation_scopes → cb_scope_matrix
  and UPSERTs scopes from data/cb_korea_seed.json when cb_code matches.

Usage:
  .venv/bin/python scripts/sync_cb_from_institution_data.py
  .venv/bin/python scripts/sync_cb_from_institution_data.py --with-scopes
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.database import SessionLocal

SEED_FILE = BASE_DIR / "data" / "cb_korea_seed.json"


def sync_cb_master(db) -> int:
    """institutionData → certification_bodies (UPDATE only, preserve ids).

    code 유니크 제약이 있으므로:
      1) 임시 코드로 치환
      2) idx=id 매칭 UPDATE
      3) institutionData에 없는 id(갭)에는 남은 institutionData(idx>max cb id)를 순서 매핑
    """
    db.execute(
        text(
            """
            UPDATE certification_bodies
            SET code = CONCAT('__tmp_', id),
                updated_at = UTC_TIMESTAMP()
            """
        )
    )
    result = db.execute(
        text(
            """
            UPDATE certification_bodies cb
            INNER JOIN `institutionData` i ON i.idx = cb.id
            SET
              cb.code = LEFT(NULLIF(TRIM(i.abbreviation), ''), 50),
              cb.name = LEFT(NULLIF(TRIM(i.korName), ''), 200),
              cb.name_en = LEFT(NULLIF(TRIM(i.engName), ''), 200),
              cb.cb_initial = LEFT(NULLIF(TRIM(i.abbreviation), ''), 20),
              cb.biz_no = LEFT(NULLIF(TRIM(i.bizNumber), ''), 30),
              cb.ceo_name = LEFT(NULLIF(TRIM(i.president), ''), 100),
              cb.address = LEFT(
                NULLIF(TRIM(CONCAT_WS(' ', i.address, i.detailAddress)), ''),
                500
              ),
              cb.tel = LEFT(NULLIF(TRIM(i.tel), ''), 50),
              cb.fax = LEFT(NULLIF(TRIM(i.fax), ''), 50),
              cb.website = LEFT(NULLIF(TRIM(i.homepage), ''), 300),
              cb.bank_name = LEFT(NULLIF(TRIM(i.bank), ''), 100),
              cb.account_no = LEFT(NULLIF(TRIM(i.bankAccount), ''), 50),
              cb.account_holder = LEFT(NULLIF(TRIM(i.depositor), ''), 100),
              cb.status = COALESCE(cb.status, '정상'),
              cb.is_active = 1,
              cb.updated_at = UTC_TIMESTAMP()
            WHERE i.korName IS NOT NULL AND TRIM(i.korName) <> ''
            """
        )
    )
    updated = int(result.rowcount or 0)

    # institutionData idx 갭(36,37,49 등) ↔ 남은 idx(71+) 매핑
    gap_ids = [
        r[0]
        for r in db.execute(
            text("SELECT id FROM certification_bodies WHERE code LIKE '\\_\\_tmp\\_%' ORDER BY id")
        ).all()
    ]
    extra_idx = [
        r[0]
        for r in db.execute(
            text(
                """
                SELECT i.idx FROM `institutionData` i
                LEFT JOIN certification_bodies cb ON cb.id = i.idx
                WHERE cb.id IS NULL
                ORDER BY i.idx
                """
            )
        ).all()
    ]
    for cb_id, inst_idx in zip(gap_ids, extra_idx):
        db.execute(
            text(
                """
                UPDATE certification_bodies cb
                INNER JOIN `institutionData` i ON i.idx = :inst_idx
                SET
                  cb.code = LEFT(NULLIF(TRIM(i.abbreviation), ''), 50),
                  cb.name = LEFT(NULLIF(TRIM(i.korName), ''), 200),
                  cb.name_en = LEFT(NULLIF(TRIM(i.engName), ''), 200),
                  cb.cb_initial = LEFT(NULLIF(TRIM(i.abbreviation), ''), 20),
                  cb.biz_no = LEFT(NULLIF(TRIM(i.bizNumber), ''), 30),
                  cb.ceo_name = LEFT(NULLIF(TRIM(i.president), ''), 100),
                  cb.address = LEFT(
                    NULLIF(TRIM(CONCAT_WS(' ', i.address, i.detailAddress)), ''),
                    500
                  ),
                  cb.tel = LEFT(NULLIF(TRIM(i.tel), ''), 50),
                  cb.fax = LEFT(NULLIF(TRIM(i.fax), ''), 50),
                  cb.website = LEFT(NULLIF(TRIM(i.homepage), ''), 300),
                  cb.status = COALESCE(cb.status, '정상'),
                  cb.is_active = 1,
                  cb.updated_at = UTC_TIMESTAMP()
                WHERE cb.id = :cb_id
                """
            ),
            {"inst_idx": inst_idx, "cb_id": cb_id},
        )
        updated += 1

    db.execute(
        text(
            """
            UPDATE certification_bodies
            SET code = CONCAT('CB', LPAD(id, 3, '0')),
                updated_at = UTC_TIMESTAMP()
            WHERE code LIKE '\\_\\_tmp\\_%'
            """
        )
    )
    db.commit()
    return updated


def expand_legacy_scopes_to_matrix(db) -> int:
    """cb_accreditation_scopes.iaf_codes CSV → cb_scope_matrix rows (INSERT IGNORE)."""
    rows = db.execute(
        text(
            """
            SELECT cb_id, standard_code, iaf_codes, is_active
            FROM cb_accreditation_scopes
            WHERE is_active = 1
            """
        )
    ).mappings().all()
    inserted = 0
    now = datetime.utcnow()
    for row in rows:
        std = (row["standard_code"] or "").strip()
        if not std:
            continue
        # normalize "ISO 9001:2015" → keep as-is for matrix
        codes = [c.strip() for c in (row["iaf_codes"] or "").split(",") if c.strip()]
        if not codes:
            codes = ["00"]
        for code in codes:
            code = code[:20]
            res = db.execute(
                text(
                    """
                    INSERT IGNORE INTO cb_scope_matrix
                      (cb_id, standard_code, iaf_code, is_active, created_at, updated_at)
                    VALUES
                      (:cb_id, :standard_code, :iaf_code, 1, :now, :now)
                    """
                ),
                {
                    "cb_id": int(row["cb_id"]),
                    "standard_code": std[:50],
                    "iaf_code": code,
                    "now": now,
                },
            )
            inserted += int(res.rowcount or 0)
    db.commit()
    return inserted


def upsert_scopes_from_seed(db) -> tuple[int, int]:
    """Match seed cb_code → certification_bodies.code; UPSERT matrix + standard_accreditations."""
    if not SEED_FILE.exists():
        return 0, 0
    items = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        items = items.get("cbs") or []

    code_to_id = {
        r[0]: r[1]
        for r in db.execute(text("SELECT code, id FROM certification_bodies")).all()
        if r[0]
    }

    now = datetime.utcnow()
    matrix_n = std_n = 0
    for item in items:
        code = (item.get("cb_code") or item.get("code") or "").strip()
        cb_id = code_to_id.get(code)
        if not cb_id:
            continue
        ab = (item.get("accreditation_body") or "").strip() or None
        reg_no = (item.get("reg_no") or "").strip() or None
        scopes = item.get("scopes") or []
        seen_std: set[str] = set()
        for sc in scopes:
            if not isinstance(sc, dict):
                continue
            std = (sc.get("standard_code") or "").strip()
            if not std:
                continue
            iaf = (sc.get("iaf_code") or sc.get("scope_code") or "").strip() or "00"
            iaf = iaf[:20]
            active = 1 if sc.get("is_active", True) else 0
            granted = sc.get("granted_date")
            expiry = sc.get("expiry_date")
            try:
                granted_d = date.fromisoformat(str(granted)) if granted else None
            except ValueError:
                granted_d = None
            try:
                expiry_d = date.fromisoformat(str(expiry)) if expiry else None
            except ValueError:
                expiry_d = None

            res = db.execute(
                text(
                    """
                    INSERT INTO cb_scope_matrix
                      (cb_id, standard_code, iaf_code, is_active, granted_date, expiry_date, created_at, updated_at)
                    VALUES
                      (:cb_id, :std, :iaf, :active, :granted, :expiry, :now, :now)
                    ON DUPLICATE KEY UPDATE
                      is_active = VALUES(is_active),
                      granted_date = COALESCE(VALUES(granted_date), granted_date),
                      expiry_date = COALESCE(VALUES(expiry_date), expiry_date),
                      updated_at = VALUES(updated_at)
                    """
                ),
                {
                    "cb_id": cb_id,
                    "std": std[:50],
                    "iaf": iaf,
                    "active": active,
                    "granted": granted_d,
                    "expiry": expiry_d,
                    "now": now,
                },
            )
            matrix_n += int(res.rowcount or 0)

            if std not in seen_std:
                seen_std.add(std)
                res2 = db.execute(
                    text(
                        """
                        INSERT INTO cb_standard_accreditations
                          (cb_id, standard_code, ab_code, registration_no, is_active, created_at, updated_at)
                        VALUES
                          (:cb_id, :std, :ab, :reg, 1, :now, :now)
                        ON DUPLICATE KEY UPDATE
                          ab_code = COALESCE(VALUES(ab_code), ab_code),
                          registration_no = COALESCE(VALUES(registration_no), registration_no),
                          is_active = 1,
                          updated_at = VALUES(updated_at)
                        """
                    ),
                    {
                        "cb_id": cb_id,
                        "std": std[:50],
                        "ab": (ab or "")[:30] or None,
                        "reg": (reg_no or "")[:100] or None,
                        "now": now,
                    },
                )
                std_n += int(res2.rowcount or 0)

            # legacy summary row (one per standard)
            db.execute(
                text(
                    """
                    INSERT INTO cb_accreditation_scopes
                      (cb_id, standard_code, standard_name, iaf_codes, use_nace, is_active, created_at, updated_at)
                    SELECT :cb_id, :std, :std, :iaf, 0, 1, :now, :now
                    FROM DUAL
                    WHERE NOT EXISTS (
                      SELECT 1 FROM cb_accreditation_scopes
                      WHERE cb_id = :cb_id AND standard_code = :std
                    )
                    """
                ),
                {"cb_id": cb_id, "std": std[:20], "iaf": iaf, "now": now},
            )

    db.commit()
    return matrix_n, std_n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-scopes", action="store_true", help="Also seed/expand scope tables")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        before = db.execute(
            text(
                "SELECT id, code, name FROM certification_bodies "
                "ORDER BY id DESC LIMIT 3"
            )
        ).all()
        print("[before top]", before)

        n = sync_cb_master(db)
        print(f"[ok] certification_bodies updated from institutionData: {n} rows")

        after = db.execute(
            text(
                "SELECT id, code, name FROM certification_bodies "
                "ORDER BY id ASC LIMIT 5"
            )
        ).all()
        print("[after sample]", after)
        dummy = db.execute(
            text(
                "SELECT COUNT(*) FROM certification_bodies "
                "WHERE name LIKE '%한국인증기관%' OR code REGEXP '^CB0[0-9]{2}$'"
            )
        ).scalar()
        print(f"[check] remaining dummy-like rows: {dummy}")

        if args.with_scopes:
            expanded = expand_legacy_scopes_to_matrix(db)
            print(f"[ok] expanded legacy scopes → matrix: {expanded}")
            m, s = upsert_scopes_from_seed(db)
            print(f"[ok] seed scopes upsert matrix≈{m} std_acc≈{s}")
            stats = db.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM cb_scope_matrix) AS matrix,
                      (SELECT COUNT(DISTINCT cb_id) FROM cb_scope_matrix) AS cbs_with_matrix,
                      (SELECT COUNT(*) FROM cb_standard_accreditations) AS std_acc,
                      (SELECT COUNT(*) FROM cb_accreditation_scopes) AS legacy
                    """
                )
            ).mappings().first()
            print("[scope stats]", dict(stats or {}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
