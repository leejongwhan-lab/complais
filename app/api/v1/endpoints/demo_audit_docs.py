"""Demo / master-aligned payloads for certification-audit document pages.

Public (no auth) when demo=1 — safe sample from real master tables
(company_id=1, contract_id=1) with additive demo fills for gaps.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.data.standards_catalog import OPERATING_STANDARDS
from app.services.iso_clauses_master import resolve_standard_key
from app.services.process_group_masters import (
    list_standard_masters_pg,
    to_process_standard_code,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo/audit-docs", tags=["Demo Audit Docs"])

# Family → legacy UI chip short-key / CSS suffix (docs UX only)
_FAMILY_CHIP: Dict[str, Dict[str, str]] = {
    "QMS": {"legacy_k": "q", "short": "품질", "cls": "chip-q", "on": "on-q"},
    "EMS": {"legacy_k": "e", "short": "환경", "cls": "chip-e", "on": "on-e"},
    "OHSMS": {"legacy_k": "s", "short": "안전보건", "cls": "chip-s", "on": "on-s"},
    "MDQMS": {"legacy_k": "m", "short": "의료기기", "cls": "chip-m", "on": "on-m"},
    "FSMS": {"legacy_k": "f", "short": "식품안전", "cls": "chip-f", "on": "on-f"},
    "ISMS": {"legacy_k": "i", "short": "정보보안", "cls": "chip-i", "on": "on-i"},
    "EnMS": {"legacy_k": "en", "short": "에너지", "cls": "chip-en", "on": "on-en"},
    "ABMS": {"legacy_k": "ac", "short": "반부패", "cls": "chip-ac", "on": "on-ac"},
    "CMS": {"legacy_k": "co", "short": "준법경영", "cls": "chip-co", "on": "on-co"},
    "AIMS": {"legacy_k": "ai", "short": "AI경영", "cls": "chip-ai", "on": "on-ai"},
    "NSMS": {"legacy_k": "nu", "short": "원자력", "cls": "chip-nu", "on": "on-nu"},
    "PIMS": {"legacy_k": "pr", "short": "개인정보", "cls": "chip-pr", "on": "on-pr"},
    "BCMS": {"legacy_k": "bc", "short": "사업연속", "cls": "chip-bc", "on": "on-bc"},
}

DOC_PAGES = [
    # ── 최초인증 Stage 1 / Stage 2 ──
    {
        "slug": "stage1_readiness",
        "title": "1단계 서류준비성 검토",
        "doc_type": "stage1_readiness",
        "path": "/audit-docs/stage1_readiness",
        "file": "stage1_readiness.html",
        "group": "initial_stage1",
        "group_label": "최초인증 · 1단계",
    },
    {
        "slug": "stage1_report",
        "title": "1단계 심사보고서",
        "doc_type": "stage1_report",
        "path": "/audit-docs/stage1_report",
        "file": "stage1_report.html",
        "group": "initial_stage1",
        "group_label": "최초인증 · 1단계",
    },
    {
        "slug": "stage2_report",
        "title": "2단계 심사보고서",
        "doc_type": "stage2_report",
        "path": "/audit-docs/stage2_report",
        "file": "stage2_report.html",
        "group": "initial_stage2",
        "group_label": "최초인증 · 2단계",
    },
    {
        "slug": "plan",
        "title": "심사계획서",
        "doc_type": "audit_plan",
        "path": "/audit-docs/plan",
        "file": "plan.html",
        "group": "common",
        "group_label": "공통 · 계획/인력/신청",
    },
    {
        "slug": "application",
        "title": "인증심사 신청·계약·인증서",
        "doc_type": "application_contract",
        "path": "/audit-docs/application",
        "file": "application.html",
        "group": "common",
        "group_label": "공통 · 계획/인력/신청",
    },
    {
        "slug": "auditor_engagement",
        "title": "심사원 위촉계약·NDA",
        "doc_type": "auditor_engagement",
        "path": "/audit-docs/auditor_engagement",
        "file": "auditor_engagement.html",
        "group": "common",
        "group_label": "공통 · 계획/인력/신청",
    },
    {
        "slug": "personnel",
        "title": "심사원역량·공정성·이의·불만",
        "doc_type": "auditor_personnel",
        "path": "/audit-docs/personnel",
        "file": "personnel.html",
        "group": "common",
        "group_label": "공통 · 계획/인력/신청",
    },
    # ── 사후·갱신 / 전환 / 특별 ──
    {
        "slug": "recert",
        "title": "갱신심사 문서 세트",
        "doc_type": "recert_audit",
        "path": "/audit-docs/recert",
        "file": "recert.html",
        "group": "recert",
        "group_label": "사후·갱신",
    },
    {
        "slug": "transfer",
        "title": "전환심사 문서 세트",
        "doc_type": "transfer_audit",
        "path": "/audit-docs/transfer",
        "file": "transfer.html",
        "group": "transfer",
        "group_label": "전환심사",
    },
    {
        "slug": "special",
        "title": "특별심사 문서 세트",
        "doc_type": "special_audit",
        "path": "/audit-docs/special",
        "file": "special.html",
        "group": "special",
        "group_label": "특별심사",
    },
    {
        "slug": "cert_decision",
        "title": "인증검증 심의서",
        "doc_type": "cert_decision",
        "path": "/audit-docs/cert_decision",
        "file": "cert_decision.html",
        "group": "decision",
        "group_label": "검증·심의",
    },
]


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


def _ensure_schema(db: Session) -> None:
    """Additive only — columns / master rows for doc demo mapping."""
    if _table_exists(db, "audit_doc_data"):
        if not _column_exists(db, "audit_doc_data", "contract_id"):
            db.execute(
                text(
                    "ALTER TABLE audit_doc_data "
                    "ADD COLUMN contract_id INT NULL COMMENT 'contracts.id' AFTER application_id"
                )
            )
        if not _column_exists(db, "audit_doc_data", "is_demo"):
            db.execute(
                text(
                    "ALTER TABLE audit_doc_data "
                    "ADD COLUMN is_demo TINYINT(1) NOT NULL DEFAULT 0 "
                    "COMMENT '1=demo/sample row' AFTER saved_by"
                )
            )
        db.commit()

    # process standard_master: ISO13485 (MDQMS) often missing
    if _table_exists(db, "standard_master"):
        exists = db.execute(
            text("SELECT 1 FROM standard_master WHERE standard_code='ISO13485' LIMIT 1")
        ).first()
        if not exists:
            db.execute(
                text(
                    "INSERT INTO standard_master "
                    "(standard_code, standard_name, hls_adopted, native_structure_note) "
                    "VALUES ('ISO13485', 'ISO 13485:2016 (의료기기 품질경영시스템)', 'Y', "
                    "'MDQMS_2016 / platform standard_masters')"
                )
            )
            db.commit()

    # platform standard_masters: align ISO 22301 family only (no duplicate standard_code)
    if _table_exists(db, "standard_masters"):
        try:
            row = db.execute(
                text(
                    "SELECT id, standard_key, family_code FROM standard_masters "
                    "WHERE standard_key IN ('BCMS_2019','ISO22301_2019') "
                    "   OR standard_code='ISO 22301:2019' OR display_code='ISO 22301:2019' "
                    "LIMIT 1"
                )
            ).mappings().first()
            if row:
                if (row.get("family_code") or "").upper() != "BCMS":
                    db.execute(
                        text("UPDATE standard_masters SET family_code='BCMS' WHERE id=:id"),
                        {"id": int(row["id"])},
                    )
                    db.commit()
            else:
                db.execute(
                    text(
                        "INSERT INTO standard_masters "
                        "(standard_key, family_code, edition_year, iso_number, display_code, "
                        " standard_code, standard_name, version_year, clauses_status, role, is_active) "
                        "VALUES "
                        "('BCMS_2019','BCMS',2019,'ISO 22301','ISO 22301:2019',"
                        " 'ISO 22301:2019','사업연속성경영시스템',2019,'READY','CERTIFIABLE',1)"
                    )
                )
                db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("standard_masters BCMS ensure skipped: %s", exc)


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


def _standards_catalog(db: Session) -> List[Dict[str, Any]]:
    """Platform standard_masters (CERTIFIABLE) + process code mapping."""
    rows: List[Dict[str, Any]] = []
    if _table_exists(db, "standard_masters"):
        q = text(
            "SELECT standard_key, family_code, edition_year, iso_number, display_code, "
            "standard_code, standard_name, clauses_status, role "
            "FROM standard_masters "
            "WHERE is_active=1 AND (role='CERTIFIABLE' OR role IS NULL) "
            "ORDER BY id"
        )
        for r in db.execute(q).mappings():
            sk = str(r["standard_key"] or "").strip()
            if not sk or sk in {"COMMON", "IMS"}:
                continue
            fam = str(r["family_code"] or sk.split("_")[0]).strip()
            # normalize orphan key naming for chips (keep DB row)
            if sk == "ISO22301_2019":
                sk = "BCMS_2019"
                fam = "BCMS"
            chip = _FAMILY_CHIP.get(fam, {})
            pg = to_process_standard_code(sk) or to_process_standard_code(
                str(r["display_code"] or "")
            )
            rows.append(
                {
                    "standard_key": sk,
                    "family_code": fam,
                    "display_code": r["display_code"],
                    "standard_code": r["standard_code"] or r["display_code"],
                    "standard_name": r["standard_name"],
                    "process_code": pg,
                    "k": sk,  # master key — primary chip id
                    "legacy_k": chip.get("legacy_k") or fam.lower()[:2],
                    "label": r["display_code"] or sk,
                    "l": r["display_code"] or sk,
                    "short": chip.get("short") or fam,
                    "s": chip.get("short") or fam,
                    "cls": chip.get("cls") or "chip-q",
                    "c": chip.get("on") or "on-q",
                    "on": chip.get("on") or "on-q",
                    "desc": r["standard_name"] or "",
                }
            )
    if rows:
        return rows
    # catalog fallback
    out: List[Dict[str, Any]] = []
    for s in OPERATING_STANDARDS:
        if s.clauses_status == "PENDING" and s.edition_year and s.edition_year >= 2026:
            # still include — master may show both editions
            pass
        chip = _FAMILY_CHIP.get(s.family_code, {})
        pg = to_process_standard_code(s.standard_key)
        out.append(
            {
                "standard_key": s.standard_key,
                "family_code": s.family_code,
                "display_code": s.display_code,
                "standard_code": s.display_code,
                "standard_name": s.standard_name,
                "process_code": pg,
                "k": s.standard_key,
                "legacy_k": chip.get("legacy_k") or s.family_code.lower()[:2],
                "label": s.display_code,
                "l": s.display_code,
                "short": chip.get("short") or s.family_code,
                "s": chip.get("short") or s.family_code,
                "cls": chip.get("cls") or "chip-q",
                "c": chip.get("on") or "on-q",
                "on": chip.get("on") or "on-q",
                "desc": s.standard_name,
            }
        )
    return out


def _normalize_contract_standards(
    raw_list: List[Any], catalog: List[Dict[str, Any]]
) -> Tuple[List[str], List[str], List[str]]:
    keys: List[str] = []
    codes: List[str] = []
    labels: List[str] = []
    by_key = {c["standard_key"]: c for c in catalog}
    seen: set = set()
    for raw in raw_list:
        token = str(raw or "").strip()
        if not token:
            continue
        sk = resolve_standard_key(token) or ""
        if not sk:
            for c in catalog:
                if token in (c["display_code"], c["standard_code"], c["process_code"]):
                    sk = c["standard_key"]
                    break
        if not sk or sk in seen:
            continue
        seen.add(sk)
        keys.append(sk)
        c = by_key.get(sk, {})
        codes.append(c.get("process_code") or to_process_standard_code(sk) or sk)
        labels.append(c.get("display_code") or token)
    return keys, codes, labels


def _ensure_demo_plan(db: Session, contract_id: int) -> Optional[int]:
    if not _table_exists(db, "audit_plans"):
        return None
    row = db.execute(
        text("SELECT id FROM audit_plans WHERE contract_id=:c ORDER BY id DESC LIMIT 1"),
        {"c": contract_id},
    ).first()
    if row:
        return int(row[0])
    now = datetime.utcnow()
    plan_date = date.today() + timedelta(days=14)
    db.execute(
        text(
            "INSERT INTO audit_plans "
            "(contract_id, status, plan_date, audit_objective, audit_criteria, "
            " scope_summary, communication_note, created_by, created_at, updated_at) "
            "VALUES "
            "(:cid, 'draft', :pd, :obj, :crit, :scope, :note, NULL, :now, :now)"
        ),
        {
            "cid": contract_id,
            "pd": plan_date,
            "obj": "[DEMO] 경영시스템 적합·유효성 확인 (ISO/IEC 17021-1)",
            "crit": "ISO 9001:2015, ISO 45001:2018",
            "scope": "데모 심사계획 — master contracts.scope_kr 기준",
            "note": "is_demo seed — 실배정 없이 UI 확인용",
            "now": now,
        },
    )
    db.commit()
    row = db.execute(
        text("SELECT id FROM audit_plans WHERE contract_id=:c ORDER BY id DESC LIMIT 1"),
        {"c": contract_id},
    ).first()
    plan_id = int(row[0]) if row else None
    if plan_id and _table_exists(db, "audit_plan_items"):
        samples = [
            ("09:00-09:30", "개회회의", "—", "경영진", "회의실", "이종환", "QMS_2015", "ISO9001"),
            ("09:30-11:00", "리더십/기획", "5.1 / 6.1", "품질팀", "본사", "이종환", "QMS_2015", "ISO9001"),
            ("11:00-12:00", "운영(생산)", "8.1 / 8.5", "생산팀", "공장", "최광윤", "OHSMS_2018", "ISO45001"),
            ("13:00-14:30", "성과평가", "9.1 / 9.2", "관리팀", "본사", "이종환", "QMS_2015", "ISO9001"),
            ("14:30-15:30", "개선/종결회의", "10.2", "경영진", "회의실", "이종환", "QMS_2015", "ISO9001"),
        ]
        cols_sk = _column_exists(db, "audit_plan_items", "standard_key")
        cols_sc = _column_exists(db, "audit_plan_items", "standard_code")
        for i, (slot, proc, clause, auditee, loc, auditor, sk, sc) in enumerate(samples):
            fields = {
                "audit_plan_id": plan_id,
                "time_slot": slot,
                "process_name": proc,
                "standard_clause": clause,
                "auditee_name": auditee,
                "location_name": loc,
                "auditor_name": auditor,
                "note": "[DEMO]",
                "sort_order": i + 1,
            }
            extra_cols = ""
            extra_vals = ""
            if cols_sk:
                extra_cols += ", standard_key"
                extra_vals += ", :standard_key"
                fields["standard_key"] = sk
            if cols_sc:
                extra_cols += ", standard_code"
                extra_vals += ", :standard_code"
                fields["standard_code"] = sc
            if _column_exists(db, "audit_plan_items", "clause_no"):
                extra_cols += ", clause_no"
                extra_vals += ", :clause_no"
                fields["clause_no"] = clause.split("/")[0].strip() if clause != "—" else None
            db.execute(
                text(
                    "INSERT INTO audit_plan_items "
                    "(audit_plan_id, time_slot, process_name, standard_clause, auditee_name, "
                    f" location_name, auditor_name, note, sort_order{extra_cols}) "
                    "VALUES "
                    "(:audit_plan_id, :time_slot, :process_name, :standard_clause, :auditee_name, "
                    f" :location_name, :auditor_name, :note, :sort_order{extra_vals})"
                ),
                fields,
            )
        db.commit()
    return plan_id


def _map_assignment_role(raw: Optional[str]) -> str:
    """Map AuditAssignmentsRole / legacy labels → plan.html role keys."""
    v = (raw or "").strip().lower()
    if v in ("lead", "leader", "team_leader", "팀장", "심사팀장"):
        return "leader"
    if v in ("expert", "te", "tech", "technical_expert", "기술전문가"):
        return "te"
    if v in ("observer", "참관", "참관인"):
        return "observer"
    if v in ("witness", "입회"):
        return "observer"
    if v in ("guide", "안내", "안내인"):
        return "guide"
    return "auditor"


def _load_assignment_rows(db: Session, contract_id: int) -> List[Dict[str, Any]]:
    if not _table_exists(db, "audit_assignments"):
        return []
    rows = db.execute(
        text(
            "SELECT id, auditor_id, role, assignment_role, status, standards_json, "
            "assignment_note "
            "FROM audit_assignments WHERE contract_id=:c ORDER BY id ASC"
        ),
        {"c": contract_id},
    ).mappings().all()
    return [dict(r) for r in rows]


def _load_plan_processes(
    db: Session, plan_id: Optional[int]
) -> Dict[str, List[str]]:
    """auditor_name / auditor_id → process names from audit_plan_items."""
    out: Dict[str, List[str]] = {}
    if not plan_id or not _table_exists(db, "audit_plan_items"):
        return out
    rows = db.execute(
        text(
            "SELECT auditor_name, auditor_id, process_name "
            "FROM audit_plan_items WHERE audit_plan_id=:p ORDER BY sort_order, id"
        ),
        {"p": plan_id},
    ).mappings().all()
    for r in rows:
        proc = (r.get("process_name") or "").strip()
        if not proc:
            continue
        keys: List[str] = []
        if r.get("auditor_id") is not None:
            keys.append(f"id:{int(r['auditor_id'])}")
        name = (r.get("auditor_name") or "").strip()
        if name:
            keys.append(f"name:{name}")
        for k in keys:
            out.setdefault(k, [])
            if proc not in out[k]:
                out[k].append(proc)
    return out


def _load_team(
    db: Session,
    contract: Dict[str, Any],
    *,
    plan_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    team: List[Dict[str, Any]] = []
    processes = _load_plan_processes(db, plan_id)
    assignments = _load_assignment_rows(db, int(contract.get("id") or 0))

    if assignments and _table_exists(db, "auditors"):
        for aa in assignments:
            aid = aa.get("auditor_id")
            if not aid:
                continue
            r = db.execute(
                text(
                    "SELECT id, name, grade, registration_no FROM auditors "
                    "WHERE id=:id LIMIT 1"
                ),
                {"id": int(aid)},
            ).mappings().first()
            if not r:
                continue
            role = _map_assignment_role(
                aa.get("assignment_role") or aa.get("role")
            )
            procs = processes.get(f"id:{int(r['id'])}") or processes.get(
                f"name:{(r.get('name') or '').strip()}"
            ) or []
            team.append(
                {
                    "auditor_id": int(r["id"]),
                    "name": r["name"],
                    "role": role,
                    "assignment_role": aa.get("assignment_role") or aa.get("role"),
                    "grade": r["grade"],
                    "registration_no": r.get("registration_no"),
                    "standards_json": aa.get("standards_json"),
                    "assignment_note": aa.get("assignment_note"),
                    "processes": procs,
                    "is_demo": False,
                }
            )
        if team:
            return team

    lead_id = contract.get("lead_auditor_id")
    member_ids = _parse_json_list(contract.get("member_auditor_ids"))
    ids: List[int] = []
    if lead_id:
        try:
            ids.append(int(lead_id))
        except (TypeError, ValueError):
            pass
    for m in member_ids:
        try:
            mid = int(m)
            if mid not in ids:
                ids.append(mid)
        except (TypeError, ValueError):
            continue
    # demo fill if empty
    if not ids:
        ids = [1, 5]
    if not _table_exists(db, "auditors"):
        return [
            {
                "auditor_id": 1,
                "name": "이종환",
                "role": "leader",
                "assignment_role": "lead",
                "grade": "senior",
                "processes": processes.get("name:이종환") or [],
                "is_demo": True,
            },
            {
                "auditor_id": 5,
                "name": "최광윤",
                "role": "auditor",
                "assignment_role": "auditor",
                "grade": "auditor",
                "processes": processes.get("name:최광윤") or [],
                "is_demo": True,
            },
        ]
    for i, aid in enumerate(ids[:5]):
        r = db.execute(
            text(
                "SELECT id, name, grade, registration_no FROM auditors WHERE id=:id LIMIT 1"
            ),
            {"id": aid},
        ).mappings().first()
        if not r:
            continue
        procs = processes.get(f"id:{int(r['id'])}") or processes.get(
            f"name:{(r.get('name') or '').strip()}"
        ) or []
        team.append(
            {
                "auditor_id": int(r["id"]),
                "name": r["name"],
                "role": "leader" if i == 0 else "auditor",
                "assignment_role": "lead" if i == 0 else "auditor",
                "grade": r["grade"],
                "registration_no": r.get("registration_no"),
                "processes": procs,
                "is_demo": aid in (1, 5) and not lead_id,
            }
        )
    return team


def _field_map(company: Dict[str, Any], contract: Dict[str, Any], cb: Dict[str, Any], labels: List[str]) -> Dict[str, str]:
    """HTML input id → master value. Keys match document UX field ids."""
    name = company.get("name") or ""
    ceo = company.get("ceo_name") or ""
    addr = company.get("address") or ""
    emp = str(company.get("employee_count") or "")
    biz = company.get("biz_no") or ""
    scope = contract.get("scope_kr") or company.get("scope_kr") or ""
    std_join = ", ".join(labels)
    contact = " / ".join(
        x for x in [company.get("tax_contact_name"), company.get("tel"), company.get("email")] if x
    )
    cert_no = company.get("cert_no") or ""
    return {
        # common org
        "a1-org": name,
        "b1-org": name,
        "c1-org": name,
        "d1-org": name,
        "d2-org": name,
        "d3-org": name,
        "d4-org": name,
        "p1-org": name,
        "p2-org": name,
        "p3-org": name,
        "p4-org": name,
        "m1-org": name,
        "r1-org": name,
        "s1-org": name,
        "s2-org": name,
        "imp-org": name,
        "cert-org": name,
        # people / address
        "a1-ceo": ceo,
        "d1-ceo": ceo,
        "a1-addr": addr,
        "d1-addr": addr,
        "p1-addr": addr,
        "s1-addr": addr,
        "s2-addr": addr,
        "cert-addr": addr,
        "a1-emp": emp,
        "d1-emp": emp,
        "md5-emp": emp,
        "a1-bizno": biz,
        "d1-bizno": biz,
        "a1-contact": contact,
        "d1-contact": contact,
        "p1-contact": contact,
        "aud-contact": contact,
        # scope / standards
        "a1-scope": scope,
        "c1-scope": scope,
        "d1-scope": scope,
        "d3-scope": scope,
        "d4-scope": scope,
        "p1-scope": scope,
        "p2-scope": scope,
        "p3-scope": scope,
        "m1-scope": scope,
        "s1-scope": scope,
        "s2-scope": scope,
        "cert-scope": scope,
        "a1-std": std_join,
        "c1-std": std_join,
        "d1-std": std_join,
        "d1-stds": std_join,
        "p1-std": std_join,
        "m1-std": std_join,
        "r1-std": std_join,
        "aud-std": std_join,
        "cert-std": std_join,
        "md5-stds": std_join,
        "c1-criteria": std_join,
        # CB / cert
        "cert-cb-name": cb.get("name") or "",
        "cert-no": cert_no,
        "a1-cert-no": cert_no,
        "d1-cert-no": cert_no,
        "m1-cert-no": cert_no,
        "p1-cert-no": cert_no,
        # team names (plan)
        "as1-name": "",
        "as2-name": "",
        "as3-name": "",
        "aud-name": "",
        # Stage1/Stage2 report sync panel (f-*)
        "f-org": name,
        "f-addr": addr,
        "f-scope": scope,
        "f-std": std_join,
        "f-lead": "",
        "f-aud": "",
        "f-te": "",
        "f-cb": cb.get("name") or "",
        "f-rep": ceo,
        "f-rptno": "",
        "f-rno": "",
    }


@router.get("/catalog")
def demo_catalog():
    """List openable document pages (hub)."""
    return {
        "hub": "/demo/audit-docs",
        "default_params": "demo=1&contract_id=1",
        "pages": DOC_PAGES,
        "portal": {
            "auditor": "/auditor-portal?tab=docs&demo=1&contract_id=1",
            "notes": "/auditor-portal?tab=reports&demo=1&contract_id=1",
            "report": "/auditor-portal?tab=reports&view=report&demo=1&contract_id=1",
            "schedules": "/auditor-portal?tab=schedules&demo=1",
            "plan_alias": "/audit_plan_doc.php?demo=1&contract_id=1",
            "stage1_readiness": "/audit-docs/stage1_readiness?demo=1&contract_id=1",
            "stage1_report": "/audit-docs/stage1_report?demo=1&contract_id=1",
            "stage2_report": "/audit-docs/stage2_report?demo=1&contract_id=1",
        },
    }


@router.get("/standards")
def demo_standards(db: Session = Depends(get_db)):
    _ensure_schema(db)
    return {
        "source": "standard_masters + process standard_master mapping",
        "standards": _standards_catalog(db),
        "process_standard_master": list_standard_masters_pg(db),
    }


@router.get("/clauses")
def demo_clauses(
    standard_key: Optional[List[str]] = Query(
        None, description="Filter by standard_key (repeatable). Empty = all seeded masters."
    ),
    db: Session = Depends(get_db),
):
    """Clause catalog from standard_clause_masters (same source as audit-notes /clauses).

    Public demo endpoint for document HTML fallback/cache — no inventing clauses.
    """
    _ensure_schema(db)
    list_official_clauses = None
    try:
        from app.services.standard_clause_titles import (
            ensure_standard_clause_titles,
            list_official_clauses as _list_official_clauses,
        )

        ensure_standard_clause_titles(db)
        list_official_clauses = _list_official_clauses
    except Exception:
        logger.exception("ensure_standard_clause_titles failed")

    catalog = _standards_catalog(db)
    keys: List[str] = []
    if standard_key:
        for raw in standard_key:
            sk = resolve_standard_key(raw) or raw
            if sk and sk not in keys:
                keys.append(sk)
    if not keys:
        keys = [
            s["standard_key"]
            for s in catalog
            if s.get("standard_key") and s["standard_key"] not in ("COMMON", "IMS")
        ]

    clauses: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for sk in keys:
        rows: List[Dict[str, Any]] = []
        try:
            if list_official_clauses:
                rows = list_official_clauses(db, sk)
        except Exception:
            logger.exception("list_official_clauses failed for %s", sk)
        counts[sk] = len(rows)
        for r in rows:
            cno = str(r.get("clause_no") or "").strip()
            if not cno:
                continue
            title = (r.get("clause_title") or r.get("clause_topic") or "").strip()
            major = cno.split(".")[0]
            clauses.append(
                {
                    "id": cno,
                    "clause_no": cno,
                    "standard_key": r.get("standard_key") or sk,
                    "family_code": r.get("family_code"),
                    "clause_title": title,
                    "clause_topic": title,
                    "label": (cno + (" " + title if title else "")).strip(),
                    "g": f"{major}항",
                    "group_name": f"{major}항",
                    "source": "standard_clause_masters",
                    "sort_order": r.get("sort_order") or 0,
                }
            )

    return {
        "source": "standard_clause_masters",
        "sync_date": date.today().isoformat(),
        "standard_keys": keys,
        "counts": counts,
        "total": len(clauses),
        "clauses": clauses,
    }


@router.get("/context")
def demo_context(
    contract_id: int = Query(1, description="contracts.id"),
    demo: int = Query(1, description="1=allow demo fill from masters"),
    db: Session = Depends(get_db),
):
    """Master-aligned context for all audit document HTML pages."""
    _ensure_schema(db)
    if not _table_exists(db, "contracts") or not _table_exists(db, "companies"):
        raise HTTPException(status_code=503, detail="master tables missing")

    contract = db.execute(
        text("SELECT * FROM contracts WHERE id=:id LIMIT 1"),
        {"id": contract_id},
    ).mappings().first()
    used_demo_contract = False
    if not contract and demo:
        contract = db.execute(
            text("SELECT * FROM contracts ORDER BY id ASC LIMIT 1")
        ).mappings().first()
        used_demo_contract = True
    if not contract:
        raise HTTPException(status_code=404, detail="contract not found")

    contract = dict(contract)
    company_id = int(contract.get("company_id") or 1)
    company = db.execute(
        text("SELECT * FROM companies WHERE id=:id LIMIT 1"),
        {"id": company_id},
    ).mappings().first()
    if not company:
        raise HTTPException(status_code=404, detail="company not found")
    company = dict(company)

    cb: Dict[str, Any] = {}
    cb_id = contract.get("cb_id")
    if cb_id and _table_exists(db, "certification_bodies"):
        row = db.execute(
            text(
                "SELECT id, name, logo_path FROM certification_bodies WHERE id=:id LIMIT 1"
            ),
            {"id": int(cb_id)},
        ).mappings().first()
        if row:
            cb = dict(row)

    catalog = _standards_catalog(db)
    raw_stds = _parse_json_list(contract.get("applied_standards") or contract.get("standards"))
    std_keys, std_codes, std_labels = _normalize_contract_standards(raw_stds, catalog)
    if not std_keys and demo:
        std_keys, std_codes, std_labels = _normalize_contract_standards(
            ["ISO 9001:2015", "ISO 45001:2018"], catalog
        )

    plan_id = _ensure_demo_plan(db, int(contract["id"])) if demo else None
    if plan_id is None and _table_exists(db, "audit_plans"):
        row = db.execute(
            text(
                "SELECT id FROM audit_plans WHERE contract_id=:c ORDER BY id DESC LIMIT 1"
            ),
            {"c": int(contract["id"])},
        ).first()
        plan_id = int(row[0]) if row else None

    audit_plan: Dict[str, Any] = {}
    if plan_id and _table_exists(db, "audit_plans"):
        prow = db.execute(
            text(
                "SELECT id, audit_objective, audit_criteria, scope_summary, "
                "communication_note, plan_date, status "
                "FROM audit_plans WHERE id=:id LIMIT 1"
            ),
            {"id": int(plan_id)},
        ).mappings().first()
        if prow:
            audit_plan = dict(prow)

    team = _load_team(db, contract, plan_id=plan_id)
    fields = _field_map(company, contract, cb, std_labels)
    if team:
        fields["as1-name"] = team[0].get("name") or ""
        fields["aud-name"] = team[0].get("name") or ""
        fields["f-lead"] = team[0].get("name") or ""
        if len(team) > 1:
            fields["as2-name"] = team[1].get("name") or ""
            fields["f-aud"] = team[1].get("name") or ""
        if len(team) > 2:
            fields["as3-name"] = team[2].get("name") or ""
            fields["f-te"] = team[2].get("name") or ""
    objective = (audit_plan.get("audit_objective") or "").strip()
    if objective:
        fields["f-objective"] = objective
        fields["s1-objective"] = objective
        fields["s2-objective"] = objective
        fields["c1-objective"] = objective

    # master field dictionary (explicit names for docs/JS)
    master = {
        "company_id": company.get("id"),
        "company_name": company.get("name"),
        "name": company.get("name"),
        "name_en": company.get("name_en"),
        "ceo_name": company.get("ceo_name"),
        "biz_no": company.get("biz_no"),
        "address": company.get("address"),
        "detail_address": company.get("detail_address"),
        "employee_count": company.get("employee_count"),
        "iaf_code": company.get("iaf_code"),
        "ksic_code": company.get("ksic_code"),
        "scope_kr": contract.get("scope_kr") or company.get("scope_kr"),
        "scope_en": contract.get("scope_en") or company.get("scope_en"),
        "cert_no": company.get("cert_no"),
        "tel": company.get("tel"),
        "email": company.get("email"),
        "contract_id": contract.get("id"),
        "contract_no": contract.get("contract_id"),
        "cb_id": contract.get("cb_id"),
        "cb_name": cb.get("name"),
        "audit_type": contract.get("audit_type"),
        "stage": contract.get("stage"),
        "status": contract.get("status"),
        "standards": std_labels,
        "standard_keys": std_keys,
        "standard_codes": std_codes,
        "audit_period_start": _ymd(contract.get("audit_period_start")),
        "audit_period_end": _ymd(contract.get("audit_period_end")),
        "total_md": str(contract.get("total_md") or ""),
        "lead_auditor_id": contract.get("lead_auditor_id"),
        "audit_objective": objective,
        "audit_plan_id": plan_id,
    }

    pages = []
    for p in DOC_PAGES:
        q = f"?demo=1&contract_id={contract['id']}"
        pages.append({**p, "url": p["path"] + q})

    return {
        "demo": bool(demo),
        "used_demo_contract_fallback": used_demo_contract,
        "master": master,
        "company": {
            "id": company.get("id"),
            "name": company.get("name"),
            "ceo_name": company.get("ceo_name"),
            "biz_no": company.get("biz_no"),
            "address": company.get("address"),
            "employee_count": company.get("employee_count"),
            "scope_kr": company.get("scope_kr"),
            "iaf_code": company.get("iaf_code"),
            "cert_no": company.get("cert_no"),
        },
        "contract": {
            "id": contract.get("id"),
            "contract_id": contract.get("contract_id"),
            "company_id": contract.get("company_id"),
            "cb_id": contract.get("cb_id"),
            "audit_type": contract.get("audit_type"),
            "standards_raw": contract.get("standards"),
            "standard_keys": std_keys,
            "standard_codes": std_codes,
            "standard_labels": std_labels,
            "scope_kr": contract.get("scope_kr"),
            "status": contract.get("status"),
            "stage": contract.get("stage"),
        },
        "cb": cb,
        "team": team,
        "audit_plan_id": plan_id,
        "audit_plan": {
            "id": audit_plan.get("id") or plan_id,
            "audit_objective": objective,
            "audit_criteria": audit_plan.get("audit_criteria"),
            "scope_summary": audit_plan.get("scope_summary"),
            "communication_note": audit_plan.get("communication_note"),
            "plan_date": _ymd(audit_plan.get("plan_date")),
            "status": audit_plan.get("status"),
        },
        "standards_catalog": catalog,
        "selected_standard_keys": std_keys,
        "fields": fields,
        "pages": pages,
        "deep_links": {
            "notes": f"/auditor-portal?tab=reports&contract_id={contract['id']}&demo=1",
            "report": f"/auditor-portal?tab=reports&view=report&contract_id={contract['id']}&demo=1",
            "schedules": "/auditor-portal?tab=schedules&demo=1",
            "plan": f"/audit-docs/plan?demo=1&contract_id={contract['id']}",
            "stage1_readiness": f"/audit-docs/stage1_readiness?demo=1&contract_id={contract['id']}",
            "stage1_report": f"/audit-docs/stage1_report?demo=1&contract_id={contract['id']}",
            "stage2_report": f"/audit-docs/stage2_report?demo=1&contract_id={contract['id']}",
            "hub": f"/demo/audit-docs?demo=1&contract_id={contract['id']}",
        },
        "field_mapping_notes": {
            "company.name": "companies.name → a1-org / s1-org / f-org / cert-org …",
            "company.ceo_name": "companies.ceo_name → a1-ceo / f-rep",
            "company.biz_no": "companies.biz_no → a1-bizno",
            "company.address": "companies.address → a1-addr / f-addr",
            "company.employee_count": "companies.employee_count → a1-emp",
            "contracts.scope_kr": "contracts.scope_kr → a1-scope / f-scope",
            "contracts.standards": "→ standard_keys (QMS_2015…) via resolve_standard_key",
            "standard_masters.standard_key": "chip k / selectedStds primary key",
            "standard_master.standard_code": "process ISO9001 code (parallel)",
            "auditors.*": "team[] / as1-name / f-lead / f-aud",
            "certification_bodies.name": "cert-cb-name / f-cb",
            "audit_plans / audit_plan_items": "seeded when empty (demo)",
            "stage1_readiness": "doc_type=stage1_readiness (audit_doc_data)",
            "stage1_report / stage2_report": "UX HTML; f-* panel from master context",
        },
    }
