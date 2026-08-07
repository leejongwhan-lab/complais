"""심사계획서(audit_plans / audit_plan_items) → 심사노트 스코프.

- Non-lead: only plan items assigned to the auditor
- Lead + team_meeting: union of all plan items for the engagement
- Empty plan: empty clause set (never dump full master to everyone)
- NC autofill: auditor name + dept/process from matching plan item
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_LEAD_ROLES = {
    "lead",
    "lead_auditor",
    "team_lead",
    "teamleader",
    "팀장",
    "심사팀장",
    "lead auditor",
}


def _table_exists(db: Session, name: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=:t LIMIT 1"
        ),
        {"t": name},
    ).first()
    return bool(row)


def _column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=:t AND column_name=:c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return bool(row)


def ensure_audit_plan_item_columns(db: Session) -> None:
    """Runtime additive columns for plan scoping (safe if already migrated)."""
    if not _table_exists(db, "audit_plan_items"):
        return
    cols = {
        "auditor_id": "INT NULL",
        "process_group_id": "VARCHAR(50) NULL",
        "clause_no": "VARCHAR(40) NULL",
        "dept": "VARCHAR(120) NULL",
        "standard_code": "VARCHAR(30) NULL",
        "standard_key": "VARCHAR(40) NULL",
    }
    for col, ddl in cols.items():
        if _column_exists(db, "audit_plan_items", col):
            continue
        try:
            db.execute(text(f"ALTER TABLE audit_plan_items ADD COLUMN {col} {ddl}"))
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
            logger.exception("ensure audit_plan_items.%s failed", col)


def _is_lead_role(raw: Optional[str]) -> bool:
    if not raw:
        return False
    key = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
    if key in _LEAD_ROLES or key == "lead":
        return True
    # Korean / mixed
    s = str(raw).strip()
    return s in {"LEAD", "팀장", "심사팀장"} or "lead" in key


def is_lead_auditor(db: Session, *, contract_id: int, auditor_id: int) -> bool:
    """Detect 심사팀장 via contracts.lead_auditor_id or assignment role."""
    if _table_exists(db, "contracts"):
        try:
            row = db.execute(
                text("SELECT lead_auditor_id FROM contracts WHERE id=:id LIMIT 1"),
                {"id": contract_id},
            ).first()
            if row and row[0] is not None and int(row[0]) == int(auditor_id):
                return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    if _table_exists(db, "audit_assignments"):
        try:
            rows = db.execute(
                text(
                    "SELECT role, assignment_role FROM audit_assignments "
                    "WHERE contract_id=:cid AND auditor_id=:aid"
                ),
                {"cid": contract_id, "aid": auditor_id},
            ).mappings().all()
            for r in rows:
                if _is_lead_role(r.get("role")) or _is_lead_role(r.get("assignment_role")):
                    return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    if _table_exists(db, "audit_application_assignments"):
        try:
            rows = db.execute(
                text(
                    "SELECT role FROM audit_application_assignments "
                    "WHERE contract_id=:cid AND auditor_id=:aid"
                ),
                {"cid": contract_id, "aid": auditor_id},
            ).mappings().all()
            for r in rows:
                if _is_lead_role(r.get("role")):
                    return True
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    return False


def get_plan_id_for_contract(db: Session, contract_id: int) -> Optional[int]:
    if not _table_exists(db, "audit_plans"):
        return None
    row = db.execute(
        text(
            "SELECT id FROM audit_plans WHERE contract_id=:cid "
            "ORDER BY "
            "CASE status WHEN 'confirmed' THEN 0 WHEN 'sent' THEN 1 ELSE 2 END, "
            "id DESC LIMIT 1"
        ),
        {"cid": contract_id},
    ).first()
    return int(row[0]) if row else None


def _extract_clause_tokens(raw: Optional[str]) -> List[str]:
    """Pull clause numbers from free-text standard_clause (e.g. '4.1, 4.2 / 6.1')."""
    if not raw:
        return []
    found = re.findall(r"\b\d+(?:\.\d+[A-Za-z]*)+(?:/\d+(?:\.\d+[A-Za-z]*)+)*\b", str(raw))
    out: List[str] = []
    seen: Set[str] = set()
    for f in found:
        t = f.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def list_plan_items(
    db: Session,
    *,
    plan_id: int,
    auditor_id: Optional[int] = None,
    auditor_name: Optional[str] = None,
    all_auditors: bool = False,
) -> List[Dict[str, Any]]:
    """Load plan items; filter by auditor unless all_auditors (팀장 전체)."""
    ensure_audit_plan_item_columns(db)
    if not _table_exists(db, "audit_plan_items"):
        return []

    has_aid = _column_exists(db, "audit_plan_items", "auditor_id")
    has_pg = _column_exists(db, "audit_plan_items", "process_group_id")
    has_cno = _column_exists(db, "audit_plan_items", "clause_no")
    has_dept = _column_exists(db, "audit_plan_items", "dept")
    has_scode = _column_exists(db, "audit_plan_items", "standard_code")
    has_skey = _column_exists(db, "audit_plan_items", "standard_key")

    cols = [
        "id",
        "audit_plan_id",
        "time_slot",
        "process_name",
        "standard_clause",
        "auditee_name",
        "location_name",
        "auditor_name",
        "note",
        "sort_order",
    ]
    if has_aid:
        cols.append("auditor_id")
    if has_pg:
        cols.append("process_group_id")
    if has_cno:
        cols.append("clause_no")
    if has_dept:
        cols.append("dept")
    if has_scode:
        cols.append("standard_code")
    if has_skey:
        cols.append("standard_key")

    sql = f"SELECT {', '.join(cols)} FROM audit_plan_items WHERE audit_plan_id=:pid"
    params: Dict[str, Any] = {"pid": plan_id}
    if not all_auditors:
        clauses = []
        if has_aid and auditor_id is not None:
            clauses.append("auditor_id = :aid")
            params["aid"] = int(auditor_id)
        if auditor_name:
            clauses.append("auditor_name = :aname")
            params["aname"] = str(auditor_name).strip()
        if clauses:
            sql += " AND (" + " OR ".join(clauses) + ")"
        elif auditor_id is not None:
            # Columns missing and no name — cannot match; return empty (strict scope)
            return []
    sql += " ORDER BY sort_order IS NULL, sort_order, id"

    try:
        rows = [dict(r) for r in db.execute(text(sql), params).mappings().all()]
    except Exception:
        logger.exception("list_plan_items failed plan_id=%s", plan_id)
        try:
            db.rollback()
        except Exception:
            pass
        return []
    return rows


def plan_scope_keys(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive filter sets from plan items."""
    clause_nos: Set[str] = set()
    process_group_ids: Set[str] = set()
    process_names: Set[str] = set()
    standard_keys: Set[str] = set()
    standard_codes: Set[str] = set()
    for it in items:
        cno = (it.get("clause_no") or "").strip()
        if cno:
            clause_nos.add(cno)
        for tok in _extract_clause_tokens(it.get("standard_clause")):
            clause_nos.add(tok)
        pg = (it.get("process_group_id") or "").strip()
        if pg:
            process_group_ids.add(pg)
        pn = (it.get("process_name") or "").strip()
        if pn:
            process_names.add(pn)
        sk = (it.get("standard_key") or "").strip()
        if sk:
            standard_keys.add(sk)
        sc = (it.get("standard_code") or "").strip()
        if sc:
            standard_codes.add(sc)
    return {
        "clause_nos": clause_nos,
        "process_group_ids": process_group_ids,
        "process_names": process_names,
        "standard_keys": standard_keys,
        "standard_codes": standard_codes,
        "item_count": len(items),
    }


