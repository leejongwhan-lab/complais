"""iso_clauses_master — 스토리보드 조항 마스터 보장/시드/조회.

소스: `standard_clauses`(질문·체크포인트·kpi_refs) + 운영 14표준(CERTIFIABLE).
테이블이 없으면 CREATE TABLE IF NOT EXISTS 후 시드한다 (DROP/TRUNCATE 없음).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.data.standards_catalog import OPERATING_STANDARDS

logger = logging.getLogger(__name__)

# standard_clauses.standard_code (레거시 단축코드) → family
_LETTER_TO_FAMILY: Dict[str, str] = {
    "q": "QMS",
    "e": "EMS",
    "s": "OHSMS",
    "i": "ISMS",
    "ac": "ABMS",
    "co": "CMS",
    "en": "EnMS",
    "f": "FSMS",
    "m": "MDQMS",
    "nu": "NSMS",
    "pr": "PIMS",
    "ai": "AIMS",
}

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS iso_clauses_master (
  id INT NOT NULL AUTO_INCREMENT,
  standard_key VARCHAR(40) NOT NULL,
  family_code VARCHAR(20) NULL,
  clause_no VARCHAR(30) NOT NULL,
  clause_title VARCHAR(255) NOT NULL DEFAULT '',
  question TEXT NULL,
  default_kpi_list TEXT NULL,
  checkpoints TEXT NULL,
  group_name VARCHAR(100) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  source_standard_code VARCHAR(10) NULL,
  source_clause_id INT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_iso_clauses_std_clause (standard_key, clause_no),
  KEY ix_iso_clauses_master_standard_key (standard_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def _table_exists(db: Session, name: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t LIMIT 1"
        ),
        {"t": name},
    ).first()
    return bool(row)


def _column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return bool(row)


def _parse_kpi_refs(raw: Optional[str]) -> List[Dict[str, str]]:
    if not raw:
        return []
    out: List[Dict[str, str]] = []
    seen = set()
    for part in re.split(r"[,;\n|]+", str(raw)):
        key = part.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append({"key": key, "label": key})
    return out


def _family_letter(family: str) -> Optional[str]:
    for letter, fam in _LETTER_TO_FAMILY.items():
        if fam == family:
            return letter
    return None


def _clause_sort_key(clause_no: str) -> Tuple:
    parts = []
    for p in re.split(r"[.\-]", str(clause_no)):
        if p.isdigit():
            parts.append((0, int(p)))
        else:
            parts.append((1, p))
    return tuple(parts)


def ensure_iso_clauses_master(db: Session, *, force_resync: bool = False) -> int:
    """테이블 보장 + (비어 있으면) standard_clauses에서 시드. 반환: 행 수."""
    db.execute(text(_CREATE_SQL))
    if not _table_exists(db, "audit_note_clauses"):
        pass
    elif not _column_exists(db, "audit_note_clauses", "kpi_json"):
        try:
            db.execute(text("ALTER TABLE audit_note_clauses ADD COLUMN kpi_json TEXT NULL"))
            db.commit()
        except Exception:
            db.rollback()

    if not _table_exists(db, "standard_clauses"):
        db.commit()
        return 0

    count = db.execute(text("SELECT COUNT(*) FROM iso_clauses_master")).scalar() or 0
    if int(count) > 0 and not force_resync:
        return int(count)

    if force_resync and int(count) > 0:
        # Never TRUNCATE — delete only our seeded rows via full replace of content
        db.execute(text("DELETE FROM iso_clauses_master"))

    rows = db.execute(
        text(
            "SELECT id, clause_id, standard_code, group_name, label, question, "
            "checkpoints, kpi_refs, sort_order "
            "FROM standard_clauses ORDER BY sort_order, id"
        )
    ).mappings().all()

    by_letter: Dict[str, List[Any]] = {}
    for r in rows:
        code = (r["standard_code"] or "").strip().lower()
        by_letter.setdefault(code, []).append(r)

    common = by_letter.get("c", [])
    inserted = 0
    for std in OPERATING_STANDARDS:
        letter = _family_letter(std.family_code)
        specific = by_letter.get(letter or "", []) if letter else []
        # 2026판 등 전용 조항이 없으면 동일 family 레거시 조항 + 공통 사용
        merged: Dict[str, Any] = {}
        for src in list(common) + list(specific):
            cno = str(src["clause_id"] or "").strip()
            if not cno:
                continue
            merged[cno] = src
        ordered = sorted(merged.items(), key=lambda kv: _clause_sort_key(kv[0]))
        for idx, (cno, src) in enumerate(ordered):
            title = (src["label"] or "").strip() or cno
            # label often "4.1 조직과 …" — strip leading clause no
            m = re.match(r"^" + re.escape(cno) + r"\s*(.*)$", title)
            if m and m.group(1):
                title = m.group(1).strip()
            kpis = _parse_kpi_refs(src.get("kpi_refs"))
            db.execute(
                text(
                    "INSERT INTO iso_clauses_master "
                    "(standard_key, family_code, clause_no, clause_title, question, "
                    " default_kpi_list, checkpoints, group_name, sort_order, "
                    " source_standard_code, source_clause_id) "
                    "VALUES "
                    "(:standard_key, :family_code, :clause_no, :clause_title, :question, "
                    " :default_kpi_list, :checkpoints, :group_name, :sort_order, "
                    " :source_standard_code, :source_clause_id) "
                    "ON DUPLICATE KEY UPDATE "
                    " clause_title=VALUES(clause_title), question=VALUES(question), "
                    " default_kpi_list=VALUES(default_kpi_list), "
                    " checkpoints=VALUES(checkpoints), group_name=VALUES(group_name), "
                    " sort_order=VALUES(sort_order)"
                ),
                {
                    "standard_key": std.standard_key,
                    "family_code": std.family_code,
                    "clause_no": cno,
                    "clause_title": title[:255],
                    "question": src.get("question"),
                    "default_kpi_list": json.dumps(kpis, ensure_ascii=False) if kpis else None,
                    "checkpoints": src.get("checkpoints"),
                    "group_name": src.get("group_name"),
                    "sort_order": int(src.get("sort_order") or idx),
                    "source_standard_code": src.get("standard_code"),
                    "source_clause_id": src.get("id"),
                },
            )
            inserted += 1

    db.commit()
    final = db.execute(text("SELECT COUNT(*) FROM iso_clauses_master")).scalar() or 0
    logger.info("iso_clauses_master seeded rows≈%s total=%s", inserted, final)
    return int(final)


def list_operating_standards() -> List[Dict[str, Any]]:
    return [
        {
            "standard_key": s.standard_key,
            "family_code": s.family_code,
            "display_code": s.display_code,
            "name_ko": s.name_ko,
            "clauses_status": s.clauses_status,
        }
        for s in OPERATING_STANDARDS
    ]


def list_clauses_for_standard(db: Session, standard_key: str) -> List[Dict[str, Any]]:
    ensure_iso_clauses_master(db)
    rows = db.execute(
        text(
            "SELECT id, standard_key, family_code, clause_no, clause_title, question, "
            "default_kpi_list, checkpoints, group_name, sort_order "
            "FROM iso_clauses_master WHERE standard_key = :sk "
            "ORDER BY sort_order, id"
        ),
        {"sk": standard_key},
    ).mappings().all()
    out: List[Dict[str, Any]] = []
    for r in rows:
        kpis: List[Dict[str, str]] = []
        raw = r.get("default_kpi_list")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    kpis = parsed
            except Exception:
                kpis = _parse_kpi_refs(str(raw))
        checkpoints = _normalize_checkpoints(r.get("checkpoints"))
        out.append(
            {
                "id": r["id"],
                "standard_key": r["standard_key"],
                "family_code": r.get("family_code"),
                "clause_no": r["clause_no"],
                "clause_title": r["clause_title"] or "",
                "question": r.get("question") or "",
                "default_kpis": kpis,
                "checkpoints": checkpoints,
                "group_name": r.get("group_name"),
                "sort_order": r.get("sort_order") or 0,
            }
        )
    return out


def _normalize_checkpoints(raw: Any) -> List[Dict[str, str]]:
    if not raw:
        return []
    if isinstance(raw, list):
        data = raw
    else:
        try:
            data = json.loads(raw)
        except Exception:
            # plain text lines
            return [{"title": line.strip(), "hint": ""} for line in str(raw).splitlines() if line.strip()]
    out: List[Dict[str, str]] = []
    if not isinstance(data, list):
        return out
    for item in data:
        if isinstance(item, dict):
            out.append(
                {
                    "title": str(item.get("t") or item.get("title") or ""),
                    "hint": str(item.get("h") or item.get("hint") or ""),
                }
            )
        elif item:
            out.append({"title": str(item), "hint": ""})
    return out


def resolve_standard_key(raw: Optional[str]) -> Optional[str]:
    """계약/배정의 표준 문자열 → standard_key."""
    if not raw:
        return None
    text_val = str(raw).strip()
    if not text_val:
        return None
    upper = text_val.upper().replace(" ", "")
    for s in OPERATING_STANDARDS:
        if text_val == s.standard_key or upper == s.standard_key.upper():
            return s.standard_key
        if upper == s.family_code.upper():
            # family only → prefer READY edition of that family
            ready = [
                x
                for x in OPERATING_STANDARDS
                if x.family_code == s.family_code and x.clauses_status == "READY"
            ]
            return (ready[0] if ready else s).standard_key
        if s.display_code.replace(" ", "").upper() in upper or upper in s.display_code.replace(" ", "").upper():
            return s.standard_key
        digits = re.sub(r"\D", "", s.iso_number)
        if digits and digits in re.sub(r"\D", "", upper):
            return s.standard_key
    return None
