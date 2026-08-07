"""심사계획서 + 심사결과보고서 aggregation — contract_id pipeline.

Source of truth: MySQL masters / transactional tables
  standard_master, contracts, companies, audit_plans, audit_plan_items,
  audit_notes, audit_note_clauses, audit_note_ncr
Reference PHP/HTML files are UX-only — do not hardcode catalogs.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.auditor import Auditor
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.enums import UsersRole
from app.schemas.auditor_audit_plans import (
    PLAN_STANDARD_CODE_ORDER,
    AuditPlanContractInfo,
    AuditPlanOut,
    AuditPlanSaveIn,
    AuditPlanSaveOut,
    AuditPlanScheduleItem,
    AuditPlanTeamMember,
    AuditReportAggregateOut,
    AuditReportClauseRow,
    AuditReportMatrixCell,
    AuditReportNcrRow,
)
from app.services.audit_plan_scope import (
    ensure_audit_plan_item_columns,
    get_plan_id_for_contract,
    list_plan_items,
)
from app.services.process_group_masters import (
    list_clauses_for_standard_pg,
    list_standard_masters_pg,
    to_process_standard_code,
)
from app.services.iso_clauses_master import resolve_standard_key
from app.data.standards_catalog import format_standard_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["Auditor Audit Plans"])

_CLAUSE_RE = re.compile(
    r"\b\d+(?:\.\d+[A-Za-z]*)+(?:/\d+(?:\.\d+[A-Za-z]*)+)*\b"
)


def _require_auditor(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.AUDITOR.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="심사원 계정만 이용할 수 있습니다.",
        )
    return current_user


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


def _get_auditor(db: Session, user_id: int) -> Auditor:
    auditor = db.query(Auditor).filter(Auditor.user_id == user_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 프로필이 없습니다.",
        )
    return auditor


def _ymd(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    return s[:10] if s else None


def _parse_json_list(raw: Any) -> List[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass
    return [p.strip() for p in re.split(r"[,;]+", s) if p.strip()]


def _parse_id_list(raw: Any) -> List[int]:
    out: List[int] = []
    for x in _parse_json_list(raw):
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def _official_standards_from_db(db: Session) -> List[Dict[str, str]]:
    """Chip list for plan UI — labels from standard_master only."""
    rows = list_standard_masters_pg(db)
    by_code = {
        str(r.get("standard_code") or "").strip().upper(): r for r in rows if r.get("standard_code")
    }
    ordered: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for code in PLAN_STANDARD_CODE_ORDER:
        key = code.upper()
        r = by_code.get(key)
        if not r:
            continue
        seen.add(key)
        name = str(r.get("standard_name") or code).strip()
        digits = re.sub(r"\D", "", code)[-5:] or code
        ordered.append(
            {
                "code": code,
                "label": name,
                "short": digits,
                "standard_key": resolve_standard_key(code) or code,
            }
        )
    # Append any other master codes not in preferred list (still DB-sourced)
    for code, r in sorted(by_code.items()):
        if code in seen:
            continue
        name = str(r.get("standard_name") or code).strip()
        digits = re.sub(r"\D", "", code)[-5:] or code
        ordered.append(
            {
                "code": code,
                "label": name,
                "short": digits,
                "standard_key": resolve_standard_key(code) or code,
            }
        )
    return ordered


def _normalize_standard_tokens(raw_list: List[Any]) -> Tuple[List[str], List[str], List[str]]:
    """Return (display_labels, standard_codes, standard_keys) from mixed inputs."""
    labels: List[str] = []
    codes: List[str] = []
    keys: List[str] = []
    seen_c: Set[str] = set()
    for raw in raw_list:
        if isinstance(raw, dict):
            token = (
                raw.get("standard_code")
                or raw.get("code")
                or raw.get("standard_key")
                or raw.get("standard")
                or ""
            )
            label = raw.get("label") or raw.get("name") or str(token)
        else:
            token = str(raw or "").strip()
            label = token
        if not token:
            continue
        code = to_process_standard_code(token) or ""
        if not code:
            # try digit extract → ISO####
            m = re.search(
                r"(9001|14001|45001|50001|22000|27001|37001|37301|22301|42001|19443|27701)",
                token,
            )
            if m:
                code = f"ISO{m.group(1)}"
        if not code:
            continue
        code = code.upper()
        if code in seen_c:
            continue
        seen_c.add(code)
        sk = resolve_standard_key(code) or code
        codes.append(code)
        keys.append(sk)
        labels.append(format_standard_label(sk) or label or code)
    return labels, codes, keys


def _auditor_names(db: Session, ids: List[int]) -> Dict[int, str]:
    if not ids:
        return {}
    rows = db.query(Auditor.id, Auditor.name).filter(Auditor.id.in_(ids)).all()
    return {int(r.id): (r.name or f"#{r.id}") for r in rows}


def _load_contract_bundle(db: Session, contract_id: int) -> Tuple[Contracts, AuditPlanContractInfo]:
    if not _table_exists(db, "contracts"):
        raise HTTPException(status_code=404, detail="계약 테이블이 없습니다.")
    contract = db.query(Contracts).filter(Contracts.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    company = None
    if contract.company_id and _table_exists(db, "companies"):
        company = db.query(Companies).filter(Companies.id == contract.company_id).first()

    cb_name = None
    if contract.cb_id and _table_exists(db, "certification_bodies"):
        cb = (
            db.query(CertificationBodies)
            .filter(CertificationBodies.id == contract.cb_id)
            .first()
        )
        if cb:
            cb_name = cb.name

    labels, codes, keys = _normalize_standard_tokens(
        _parse_json_list(getattr(contract, "standards", None))
        or _parse_json_list(getattr(contract, "applied_standards", None))
    )
    lead_id = int(contract.lead_auditor_id) if contract.lead_auditor_id else None
    member_ids = _parse_id_list(getattr(contract, "member_auditor_ids", None))
    name_map = _auditor_names(db, ([lead_id] if lead_id else []) + member_ids)
    addr = None
    if company:
        parts = [p for p in [company.address, getattr(company, "detail_address", None)] if p]
        addr = " ".join(parts) if parts else None

    info = AuditPlanContractInfo(
        contract_id=int(contract.id),
        company_id=int(contract.company_id) if contract.company_id else None,
        company_name=(company.name if company else None),
        biz_no=(company.biz_no if company else None),
        address=addr,
        scope_kr=getattr(contract, "scope_kr", None)
        or (getattr(company, "scope_kr", None) if company else None),
        standards=labels,
        standards_codes=codes,
        standards_keys=keys,
        audit_type=getattr(contract, "audit_type", None),
        audit_period_start=_ymd(getattr(contract, "audit_period_start", None)),
        audit_period_end=_ymd(getattr(contract, "audit_period_end", None)),
        lead_auditor_id=lead_id,
        lead_auditor_name=name_map.get(lead_id) if lead_id else None,
        member_auditor_ids=member_ids,
        cb_name=cb_name,
    )
    return contract, info


def _team_from_contract(info: AuditPlanContractInfo, db: Session) -> List[AuditPlanTeamMember]:
    team: List[AuditPlanTeamMember] = []
    if info.lead_auditor_id:
        team.append(
            AuditPlanTeamMember(
                role="leader",
                name=info.lead_auditor_name or "",
                auditor_id=info.lead_auditor_id,
                desc="심사팀장",
            )
        )
    names = _auditor_names(db, info.member_auditor_ids)
    for mid in info.member_auditor_ids:
        team.append(
            AuditPlanTeamMember(
                role="auditor",
                name=names.get(mid, f"#{mid}"),
                auditor_id=mid,
                desc="심사원",
            )
        )
    return team


def _deep_link(contract_id: int, *, report: bool = False) -> str:
    base = f"/auditor-portal?tab=reports&contract={int(contract_id)}"
    if report:
        return base + "&view=report"
    return base


def _load_plan_row(db: Session, contract_id: int) -> Optional[Dict[str, Any]]:
    if not _table_exists(db, "audit_plans"):
        return None
    row = db.execute(
        text(
            "SELECT * FROM audit_plans WHERE contract_id=:cid "
            "ORDER BY "
            "CASE status WHEN 'confirmed' THEN 0 WHEN 'sent' THEN 1 ELSE 2 END, "
            "id DESC LIMIT 1"
        ),
        {"cid": contract_id},
    ).mappings().first()
    return dict(row) if row else None


def _items_out(db: Session, plan_id: int) -> List[AuditPlanScheduleItem]:
    ensure_audit_plan_item_columns(db)
    rows = list_plan_items(db, plan_id=plan_id, all_auditors=True)
    out: List[AuditPlanScheduleItem] = []
    for r in rows:
        out.append(
            AuditPlanScheduleItem(
                time_slot=r.get("time_slot"),
                process_name=r.get("process_name"),
                standard_clause=r.get("standard_clause"),
                clause_no=r.get("clause_no"),
                auditee_name=r.get("auditee_name"),
                location_name=r.get("location_name"),
                auditor_name=r.get("auditor_name"),
                auditor_id=r.get("auditor_id"),
                dept=r.get("dept"),
                process_group_id=r.get("process_group_id"),
                standard_code=r.get("standard_code"),
                standard_key=r.get("standard_key"),
                note=r.get("note"),
                sort_order=r.get("sort_order"),
            )
        )
    return out


@router.get("/audit-plans/{contract_id}", response_model=AuditPlanOut)
def get_audit_plan(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Load plan header from contracts/companies + audit_plans/items; standards from master."""
    _require_auditor(current_user)
    _get_auditor(db, current_user.id)
    _, info = _load_contract_bundle(db, contract_id)
    plan = _load_plan_row(db, contract_id)
    plan_id = int(plan["id"]) if plan else None
    items = _items_out(db, plan_id) if plan_id else []
    team = _team_from_contract(info, db)

    return AuditPlanOut(
        plan_id=plan_id,
        contract_id=contract_id,
        status=(plan.get("status") if plan else None),
        plan_date=_ymd(plan.get("plan_date")) if plan else None,
        audit_objective=plan.get("audit_objective") if plan else None,
        audit_criteria=plan.get("audit_criteria") if plan else None,
        scope_summary=plan.get("scope_summary") if plan else info.scope_kr,
        confirmed_at=str(plan["confirmed_at"])[:19] if plan and plan.get("confirmed_at") else None,
        contract=info,
        team=team,
        items=items,
        official_standards=_official_standards_from_db(db),
        notes_deep_link=_deep_link(contract_id),
        reports_deep_link=_deep_link(contract_id, report=True),
    )