def _clause_field(clause: Any, *names: str) -> str:
    for name in names:
        if isinstance(clause, dict):
            val = clause.get(name)
        else:
            val = getattr(clause, name, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


def _items_for_clause_standard(
    items: List[Dict[str, Any]], clause: Any
) -> List[Dict[str, Any]]:
    """Prefer plan items whose standard_key/code matches the clause's standard."""
    sk = _clause_field(clause, "standard_key")
    sc = _clause_field(clause, "standard_code")
    if not sk and not sc:
        return items
    matched = []
    generic = []
    for it in items:
        isk = (it.get("standard_key") or "").strip()
        isc = (it.get("standard_code") or "").strip()
        if not isk and not isc:
            generic.append(it)
            continue
        if (sk and isk and isk == sk) or (sc and isc and isc == sc):
            matched.append(it)
            continue
        # family soft-match e.g. QMS_2015 vs ISO9001 handled by caller keys
        if sk and isk and sk.split("_")[0].upper() == isk.split("_")[0].upper():
            matched.append(it)
    return matched if matched else generic


def clause_matches_plan(
    clause: Any,
    scope: Dict[str, Any],
    *,
    items: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """True if clause is covered by plan scope (clause_no or process group/name)."""
    if items is not None:
        relevant = _items_for_clause_standard(items, clause)
        scope = plan_scope_keys(relevant)
    if not scope or not scope.get("item_count"):
        return False
    cno = _clause_field(clause, "clause_no")
    pgid = _clause_field(clause, "process_group_id")
    pgname = _clause_field(clause, "process_group_name", "group_name")

    if cno and cno in scope["clause_nos"]:
        return True
    # prefix match for combined clauses e.g. plan 8.2 vs clause 8.2/8.3
    if cno:
        for p in scope["clause_nos"]:
            if (
                cno == p
                or cno.startswith(p + ".")
                or cno.startswith(p + "/")
                or p.startswith(cno + "/")
            ):
                return True
    if pgid and pgid in scope["process_group_ids"]:
        return True
    if pgname and pgname in scope["process_names"]:
        return True
    return False


def filter_clauses_by_plan(clauses: List[Any], items: List[Dict[str, Any]]) -> List[Any]:
    if not items:
        return []
    scope = plan_scope_keys(items)
    if not scope["item_count"]:
        return []
    # If items only name processes/clauses with no usable keys, still empty
    if not (
        scope["clause_nos"]
        or scope["process_group_ids"]
        or scope["process_names"]
    ):
        return []
    return [c for c in clauses if clause_matches_plan(c, scope, items=items)]


def resolve_plan_autofill(
    items: List[Dict[str, Any]],
    *,
    clause_no: Optional[str] = None,
    process_group_id: Optional[str] = None,
    process_group_name: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Pick dept / process label for NC modal from best matching plan item."""
    if not items:
        return {"dept": None, "process": None, "auditor_name": None}

    def score(it: Dict[str, Any]) -> int:
        s = 0
        cno = (it.get("clause_no") or "").strip()
        tokens = set(_extract_clause_tokens(it.get("standard_clause")))
        if clause_no:
            if cno == clause_no or clause_no in tokens:
                s += 100
            elif cno and (clause_no.startswith(cno) or cno.startswith(clause_no.split("/")[0])):
                s += 60
        pg = (it.get("process_group_id") or "").strip()
        if process_group_id and pg and pg == process_group_id:
            s += 40
        pn = (it.get("process_name") or "").strip()
        if process_group_name and pn and pn == process_group_name:
            s += 30
        return s

    ranked = sorted(items, key=score, reverse=True)
    best = ranked[0]
    if score(best) <= 0:
        # fallback: first item with any dept/process
        for it in items:
            if (it.get("dept") or it.get("process_name") or it.get("location_name")):
                best = it
                break

    dept = (
        (best.get("dept") or "").strip()
        or (best.get("process_name") or "").strip()
        or (best.get("location_name") or "").strip()
        or None
    )
    process = (best.get("process_name") or "").strip() or None
    return {
        "dept": dept,
        "process": process,
        "auditor_name": (best.get("auditor_name") or "").strip() or None,
    }


def load_engagement_plan_scope(
    db: Session,
    *,
    contract_id: int,
    auditor_id: int,
    auditor_name: Optional[str] = None,
    team_meeting: bool = False,
) -> Dict[str, Any]:
    """Full scope payload for session/matrix.

    Returns:
      plan_id, is_lead, team_meeting, plan_empty, items, scope
    """
    ensure_audit_plan_item_columns(db)
    is_lead = is_lead_auditor(db, contract_id=contract_id, auditor_id=auditor_id)
    # Only leads may request team_meeting full coverage
    tm = bool(team_meeting and is_lead)
    plan_id = get_plan_id_for_contract(db, contract_id)
    if not plan_id:
        return {
            "plan_id": None,
            "is_lead": is_lead,
            "team_meeting": tm,
            "plan_empty": True,
            "items": [],
            "scope": plan_scope_keys([]),
            "scope_mode": "no_plan",
        }
    items = list_plan_items(
        db,
        plan_id=plan_id,
        auditor_id=auditor_id,
        auditor_name=auditor_name,
        all_auditors=tm,
    )
    # If lead in team meeting but no items at all on plan → empty
    # If non-lead has no personal items → empty (even if others have items)
    return {
        "plan_id": plan_id,
        "is_lead": is_lead,
        "team_meeting": tm,
        "plan_empty": len(items) == 0,
        "items": items,
        "scope": plan_scope_keys(items),
        "scope_mode": "team_meeting" if tm else "assigned",
    }