def _resolve_auditor_id_by_name(db: Session, name: Optional[str], cache: Dict[str, Optional[int]]) -> Optional[int]:
    key = (name or "").strip()
    if not key:
        return None
    if key in cache:
        return cache[key]
    row = db.execute(
        text("SELECT id FROM auditors WHERE name=:n LIMIT 1"),
        {"n": key},
    ).first()
    cache[key] = int(row[0]) if row else None
    return cache[key]


def _extract_clause_no(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    m = _CLAUSE_RE.search(str(raw))
    return m.group(0) if m else None


@router.put("/audit-plans/{contract_id}", response_model=AuditPlanSaveOut)
def save_audit_plan(
    contract_id: int,
    payload: AuditPlanSaveIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Persist confirmed plan → audit_plans + audit_plan_items; optionally update contract roster/standards."""
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)
    contract, _info = _load_contract_bundle(db, contract_id)

    if not _table_exists(db, "audit_plans") or not _table_exists(db, "audit_plan_items"):
        raise HTTPException(status_code=500, detail="audit_plans 테이블이 없습니다.")

    ensure_audit_plan_item_columns(db)
    labels, codes, keys = _normalize_standard_tokens(payload.standards or [])
    if not codes:
        # fall back to contract standards
        labels, codes, keys = _normalize_standard_tokens(
            _parse_json_list(getattr(contract, "standards", None))
        )

    # Resolve lead / members from payload.team if ids missing
    lead_id = payload.lead_auditor_id
    member_ids = list(payload.member_auditor_ids or [])
    name_cache: Dict[str, Optional[int]] = {}
    if payload.team:
        for m in payload.team:
            aid = m.auditor_id or _resolve_auditor_id_by_name(db, m.name, name_cache)
            role = (m.role or "").lower()
            if role in {"leader", "lead", "lead_auditor", "team_leader", "팀장", "심사팀장"}:
                if aid and not lead_id:
                    lead_id = aid
            elif role in {"auditor", "member", "심사원"} and aid:
                if aid not in member_ids and aid != lead_id:
                    member_ids.append(aid)

    status_val = (payload.status or "confirmed").strip() or "confirmed"
    criteria = payload.audit_criteria or (", ".join(labels) if labels else None)
    plan_date = None
    if payload.plan_date:
        try:
            plan_date = date.fromisoformat(payload.plan_date[:10])
        except Exception:
            plan_date = None

    existing = _load_plan_row(db, contract_id)
    now = datetime.utcnow()
    confirmed_sql = ", confirmed_at=NOW()" if status_val == "confirmed" else ""

    if existing:
        plan_id = int(existing["id"])
        db.execute(
            text(
                f"UPDATE audit_plans SET status=:st, plan_date=:pd, "
                f"audit_objective=:obj, audit_criteria=:crit, scope_summary=:scope, "
                f"updated_at=NOW(){confirmed_sql} WHERE id=:id"
            ),
            {
                "st": status_val,
                "pd": plan_date,
                "obj": payload.audit_objective,
                "crit": criteria,
                "scope": payload.scope_summary,
                "id": plan_id,
            },
        )
        db.execute(
            text("DELETE FROM audit_plan_items WHERE audit_plan_id=:pid"),
            {"pid": plan_id},
        )
    else:
        db.execute(
            text(
                "INSERT INTO audit_plans "
                "(contract_id, status, plan_date, audit_objective, audit_criteria, "
                "scope_summary, created_by, created_at, updated_at, confirmed_at) "
                "VALUES (:cid, :st, :pd, :obj, :crit, :scope, :by, NOW(), NOW(), "
                + ("NOW()" if status_val == "confirmed" else "NULL")
                + ")"
            ),
            {
                "cid": contract_id,
                "st": status_val,
                "pd": plan_date,
                "obj": payload.audit_objective,
                "crit": criteria,
                "scope": payload.scope_summary,
                "by": auditor.id,
            },
        )
        plan_id = int(
            db.execute(text("SELECT LAST_INSERT_ID()")).scalar() or 0
        )
        if not plan_id:
            row = db.execute(
                text(
                    "SELECT id FROM audit_plans WHERE contract_id=:cid ORDER BY id DESC LIMIT 1"
                ),
                {"cid": contract_id},
            ).first()
            plan_id = int(row[0]) if row else 0

    # Insert schedule items
    has_aid = _column_exists(db, "audit_plan_items", "auditor_id")
    has_pg = _column_exists(db, "audit_plan_items", "process_group_id")
    has_cno = _column_exists(db, "audit_plan_items", "clause_no")
    has_dept = _column_exists(db, "audit_plan_items", "dept")
    has_scode = _column_exists(db, "audit_plan_items", "standard_code")
    has_skey = _column_exists(db, "audit_plan_items", "standard_key")

    default_code = codes[0] if codes else None
    default_key = keys[0] if keys else None
    item_count = 0
    for idx, it in enumerate(payload.items or []):
        aname = (it.auditor_name or "").strip() or None
        aid = it.auditor_id or _resolve_auditor_id_by_name(db, aname, name_cache)
        clause_no = (it.clause_no or "").strip() or _extract_clause_no(
            it.standard_clause or it.process_name or it.note
        )
        scode = (it.standard_code or "").strip() or default_code
        if scode:
            scode = to_process_standard_code(scode) or scode
        skey = (it.standard_key or "").strip() or (
            resolve_standard_key(scode) if scode else default_key
        )
        cols = [
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
        vals = [
            ":pid",
            ":ts",
            ":pn",
            ":sc",
            ":an",
            ":loc",
            ":aud",
            ":note",
            ":so",
        ]
        params: Dict[str, Any] = {
            "pid": plan_id,
            "ts": (it.time_slot or "")[:50] or None,
            "pn": (it.process_name or "")[:255] or None,
            "sc": (it.standard_clause or (clause_no or ""))[:120] or None,
            "an": (it.auditee_name or "")[:120] or None,
            "loc": (it.location_name or "")[:120] or None,
            "aud": aname,
            "note": it.note,
            "so": it.sort_order if it.sort_order is not None else idx + 1,
        }
        if has_aid:
            cols.append("auditor_id")
            vals.append(":aid")
            params["aid"] = aid
        if has_pg:
            cols.append("process_group_id")
            vals.append(":pg")
            params["pg"] = (it.process_group_id or "")[:50] or None
        if has_cno:
            cols.append("clause_no")
            vals.append(":cno")
            params["cno"] = (clause_no or "")[:40] or None
        if has_dept:
            cols.append("dept")
            vals.append(":dept")
            params["dept"] = (it.dept or it.process_name or "")[:120] or None
        if has_scode:
            cols.append("standard_code")
            vals.append(":scode")
            params["scode"] = (scode or "")[:30] or None
        if has_skey:
            cols.append("standard_key")
            vals.append(":skey")
            params["skey"] = (skey or "")[:40] or None

        db.execute(
            text(
                f"INSERT INTO audit_plan_items ({', '.join(cols)}) "
                f"VALUES ({', '.join(vals)})"
            ),
            params,
        )
        item_count += 1

    if payload.update_contract_roster:
        updates = ["updated_at=NOW()"]
        params_c: Dict[str, Any] = {"cid": contract_id}
        if lead_id:
            updates.append("lead_auditor_id=:lead")
            params_c["lead"] = int(lead_id)
        if member_ids is not None:
            updates.append("member_auditor_ids=:mids")
            params_c["mids"] = json.dumps(member_ids, ensure_ascii=False)
        if codes:
            # Store master codes + human labels for downstream notes filter
            updates.append("standards=:stds")
            params_c["stds"] = json.dumps(labels or codes, ensure_ascii=False)
            if _column_exists(db, "contracts", "applied_standards"):
                updates.append("applied_standards=:astds")
                params_c["astds"] = json.dumps(codes, ensure_ascii=False)
        db.execute(
            text(f"UPDATE contracts SET {', '.join(updates)} WHERE id=:cid"),
            params_c,
        )

    db.commit()
    return AuditPlanSaveOut(
        ok=True,
        plan_id=plan_id,
        contract_id=contract_id,
        item_count=item_count,
        status=status_val,
        message="심사계획서가 저장되었습니다.",
        notes_deep_link=_deep_link(contract_id),
        reports_deep_link=_deep_link(contract_id, report=True),
    )


# ─── Result report aggregation (② 조항 / ③ NCR / ⑤ 매트릭스) ───────────────


def _verdict_kr(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    mapping = {
        "ok": "적합",
        "적합": "적합",
        "minor": "경부적합",
        "경미한부적합": "경부적합",
        "경부적합": "경부적합",
        "major": "중부적합",
        "중대한부적합": "중부적합",
        "중부적합": "중부적합",
        "obs": "관찰사항",
        "observation": "관찰사항",
        "관찰사항": "관찰사항",
    }
    return mapping.get(str(v).strip(), str(v).strip())


def _ncr_bucket(grade: Optional[str]) -> str:
    g = (grade or "").strip().lower()
    if g in {"major", "중대한부적합", "중부적합"}:
        return "major"
    if g in {"minor", "경미한부적합", "경부적합"}:
        return "minor"
    return "obs"


@router.get(
    "/audit-reports/{contract_id}",
    response_model=AuditReportAggregateOut,
)
def get_audit_report_aggregate(
    contract_id: int,
    team_meeting: bool = Query(False, description="팀장 — 매트릭스 전체 스코프"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Live 심사결과보고서 payload from saved notes + plan roster (no stubs)."""
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)
    _, info = _load_contract_bundle(db, contract_id)

    plan = _load_plan_row(db, contract_id)
    plan_id = int(plan["id"]) if plan else None

    note_id = None
    if _table_exists(db, "audit_notes"):
        nrow = db.execute(
            text(
                "SELECT id FROM audit_notes WHERE contract_id=:cid ORDER BY id DESC LIMIT 1"
            ),
            {"cid": contract_id},
        ).first()
        note_id = int(nrow[0]) if nrow else None

    # ② clauses
    clauses: List[AuditReportClauseRow] = []
    if note_id and _table_exists(db, "audit_note_clauses"):
        has_seq = _column_exists(db, "audit_note_clauses", "note_seq")
        has_scode = _column_exists(db, "audit_note_clauses", "standard_code")
        has_topic = _column_exists(db, "audit_note_clauses", "clause_topic")
        cols = [
            "clause_id",
            "standard",
            "clause_label",
            "verdict",
            "finding",
            "evidence",
        ]
        if has_seq:
            cols.append("note_seq")
        if has_scode:
            cols.append("standard_code")
        if has_topic:
            cols.append("clause_topic")
        rows = db.execute(
            text(
                f"SELECT {', '.join(cols)} FROM audit_note_clauses "
                "WHERE note_id=:nid ORDER BY standard, clause_id, "
                + ("note_seq," if has_seq else "")
                + " id"
            ),
            {"nid": note_id},
        ).mappings().all()
        for r in rows:
            label = (
                (r.get("clause_topic") if has_topic else None)
                or r.get("clause_label")
                or r.get("clause_id")
            )
            note_txt = (r.get("finding") or r.get("evidence") or "") or None
            clauses.append(
                AuditReportClauseRow(
                    clause_no=str(r.get("clause_id") or ""),
                    standard=str(r.get("standard") or ""),
                    standard_code=(r.get("standard_code") if has_scode else None),
                    clause_label=label,
                    verdict=_verdict_kr(r.get("verdict")),
                    note=note_txt,
                    note_seq=int(r["note_seq"]) if has_seq and r.get("note_seq") else 1,
                )
            )

    # ③ NCRs
    ncrs: List[AuditReportNcrRow] = []
    if note_id and _table_exists(db, "audit_note_ncr"):
        nrows = db.execute(
            text(
                "SELECT id, grade, clause, standard, title, description, requirement, "
                "due_date, status, auditor_name, dept FROM audit_note_ncr "
                "WHERE note_id=:nid AND status != 'closed' ORDER BY id"
            ),
            {"nid": note_id},
        ).mappings().all()
        for n in nrows:
            ncrs.append(
                AuditReportNcrRow(
                    id=int(n["id"]),
                    grade=n.get("grade"),
                    clause=n.get("clause"),
                    standard=n.get("standard"),
                    title=n.get("title"),
                    description=n.get("description") or n.get("title"),
                    requirement=n.get("requirement"),
                    due_date=_ymd(n.get("due_date")),
                    status=n.get("status"),
                    auditor_name=n.get("auditor_name"),
                    dept=n.get("dept"),
                )
            )
    elif _table_exists(db, "audit_ncrs"):
        nrows = db.execute(
            text(
                "SELECT id, grade, clause_id, std_code, finding, requirement, due_date, status "
                "FROM audit_ncrs WHERE contract_id=:cid ORDER BY id"
            ),
            {"cid": contract_id},
        ).mappings().all()
        for n in nrows:
            ncrs.append(
                AuditReportNcrRow(
                    id=int(n["id"]),
                    grade=n.get("grade"),
                    clause=n.get("clause_id"),
                    standard=n.get("std_code"),
                    title=n.get("finding"),
                    description=n.get("finding"),
                    requirement=n.get("requirement"),
                    due_date=_ymd(n.get("due_date")),
                    status=n.get("status"),
                )
            )

    ncr_major = sum(1 for n in ncrs if _ncr_bucket(n.grade) == "major")
    ncr_minor = sum(1 for n in ncrs if _ncr_bucket(n.grade) == "minor")
    ncr_obs = sum(1 for n in ncrs if _ncr_bucket(n.grade) == "obs")

    # ⑤ matrix — required from standard_clause_map / process maps for contract standards
    written_set: Set[Tuple[str, str]] = set()
    verdict_map: Dict[Tuple[str, str], Optional[str]] = {}
    for c in clauses:
        code = (c.standard_code or to_process_standard_code(c.standard) or c.standard or "").upper()
        written_set.add((code, c.clause_no))
        verdict_map[(code, c.clause_no)] = c.verdict

    matrix_cells: List[AuditReportMatrixCell] = []
    std_keys = info.standards_keys or []
    std_codes = info.standards_codes or []
    if not std_codes and std_keys:
        std_codes = [to_process_standard_code(k) or k for k in std_keys]

    for i, code in enumerate(std_codes):
        sk = std_keys[i] if i < len(std_keys) else (resolve_standard_key(code) or code)
        master_clauses = list_clauses_for_standard_pg(db, code, standard_key=sk)
        for mc in master_clauses:
            cno = str(mc.get("clause_no") or mc.get("actual_clause_no") or "").strip()
            if not cno:
                continue
            topic = str(
                mc.get("clause_topic") or mc.get("clause_title") or cno
            ).strip()
            key = (code.upper(), cno)
            written = key in written_set
            matrix_cells.append(
                AuditReportMatrixCell(
                    clause_no=cno,
                    clause_topic=topic,
                    standard_key=sk,
                    standard_code=code,
                    written=written,
                    missing=not written,
                    verdict=verdict_map.get(key),
                )
            )

    # If plan items exist, prefer plan-scoped required set
    if plan_id:
        from app.services.audit_plan_scope import is_lead_auditor, load_engagement_plan_scope

        scope = load_engagement_plan_scope(
            db,
            contract_id=contract_id,
            auditor_id=int(auditor.id),
            auditor_name=(auditor.name or None),
            team_meeting=bool(
                team_meeting
                and is_lead_auditor(db, contract_id=contract_id, auditor_id=int(auditor.id))
            ),
        )
        plan_items = scope.get("items") or []
        if plan_items:
            from app.services.audit_plan_scope import filter_clauses_by_plan

            # Rebuild as lightweight dicts for filter
            filtered = filter_clauses_by_plan(
                [
                    {
                        "clause_no": c.clause_no,
                        "standard_key": c.standard_key,
                        "standard_code": c.standard_code,
                        "process_group_id": None,
                        "process_group_name": None,
                    }
                    for c in matrix_cells
                ],
                plan_items,
            )
            keep = {(x.get("standard_code"), x.get("clause_no")) for x in filtered}
            if keep:
                matrix_cells = [
                    c
                    for c in matrix_cells
                    if (c.standard_code, c.clause_no) in keep
                ]

    required = len(matrix_cells)
    written_n = sum(1 for c in matrix_cells if c.written)
    missing_n = required - written_n
    pct = round((written_n / required) * 100.0, 1) if required else 0.0

    member_names = list(_auditor_names(db, info.member_auditor_ids).values())
    team_bits = []
    if info.lead_auditor_name:
        team_bits.append(f"{info.lead_auditor_name}(팀장)")
    team_bits.extend(member_names)

    return AuditReportAggregateOut(
        contract_id=contract_id,
        company_name=info.company_name,
        biz_no=info.biz_no,
        address=info.address,
        standards=info.standards,
        standards_label=", ".join(info.standards) if info.standards else None,
        audit_type=info.audit_type,
        audit_period_start=info.audit_period_start,
        audit_period_end=info.audit_period_end,
        lead_auditor_name=info.lead_auditor_name,
        member_auditor_names=member_names,
        team_label=", ".join(team_bits) if team_bits else None,
        plan_id=plan_id,
        plan_status=(plan.get("status") if plan else None),
        note_id=note_id,
        clauses=clauses,
        ncrs=ncrs,
        ncr_major=ncr_major,
        ncr_minor=ncr_minor,
        ncr_obs=ncr_obs,
        matrix_required=required,
        matrix_written=written_n,
        matrix_missing=missing_n,
        matrix_coverage_pct=pct,
        matrix_cells=matrix_cells,
        notes_deep_link=_deep_link(contract_id),
    )
