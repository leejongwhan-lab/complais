"""심사원 포털 — 심사노트(조항 단위) API.

- 조항 마스터: process-group Excel tables (standard_clause_map / hls / process_group); NOT iso_clauses_master
- 저장: audit_notes(헤더) + audit_note_clauses + audit_note_ncr
- KPI: 선택 입력 — 빈 값이어도 저장 성공
- AI: OPENAI_API_KEY 있을 때 문장 정형화 (없으면 graceful stub)
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.data.audit_interviews import list_interviews_for_standards
from app.data.standards_catalog import OPERATING_STANDARDS
from app.models.auditor import Auditor
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.enums import UsersRole
from app.schemas.auditor_audit_notes import (
    AuditInterviewEntry,
    AuditInterviewSaveIn,
    AuditInterviewSaveOut,
    AuditInterviewTemplateItem,
    AuditKpiMasterItem,
    AuditMatrixCell,
    AuditMatrixOut,
    AuditNoteCheckpoint,
    AuditNoteClauseItem,
    AuditNoteClauseSaveIn,
    AuditNoteClauseSaveOut,
    AuditNoteFormalizeIn,
    AuditNoteFormalizeOut,
    AuditNoteKpiHint,
    AuditNoteMethodIn,
    AuditNoteMethodOut,
    AuditNoteSessionOut,
    AuditNoteStandardItem,
    ProcessGroupClauseItem,
    ProcessGroupHlsItem,
    ProcessGroupItem,
    ProcessGroupNavOut,
)
from app.services.audit_plan_scope import (
    filter_clauses_by_plan,
    load_engagement_plan_scope,
    resolve_plan_autofill,
)
from app.services.company_held_certs import list_company_held_standards
from app.services.iso_clauses_master import (
    list_operating_standards,
    resolve_standard_key,
)
from app.services.process_group_masters import (
    count_clauses_for_standard_pg,
    ensure_audit_note_longtext,
    ensure_ncr_extra_columns,
    list_audit_kpis,
    list_clauses_for_standard_pg,
    list_process_group_tree,
    list_standard_masters_pg,
    seed_process_group_masters,
    to_process_standard_code,
)


def _kpi_hints(rows: Optional[List[Dict[str, Any]]]) -> List[AuditNoteKpiHint]:
    out: List[AuditNoteKpiHint] = []
    for k in rows or []:
        out.append(
            AuditNoteKpiHint(
                kpi_id=k.get("kpi_id") or k.get("key") or "",
                kpi_name=k.get("kpi_name") or k.get("label") or "",
                source=k.get("source"),
                kpi_kind=k.get("kpi_kind"),
            )
        )
    return out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor/audit-notes", tags=["Auditor Audit Notes"])

_VERDICT_CONFORM = "적합"
_VERDICT_BY_GRADE = {
    "major": "중대한부적합",
    "minor": "경미한부적합",
    "observation": "관찰사항",
    "obs": "관찰사항",
}
_GRADE_BY_VERDICT = {
    "중대한부적합": "major",
    "경미한부적합": "minor",
    "관찰사항": "observation",
}


def _parse_esg_tags(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    return [p.strip() for p in s.replace(";", ",").split(",") if p.strip()]


def _require_auditor(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.AUDITOR.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="심사원 포털은 심사원 계정만 이용할 수 있습니다.",
        )
    return current_user


def _table_exists(db: Session, name: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t LIMIT 1"
        ),
        {"t": name},
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


def _parse_standards_field(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw).strip()
    if not s:
        return []
    if s.startswith("["):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            pass
    return [p.strip() for p in s.replace(";", ",").split(",") if p.strip()]


def _family_of(standard_key: str) -> str:
    s = (standard_key or "").strip()
    return s.split("_")[0].upper() if "_" in s else s.upper()


def _keys_from_raw_fields(*fields: Any) -> List[str]:
    keys: List[str] = []
    seen: Set[str] = set()
    for field in fields:
        for raw in _parse_standards_field(field):
            sk = resolve_standard_key(raw)
            if sk and sk not in seen:
                seen.add(sk)
                keys.append(sk)
    return keys


def _contract_field_standard_keys(contract: Contracts) -> List[str]:
    """Standards declared on the contract / 신청표준 — no catalog fallback."""
    return _keys_from_raw_fields(
        getattr(contract, "standards", None),
        getattr(contract, "applied_standards", None),
        getattr(contract, "standard_codes", None),
        getattr(contract, "iso_standards", None),
        getattr(contract, "standard_code", None),
    )


def _company_held_standard_keys(db: Session, company_id: Optional[int]) -> List[str]:
    """보유표준/신청표준 from company_certificates + apps (via list_company_held_standards)."""
    if not company_id:
        return []
    keys: List[str] = []
    seen: Set[str] = set()
    try:
        rows = list_company_held_standards(db, int(company_id), display_mode="auditor")
    except Exception:
        logger.exception("list_company_held_standards failed company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass
        return []
    for row in rows or []:
        candidates = [
            row.get("standard_code"),
            row.get("initial"),
            row.get("iso_code"),
            row.get("label"),
        ]
        for raw in candidates:
            sk = resolve_standard_key(raw) if raw else None
            if sk and sk not in seen:
                seen.add(sk)
                keys.append(sk)
                break
    return keys


def _session_standard_keys(
    db: Session, contract: Contracts
) -> tuple[List[str], str]:
    """Filter standards for a real audit engagement.

    Prefer intersection(contract ∩ company held/applied by family).
    If contract has specific standards, those win when intersection is empty.
    Else company held/applied. Never dump all 14 operating standards.
    """
    contract_keys = _contract_field_standard_keys(contract)
    company_id = getattr(contract, "company_id", None)
    company_keys = _company_held_standard_keys(db, company_id)

    if contract_keys and company_keys:
        company_fams = {_family_of(k) for k in company_keys}
        company_set = set(company_keys)
        inter = [
            k
            for k in contract_keys
            if k in company_set or _family_of(k) in company_fams
        ]
        if inter:
            return inter, "intersection"
        return contract_keys, "contract"
    if contract_keys:
        return contract_keys, "contract"
    if company_keys:
        return company_keys, "company"
    return [], "none"


def _normalize_audit_mode(raw: Optional[str]) -> Optional[str]:
    """contracts.audit_mode → single | integrated (or None)."""
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if key in {"single", "단독", "단일", "단독심사", "단일심사"}:
        return "single"
    if key in {"integrated", "통합", "통합심사", "multi", "multi_standard"}:
        return "integrated"
    return None


def _audit_mode_label(mode: Optional[str]) -> Optional[str]:
    if mode == "integrated":
        return "통합심사"
    if mode == "single":
        return "단일심사"
    return None


def _resolve_audit_mode(
    contract: Optional[Contracts], standard_keys: List[str]
) -> tuple[Optional[str], Optional[str]]:
    """Detect 단일/통합 from contracts.audit_mode; fall back to standard count."""
    raw = getattr(contract, "audit_mode", None) if contract else None
    mode = _normalize_audit_mode(raw)
    if not mode:
        mode = "integrated" if len(standard_keys) >= 2 else (
            "single" if standard_keys else None
        )
    # If DB says single but package has 2+ held/applied standards, prefer integrated
    if mode == "single" and len(standard_keys) >= 2:
        mode = "integrated"
    return mode, _audit_mode_label(mode)


def _interview_templates_out(
    standard_keys: List[str],
) -> List[AuditInterviewTemplateItem]:
    return [
        AuditInterviewTemplateItem(**iv)
        for iv in list_interviews_for_standards(standard_keys)
    ]


def _decode_interview_json(raw: Any) -> Any:
    if raw is None:
        return None
    data = raw
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="ignore")
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            # Plain text stored without JSON wrapper
            return {"content": raw}
    return data


def _merge_legacy_answers_to_qa(answers: Dict[str, str], qa_content: Optional[str]) -> str:
    """Unify split q0/q1 boxes into one qa_content string."""
    if (qa_content or "").strip():
        return str(qa_content).strip()
    if not answers:
        return ""
    # Prefer explicit qa / content keys
    for k in ("qa", "qa_content", "content"):
        if (answers.get(k) or "").strip():
            return str(answers[k]).strip()
    lines: List[str] = []
    for k in sorted(answers.keys(), key=lambda x: (len(x), x)):
        v = (answers.get(k) or "").strip()
        if not v:
            continue
        if str(k).startswith("q") and str(k)[1:].isdigit():
            lines.append(f"Q{int(str(k)[1:]) + 1}: {v}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines).strip()


def _flatten_legacy_interview_entries(entries: List[AuditInterviewEntry]) -> str:
    """Convert multi-field entries into a readable text block (compat)."""
    parts: List[str] = []
    for e in entries:
        lines: List[str] = []
        title = (e.role or e.role_key or "").strip()
        if title:
            lines.append("【" + title + "】")
        meta = []
        if e.name:
            meta.append("성명: " + str(e.name))
        if e.dept:
            meta.append("부서: " + str(e.dept))
        if e.position:
            meta.append("직책: " + str(e.position))
        if e.date:
            meta.append("일자: " + str(e.date))
        st = (e.startTime or "").strip()
        et = (e.endTime or "").strip()
        if st or et:
            meta.append("시간: " + st + (" ~ " + et if et else ""))
        if e.place:
            meta.append("장소: " + str(e.place))
        if meta:
            lines.append(" / ".join(meta))
        qa = _merge_legacy_answers_to_qa(e.answers or {}, e.qa_content)
        if qa:
            lines.append("질문·응답:\n" + qa)
        if (e.overall or "").strip():
            lines.append("종합의견: " + str(e.overall).strip())
        block = "\n".join(lines).strip()
        if block:
            parts.append(block)
    return "\n\n".join(parts).strip()


def _parse_interview_entries(raw: Any) -> List[AuditInterviewEntry]:
    data = _decode_interview_json(raw)
    if data is None:
        return []
    entries_raw: Any
    if isinstance(data, dict) and "entries" in data:
        entries_raw = data.get("entries")
    elif isinstance(data, list):
        entries_raw = data
    elif isinstance(data, dict) and "content" in data and len(
        [k for k in data.keys() if k not in {"content"}]
    ) == 0:
        # Plain single-box legacy — no structural entries
        return []
    elif isinstance(data, dict):
        # v15-style map keyed by role_key
        entries_raw = []
        for rk, val in data.items():
            if rk in {"content", "entries"} or not isinstance(val, dict):
                continue
            item = dict(val)
            item.setdefault("role_key", rk)
            answers = item.get("answers")
            if not isinstance(answers, dict):
                answers = {
                    k: str(v)
                    for k, v in item.items()
                    if str(k).startswith("q") and str(k)[1:].isdigit()
                }
                item["answers"] = answers
            if not item.get("qa_content"):
                item["qa_content"] = _merge_legacy_answers_to_qa(
                    answers, item.get("qa_content")
                )
            entries_raw.append(item)
    else:
        return []

    out: List[AuditInterviewEntry] = []
    if not isinstance(entries_raw, list):
        return out
    for item in entries_raw:
        if not isinstance(item, dict):
            continue
        rk = str(item.get("role_key") or "").strip()
        if not rk:
            continue
        answers = item.get("answers") if isinstance(item.get("answers"), dict) else {}
        if not answers:
            answers = {
                k: ("" if v is None else str(v))
                for k, v in item.items()
                if str(k).startswith("q") and str(k)[1:].isdigit()
            }
        qa = _merge_legacy_answers_to_qa(
            {str(k): ("" if v is None else str(v)) for k, v in answers.items()},
            item.get("qa_content"),
        )
        out.append(
            AuditInterviewEntry(
                role_key=rk,
                role=item.get("role"),
                name=item.get("name"),
                dept=item.get("dept"),
                position=item.get("position"),
                date=item.get("date"),
                startTime=item.get("startTime") or item.get("start_time"),
                endTime=item.get("endTime") or item.get("end_time"),
                place=item.get("place"),
                overall=item.get("overall"),
                qa_content=qa or None,
                answers={str(k): ("" if v is None else str(v)) for k, v in answers.items()},
            )
        )
    return out


def _parse_interview_content(raw: Any) -> str:
    """Flatten for compat string; prefer entries when present."""
    data = _decode_interview_json(raw)
    if data is None:
        return ""
    entries = _parse_interview_entries(raw)
    if entries:
        return _flatten_legacy_interview_entries(entries)
    if isinstance(data, dict) and "content" in data:
        return "" if data.get("content") is None else str(data.get("content"))
    if isinstance(data, str):
        return data
    return ""


def _load_interview_entries(db: Session, note_id: int) -> List[AuditInterviewEntry]:
    if not _table_exists(db, "audit_notes"):
        return []
    ensure_audit_note_longtext(db)
    row = db.execute(
        text("SELECT interview_json FROM audit_notes WHERE id = :id LIMIT 1"),
        {"id": note_id},
    ).first()
    if not row:
        return []
    return _parse_interview_entries(row[0])


def _load_interview_content(db: Session, note_id: int) -> str:
    if not _table_exists(db, "audit_notes"):
        return ""
    ensure_audit_note_longtext(db)
    row = db.execute(
        text("SELECT interview_json FROM audit_notes WHERE id = :id LIMIT 1"),
        {"id": note_id},
    ).first()
    if not row:
        return ""
    return _parse_interview_content(row[0])


def _entries_to_storage(entries: List[AuditInterviewEntry]) -> Dict[str, Any]:
    """Persist as {entries:[…]} — structural fields + single qa_content."""
    out = []
    for e in entries:
        out.append(
            {
                "role_key": e.role_key,
                "role": e.role,
                "name": e.name or "",
                "dept": e.dept or "",
                "position": e.position or "",
                "date": e.date or "",
                "startTime": e.startTime or "",
                "endTime": e.endTime or "",
                "place": e.place or "",
                "qa_content": e.qa_content or "",
                "overall": e.overall or "",
            }
        )
    return {"entries": out}


def _normalize_note_method(raw: Optional[str]) -> str:
    s = (raw or "").strip().lower()
    if s in {"clause", "조항", "조항심사", "sequential"}:
        return "clause"
    return "process"


def _clause_no_sort_key(clause_no: str) -> Tuple:
    """Natural sort for 4.1 / 4.2 / 6.1.2 / 8.2/8.3."""
    parts: List[Any] = []
    for token in re.split(r"[/~\-]", str(clause_no or "")):
        for p in re.split(r"[.\s]+", token.strip()):
            if not p:
                continue
            if p.isdigit():
                parts.append((0, int(p)))
            else:
                m = re.match(r"^(\d+)(.*)$", p)
                if m:
                    parts.append((0, int(m.group(1))))
                    if m.group(2):
                        parts.append((1, m.group(2)))
                else:
                    parts.append((1, p))
    return tuple(parts) if parts else ((1, str(clause_no or "")),)


def _apply_note_method_order(
    clauses: List[AuditNoteClauseItem], note_method: str
) -> List[AuditNoteClauseItem]:
    """clause=조항 순번(장 단위), process=프로세스그룹→HLS 마스터 순서 유지.

    Frontend builds distinct nav trees from note_method; here we only reorder.
    Do not overwrite process_group_name (validator syncs group_name ← process_group).
    """
    if note_method != "clause":
        # Keep process-group / HLS master order from list_clauses_for_standard_pg
        return list(clauses)
    return sorted(clauses, key=lambda c: _clause_no_sort_key(c.clause_no))


def _load_note_method(db: Session, note_id: int) -> str:
    ensure_audit_note_longtext(db)
    try:
        row = db.execute(
            text("SELECT note_method FROM audit_notes WHERE id = :id LIMIT 1"),
            {"id": note_id},
        ).first()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return "process"
    if not row or not row[0]:
        return "process"
    return _normalize_note_method(row[0])


def _save_note_method(db: Session, note_id: int, note_method: str) -> None:
    ensure_audit_note_longtext(db)
    method = _normalize_note_method(note_method)
    try:
        db.execute(
            text(
                "UPDATE audit_notes SET note_method=:m, updated_at=CURRENT_TIMESTAMP "
                "WHERE id=:id"
            ),
            {"m": method, "id": note_id},
        )
    except Exception:
        logger.exception("save note_method failed note_id=%s", note_id)
        try:
            db.rollback()
        except Exception:
            pass


def _column_exists(db: Session, table: str, column: str) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=:t AND column_name=:c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return bool(row)


def _get_or_create_note(
    db: Session, *, contract_id: int, auditor_id: int
) -> int:
    row = db.execute(
        text("SELECT id FROM audit_notes WHERE contract_id = :cid LIMIT 1"),
        {"cid": contract_id},
    ).first()
    if row:
        return int(row[0])
    db.execute(
        text(
            "INSERT INTO audit_notes "
            "(contract_id, auditor_id, status, standard_code, clause_no, dept, process, finding_type) "
            "VALUES (:cid, :aid, 'draft', '', '', '', '', 'ok')"
        ),
        {"cid": contract_id, "aid": auditor_id},
    )
    db.flush()
    row = db.execute(
        text("SELECT id FROM audit_notes WHERE contract_id = :cid LIMIT 1"),
        {"cid": contract_id},
    ).first()
    if not row:
        raise HTTPException(status_code=500, detail="심사노트 헤더 생성 실패")
    return int(row[0])


def _short_standard(standard_key: str) -> str:
    """audit_note_clauses.standard VARCHAR(20) — family 우선."""
    for s in OPERATING_STANDARDS:
        if s.standard_key == standard_key:
            return s.family_code[:20]
    return (standard_key or "")[:20]


@router.get("/standards", response_model=List[AuditNoteStandardItem])
def list_note_standards(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_auditor(current_user)
    try:
        seed_needed = True
        if _table_exists(db, "process_group_master"):
            n = db.execute(text("SELECT COUNT(*) FROM process_group_master")).scalar() or 0
            seed_needed = int(n) == 0
        if seed_needed:
            seed_process_group_masters(db)
    except Exception:
        logger.exception("process_group seed on standards list failed")
    items = []
    for s in list_operating_standards():
        pg = to_process_standard_code(s["standard_key"])
        n_pg = count_clauses_for_standard_pg(db, pg) if pg else 0
        items.append(
            AuditNoteStandardItem(
                standard_key=s["standard_key"],
                standard_code=pg,
                family_code=s["family_code"],
                display_code=s["display_code"],
                name_ko=s["name_ko"],
                clauses_status=s["clauses_status"] if n_pg else "PENDING",
                clause_count=int(n_pg),
            )
        )
    return items


@router.get("/clauses", response_model=List[AuditNoteClauseItem])
def list_note_clauses(
    standard_key: str = Query(..., description="예: QMS_2015 또는 ISO9001"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """표준별 조항 — process-group Excel masters only (no iso_clauses_master)."""
    _require_auditor(current_user)
    sk = resolve_standard_key(standard_key) or standard_key
    pg_code = to_process_standard_code(sk) or to_process_standard_code(standard_key)
    rows: List[Dict[str, Any]] = []
    if pg_code:
        rows = list_clauses_for_standard_pg(db, pg_code, standard_key=sk)
    return [
        AuditNoteClauseItem(
            id=r["id"],
            standard_key=r.get("standard_key") or sk,
            standard_code=r.get("standard_code") or pg_code,
            family_code=r.get("family_code"),
            clause_no=r["clause_no"],
            clause_topic=r.get("clause_topic") or r.get("clause_title") or "",
            clause_title=r.get("clause_topic") or r.get("clause_title") or "",
            question=r.get("question") or "",
            default_kpis=_kpi_hints(r.get("default_kpis")),
            iso_audit_kpis=_kpi_hints(
                r.get("iso_audit_kpis") or r.get("default_kpis")
            ),
            esg_kpis=_kpi_hints(r.get("esg_kpis")),
            checkpoints=[
                AuditNoteCheckpoint(title=c.get("title") or "", hint=c.get("hint") or "")
                for c in (r.get("checkpoints") or [])
            ],
            process_group_name=r.get("process_group_name") or r.get("group_name"),
            group_name=r.get("process_group_name") or r.get("group_name"),
            process_group_id=r.get("process_group_id"),
            hls_code=r.get("hls_code"),
            source=r.get("source"),
            sort_order=r.get("sort_order") or 0,
        )
        for r in rows
    ]


def _build_standards_out(
    db: Session, keys: List[str]
) -> List[AuditNoteStandardItem]:
    std_catalog = {s["standard_key"]: s for s in list_operating_standards()}
    standards_out: List[AuditNoteStandardItem] = []
    for k in keys:
        meta = std_catalog.get(k)
        pg_code = to_process_standard_code(k)
        n = count_clauses_for_standard_pg(db, pg_code) if pg_code else 0
        if meta:
            standards_out.append(
                AuditNoteStandardItem(
                    standard_key=k,
                    standard_code=pg_code,
                    family_code=meta["family_code"],
                    display_code=meta["display_code"],
                    name_ko=meta["name_ko"],
                    clauses_status=meta["clauses_status"],
                    clause_count=int(n),
                )
            )
        else:
            standards_out.append(
                AuditNoteStandardItem(
                    standard_key=k,
                    standard_code=pg_code,
                    family_code=k.split("_")[0],
                    display_code=k,
                    name_ko=k,
                    clause_count=int(n),
                )
            )
    return standards_out


def _row_to_clause_item(
    r: Dict[str, Any],
    *,
    saved_map: Dict[str, Any],
    ncr_map: Dict[str, Any],
    plan_items: Optional[List[Dict[str, Any]]] = None,
) -> AuditNoteClauseItem:
    saved = saved_map.get(r["clause_no"])
    ncr = ncr_map.get(r["clause_no"])
    kpi_values: Dict[str, str] = {}
    if saved and saved.get("kpi_json"):
        try:
            parsed = json.loads(saved["kpi_json"])
            if isinstance(parsed, dict):
                kpi_values = {
                    str(k): ("" if v is None else str(v)) for k, v in parsed.items()
                }
        except Exception:
            pass
    note_text = None
    verdict = None
    saved_at = None
    if saved:
        note_text = saved.get("finding") or saved.get("evidence")
        verdict = saved.get("verdict")
        saved_at = saved.get("updated_at")
    topic = r.get("clause_topic") or r.get("clause_title") or ""
    pg_name = r.get("process_group_name") or r.get("group_name")
    autofill = resolve_plan_autofill(
        plan_items or [],
        clause_no=r.get("clause_no"),
        process_group_id=r.get("process_group_id"),
        process_group_name=pg_name,
    )
    return AuditNoteClauseItem(
        id=r["id"],
        standard_key=r["standard_key"],
        standard_code=r.get("standard_code"),
        family_code=r.get("family_code"),
        clause_no=r["clause_no"],
        clause_topic=topic,
        clause_title=topic,
        question=r.get("question") or "",
        default_kpis=_kpi_hints(r.get("default_kpis")),
        iso_audit_kpis=_kpi_hints(r.get("iso_audit_kpis") or r.get("default_kpis")),
        esg_kpis=_kpi_hints(r.get("esg_kpis")),
        checkpoints=[
            AuditNoteCheckpoint(
                title=c.get("title") or "", hint=c.get("hint") or ""
            )
            for c in (r.get("checkpoints") or [])
        ],
        process_group_name=pg_name,
        group_name=pg_name,
        process_group_id=r.get("process_group_id"),
        hls_code=r.get("hls_code"),
        source=r.get("source"),
        sort_order=r.get("sort_order") or 0,
        plan_dept=autofill.get("dept"),
        plan_process=autofill.get("process"),
        verdict=verdict,
        note_text=note_text,
        kpi_values=kpi_values,
        ncr_grade=(ncr.get("grade") if ncr else None),
        ncr_fact=(ncr.get("description") if ncr else None),
        ncr_requirement=(ncr.get("requirement") if ncr else None),
        ncr_root_cause=(ncr.get("root_cause") if ncr else None),
        ncr_audit_date=(
            str(ncr.get("reported_at"))[:10] if ncr and ncr.get("reported_at") else None
        ),
        ncr_auditor_name=(ncr.get("auditor_name") if ncr else None),
        ncr_dept=(ncr.get("dept") if ncr else None),
        ncr_request_date=(
            str(ncr.get("request_date"))[:10] if ncr and ncr.get("request_date") else None
        ),
        ncr_due_date=(
            str(ncr.get("due_date"))[:10] if ncr and ncr.get("due_date") else None
        ),
        ncr_esg_tags=_parse_esg_tags(ncr.get("esg_tags") if ncr else None),
        saved_at=saved_at,
    )


def _clauses_from_master(
    db: Session,
    sk: str,
    *,
    saved_map: Optional[Dict[str, Any]] = None,
    ncr_map: Optional[Dict[str, Any]] = None,
    plan_items: Optional[List[Dict[str, Any]]] = None,
) -> tuple:
    """Process-group Excel masters only — never iso_clauses_master / 환경심층."""
    saved_map = saved_map or {}
    ncr_map = ncr_map or {}
    pg_code = to_process_standard_code(sk)
    master: List[Dict[str, Any]] = []
    source = "process_group"
    if pg_code:
        try:
            master = list_clauses_for_standard_pg(db, pg_code, standard_key=sk)
        except Exception:
            logger.exception("process-group clause load failed for %s", sk)
            master = []
    clauses_out = [
        _row_to_clause_item(
            r, saved_map=saved_map, ncr_map=ncr_map, plan_items=plan_items
        )
        for r in master
    ]
    return clauses_out, source, pg_code


def _scope_message(scope_info: Dict[str, Any]) -> str:
    mode = scope_info.get("scope_mode")
    if mode == "no_plan" or scope_info.get("plan_empty"):
        if scope_info.get("is_lead"):
            return (
                "인증심사 계획서에 배정된 공정/조항이 없습니다. "
                "계획서 항목을 등록한 뒤 심사노트를 작성하세요. "
                "(팀장: 심사팀회의에서는 전체 팀 배정분 조회)"
            )
        return (
            "인증심사 계획서에 배정된 공정/조항이 없습니다. "
            "배정된 항목이 없으면 조항 목록이 표시되지 않습니다."
        )
    if mode == "team_meeting":
        return "심사팀회의 — 팀 전체 배정 공정/조항 (부적합 정도 판정용)"
    n = int(scope_info.get("scope", {}).get("item_count") or 0)
    return f"계획서 배정 {n}건 — 본인 담당 공정/조항만 표시"


def _preview_session(
    db: Session,
    standard_key: Optional[str],
    note_method: Optional[str] = None,
) -> AuditNoteSessionOut:
    """배정/계약 없이 process-group 조항으로 UI 미리보기."""
    sk = resolve_standard_key(standard_key) if standard_key else None
    if not sk:
        sk = "QMS_2015"
        # fallback if catalog order differs
        for s in OPERATING_STANDARDS:
            if s.standard_key == "QMS_2015":
                break
        else:
            for s in OPERATING_STANDARDS:
                if s.clauses_status == "READY":
                    sk = s.standard_key
                    break

    # All READY operating standards selectable in preview
    keys: List[str] = []
    seen: Set[str] = set()
    for s in list_operating_standards():
        k = s["standard_key"]
        if k not in seen:
            seen.add(k)
            keys.append(k)
    if sk not in keys:
        keys = [sk] + keys

    # Prefer process-group seed; auto-seed if empty
    if _table_exists(db, "process_group_master"):
        n = db.execute(text("SELECT COUNT(*) FROM process_group_master")).scalar() or 0
        if int(n) == 0:
            try:
                seed_process_group_masters(db)
            except Exception:
                logger.exception("auto-seed process_group masters failed")
    else:
        try:
            seed_process_group_masters(db)
        except Exception:
            logger.exception("auto-seed process_group masters failed")
    ensure_audit_note_longtext(db)

    method = _normalize_note_method(note_method or "process")
    standards_out = _build_standards_out(db, keys)
    clauses_out, clause_source, pg_code = _clauses_from_master(db, sk)
    clauses_out = _apply_note_method_order(clauses_out, method)
    iv_templates = _interview_templates_out([sk] if sk else keys[:1])
    # Preview: treat multi-select catalog as 통합 가능 (선택 표준 기준 표시)
    amode, amode_label = "single", "단일심사"
    return AuditNoteSessionOut(
        note_id=None,
        contract_id=None,
        company_id=None,
        company_name="미리보기 (배정 없음)",
        standard_key=sk,
        standards=standards_out,
        status="preview",
        clauses=clauses_out,
        preview=True,
        preview_message=(
            "미리보기(배정 없음) — 전체 운영표준 선택 가능. "
            "실제 배정 세션에서는 계획서 배정 + 보유/신청 표준만 표시됩니다. DB 미저장."
        ),
        process_standard_code=pg_code,
        clause_source=clause_source,
        standards_filter="preview",
        note_method=method,
        audit_mode=amode,
        audit_mode_label=amode_label,
        audit_type=None,
        auditor_name=None,
        is_lead=False,
        team_meeting=False,
        plan_id=None,
        plan_empty=False,
        plan_item_count=0,
        scope_mode="preview",
        scope_message="미리보기 — 계획서 스코프 미적용",
        interview_content="",
        interview_templates=iv_templates,
        interview_entries=[],
    )


@router.get("/session", response_model=AuditNoteSessionOut)
def get_note_session(
    contract_id: Optional[int] = Query(
        None, description="없으면 preview 모드 (process-group masters)"
    ),
    standard_key: Optional[str] = Query(None),
    preview: bool = Query(False, description="강제 미리보기"),
    note_method: Optional[str] = Query(
        None, description="clause=조항심사 | process=프로세스심사"
    ),
    team_meeting: bool = Query(
        False,
        description="심사팀장 전용 — 팀 전체 계획서 배정 공정/조항 조회 (심사팀회의)",
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_auditor(current_user)

    if preview or not contract_id:
        return _preview_session(db, standard_key, note_method=note_method)

    auditor = _get_auditor(db, current_user.id)
    if not _table_exists(db, "contracts"):
        raise HTTPException(status_code=404, detail="계약 테이블이 없습니다.")
    contract = db.query(Contracts).filter(Contracts.id == contract_id).first()
    if not contract:
        # Soft fallback: open preview instead of hard 404 so UI remains reviewable
        return _preview_session(db, standard_key, note_method=note_method)

    keys, filter_mode = _session_standard_keys(db, contract)
    sk = resolve_standard_key(standard_key) if standard_key else None
    if keys:
        # Strict filter: do not inject standards outside company/contract set
        if not sk or sk not in keys:
            # Allow same-family remap (e.g. request EMS_2026 when only EMS_2015 held)
            if sk:
                fam = _family_of(sk)
                fam_hit = next((k for k in keys if _family_of(k) == fam), None)
                sk = fam_hit or keys[0]
            else:
                sk = keys[0]
    else:
        # No held/applied/contract standards — keep UI open but empty selector
        if not sk:
            sk = "QMS_2015"
        keys = []
        filter_mode = "none"

    note_id = _get_or_create_note(db, contract_id=contract_id, auditor_id=auditor.id)
    db.commit()

    company_name = None
    company_id = getattr(contract, "company_id", None)
    if company_id and _table_exists(db, "companies"):
        co = db.query(Companies).filter(Companies.id == company_id).first()
        if co:
            company_name = co.name

    standards_out = _build_standards_out(db, keys if keys else ([sk] if sk else []))
    short = _short_standard(sk)

    saved_map: Dict[str, Any] = {}
    if _table_exists(db, "audit_note_clauses"):
        saved_rows = db.execute(
            text(
                "SELECT id, clause_id, clause_label, verdict, evidence, finding, "
                "kpi_json, updated_at FROM audit_note_clauses "
                "WHERE note_id = :nid AND (standard = :std OR standard = :sk)"
            ),
            {"nid": note_id, "std": short, "sk": sk[:20]},
        ).mappings().all()
        for sr in saved_rows:
            saved_map[str(sr["clause_id"])] = sr

    ncr_map: Dict[str, Any] = {}
    ensure_ncr_extra_columns(db)
    if _table_exists(db, "audit_note_ncr"):
        ncrs = db.execute(
            text(
                "SELECT id, clause, grade, description, title, requirement, root_cause, "
                "due_date, request_date, reported_at, auditor_name, dept, esg_tags, evidence "
                "FROM audit_note_ncr "
                "WHERE note_id = :nid AND standard = :std AND status != 'closed'"
            ),
            {"nid": note_id, "std": short},
        ).mappings().all()
        for n in ncrs:
            ncr_map[str(n["clause"])] = n

    # 계획서 스코프 (본인 배정 / 팀장 심사팀회의)
    auditor_name = (getattr(auditor, "name", None) or "").strip() or None
    scope_info = load_engagement_plan_scope(
        db,
        contract_id=int(contract_id),
        auditor_id=int(auditor.id),
        auditor_name=auditor_name,
        team_meeting=bool(team_meeting),
    )
    plan_items = scope_info.get("items") or []

    ensure_audit_note_longtext(db)
    clauses_out, clause_source, pg_code = _clauses_from_master(
        db, sk, saved_map=saved_map, ncr_map=ncr_map, plan_items=plan_items
    )
    # Strict plan filter — empty plan ⇒ empty nav (never full master dump)
    clauses_out = filter_clauses_by_plan(clauses_out, plan_items)

    # 심사방식: query overrides persisted; else load from note header
    if note_method:
        method = _normalize_note_method(note_method)
        _save_note_method(db, note_id, method)
        db.commit()
    else:
        method = _load_note_method(db, note_id)
    clauses_out = _apply_note_method_order(clauses_out, method)

    status_row = db.execute(
        text("SELECT status FROM audit_notes WHERE id = :id"),
        {"id": note_id},
    ).first()

    # 면담: structural fields + single Q/A box (v15-aligned)
    iv_stds = keys if keys else ([sk] if sk else [])
    iv_templates = _interview_templates_out(iv_stds)
    iv_entries = _load_interview_entries(db, note_id)
    iv_content = _load_interview_content(db, note_id)

    # 단일/통합 — contracts.audit_mode (+ 표준 패키지 수)
    package_keys = keys if keys else ([sk] if sk else [])
    amode, amode_label = _resolve_audit_mode(contract, package_keys)
    audit_type = getattr(contract, "audit_type", None)

    return AuditNoteSessionOut(
        note_id=note_id,
        contract_id=contract_id,
        company_id=company_id,
        company_name=company_name,
        standard_key=sk,
        standards=standards_out,
        status=(status_row[0] if status_row else "draft") or "draft",
        clauses=clauses_out,
        preview=False,
        preview_message=None,
        process_standard_code=pg_code,
        clause_source=clause_source,
        standards_filter=filter_mode,
        note_method=method,
        audit_mode=amode,
        audit_mode_label=amode_label,
        audit_type=str(audit_type) if audit_type else None,
        auditor_name=auditor_name,
        is_lead=bool(scope_info.get("is_lead")),
        team_meeting=bool(scope_info.get("team_meeting")),
        plan_id=scope_info.get("plan_id"),
        plan_empty=bool(scope_info.get("plan_empty")),
        plan_item_count=int((scope_info.get("scope") or {}).get("item_count") or 0),
        scope_mode=scope_info.get("scope_mode"),
        scope_message=_scope_message(scope_info),
        interview_content=iv_content,
        interview_templates=iv_templates,
        interview_entries=iv_entries,
    )


@router.put("/clause", response_model=AuditNoteClauseSaveOut)
def save_note_clause(
    payload: AuditNoteClauseSaveIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """조항 노트 저장. KPI 값은 비어 있어도 Validation 없이 성공."""
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)

    if not _table_exists(db, "audit_notes") or not _table_exists(db, "audit_note_clauses"):
        raise HTTPException(status_code=500, detail="심사노트 테이블이 없습니다.")

    contract = db.query(Contracts).filter(Contracts.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    sk = resolve_standard_key(payload.standard_key) or payload.standard_key
    short = _short_standard(sk)
    std_code = (
        (payload.standard_code or "").strip()
        or to_process_standard_code(sk)
        or short
    )
    clause_no = (payload.clause_no or "").strip()
    if not clause_no:
        raise HTTPException(status_code=400, detail="조항번호가 필요합니다.")
    clause_topic = (
        (payload.clause_topic or payload.clause_title or "").strip() or clause_no
    )[:255]
    process_group_id = (payload.process_group_id or "").strip() or None
    hls_code = (payload.hls_code or "").strip() or None

    # Normalize verdict / grade — KPI not validated
    grade = (payload.ncr_grade or "").strip().lower() or None
    if grade in ("obs",):
        grade = "observation"
    verdict = (payload.verdict or "").strip()
    if grade and grade in _VERDICT_BY_GRADE:
        verdict = _VERDICT_BY_GRADE[grade]
    if verdict not in {
        _VERDICT_CONFORM,
        "중대한부적합",
        "경미한부적합",
        "관찰사항",
        "해당없음",
    }:
        if verdict in ("conform", "ok", "적합"):
            verdict = _VERDICT_CONFORM
        elif verdict in ("major",):
            verdict = "중대한부적합"
            grade = "major"
        elif verdict in ("minor",):
            verdict = "경미한부적합"
            grade = "minor"
        elif verdict in ("observation", "obs", "관찰"):
            verdict = "관찰사항"
            grade = "observation"
        else:
            verdict = _VERDICT_CONFORM

    # Optional KPI map keyed by kpi_id — blank values kept as "" (not an error)
    kpi_map: Dict[str, str] = {}
    for item in payload.kpi_values or []:
        key = ((item.kpi_id or item.key) or "").strip()
        if not key:
            continue
        kpi_map[key] = "" if item.value is None else str(item.value).strip()

    if not _column_exists_kpi_json(db):
        try:
            db.execute(text("ALTER TABLE audit_note_clauses ADD COLUMN kpi_json TEXT NULL"))
            db.commit()
        except Exception:
            db.rollback()

    note_id = _get_or_create_note(
        db, contract_id=payload.contract_id, auditor_id=auditor.id
    )

    note_text = payload.note_text or ""
    if verdict != _VERDICT_CONFORM and (payload.ncr_fact or "").strip():
        # keep fact also in finding for report readability
        if not note_text.strip():
            note_text = (payload.ncr_fact or "").strip()

    existing = db.execute(
        text(
            "SELECT id FROM audit_note_clauses "
            "WHERE note_id = :nid AND clause_id = :cno AND standard = :std LIMIT 1"
        ),
        {"nid": note_id, "cno": clause_no, "std": short},
    ).first()

    kpi_json = json.dumps(kpi_map, ensure_ascii=False)
    label = clause_topic[:200]
    ensure_audit_note_longtext(db)
    write_method = _normalize_note_method(payload.audit_method) if payload.audit_method else None
    has_method_col = _column_exists(db, "audit_note_clauses", "audit_method")
    has_std_code = _column_exists(db, "audit_note_clauses", "standard_code")
    has_pg = _column_exists(db, "audit_note_clauses", "process_group_id")
    has_hls = _column_exists(db, "audit_note_clauses", "hls_code")
    has_topic = _column_exists(db, "audit_note_clauses", "clause_topic")

    master_set_parts: List[str] = []
    master_params: Dict[str, Any] = {}
    if has_std_code:
        master_set_parts.append("standard_code=:std_code")
        master_params["std_code"] = (std_code or "")[:30] or None
    if has_pg:
        master_set_parts.append("process_group_id=:pg_id")
        master_params["pg_id"] = process_group_id
    if has_hls:
        master_set_parts.append("hls_code=:hls")
        master_params["hls"] = hls_code
    if has_topic:
        master_set_parts.append("clause_topic=:topic")
        master_params["topic"] = clause_topic
    master_sql = (", " + ", ".join(master_set_parts)) if master_set_parts else ""
    master_ins_cols = ""
    master_ins_vals = ""
    if has_std_code:
        master_ins_cols += ", standard_code"
        master_ins_vals += ", :std_code"
    if has_pg:
        master_ins_cols += ", process_group_id"
        master_ins_vals += ", :pg_id"
    if has_hls:
        master_ins_cols += ", hls_code"
        master_ins_vals += ", :hls"
    if has_topic:
        master_ins_cols += ", clause_topic"
        master_ins_vals += ", :topic"

    if existing:
        clause_row_id = int(existing[0])
        base_params = {
            "id": clause_row_id,
            "label": label,
            "verdict": verdict,
            "finding": note_text,
            "evidence": (payload.ncr_fact or note_text or None),
            "kpi_json": kpi_json,
            "aid": auditor.id,
            **master_params,
        }
        if has_method_col and write_method:
            db.execute(
                text(
                    "UPDATE audit_note_clauses SET "
                    "clause_label=:label, verdict=:verdict, finding=:finding, "
                    "evidence=:evidence, kpi_json=:kpi_json, auditor_id=:aid, "
                    f"audit_method=:amethod{master_sql}, updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=:id"
                ),
                {**base_params, "amethod": write_method},
            )
        else:
            db.execute(
                text(
                    "UPDATE audit_note_clauses SET "
                    "clause_label=:label, verdict=:verdict, finding=:finding, "
                    f"evidence=:evidence, kpi_json=:kpi_json, auditor_id=:aid{master_sql}, "
                    "updated_at=CURRENT_TIMESTAMP "
                    "WHERE id=:id"
                ),
                base_params,
            )
        if write_method:
            _save_note_method(db, note_id, write_method)
    else:
        base_params = {
            "nid": note_id,
            "std": short,
            "cno": clause_no,
            "label": label,
            "verdict": verdict,
            "evidence": (payload.ncr_fact or note_text or None),
            "finding": note_text,
            "aid": auditor.id,
            "kpi_json": kpi_json,
            **master_params,
        }
        if has_method_col and write_method:
            db.execute(
                text(
                    "INSERT INTO audit_note_clauses "
                    "(note_id, standard, clause_id, clause_label, verdict, evidence, finding, "
                    f" auditor_id, kpi_json, audit_method{master_ins_cols}) "
                    "VALUES "
                    "(:nid, :std, :cno, :label, :verdict, :evidence, :finding, :aid, :kpi_json, "
                    f":amethod{master_ins_vals})"
                ),
                {**base_params, "amethod": write_method},
            )
        else:
            db.execute(
                text(
                    "INSERT INTO audit_note_clauses "
                    "(note_id, standard, clause_id, clause_label, verdict, evidence, finding, "
                    f" auditor_id, kpi_json{master_ins_cols}) "
                    "VALUES "
                    "(:nid, :std, :cno, :label, :verdict, :evidence, :finding, :aid, "
                    f":kpi_json{master_ins_vals})"
                ),
                base_params,
            )
        if write_method:
            _save_note_method(db, note_id, write_method)
        row = db.execute(
            text(
                "SELECT id FROM audit_note_clauses "
                "WHERE note_id = :nid AND clause_id = :cno AND standard = :std "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"nid": note_id, "cno": clause_no, "std": short},
        ).first()
        clause_row_id = int(row[0]) if row else None

    ensure_ncr_extra_columns(db)
    ncr_id = None
    if verdict != _VERDICT_CONFORM and grade in {"major", "minor", "observation"}:
        fact = (payload.ncr_fact or note_text or "").strip() or f"{clause_no} 부적합/관찰"
        title = f"{short} {clause_no} {clause_topic}".strip()[:300]
        req = (payload.ncr_requirement or "").strip() or None
        cause = (payload.ncr_root_cause or "").strip() or None
        due = (payload.ncr_due_date or "").strip() or None
        req_date = (payload.ncr_request_date or "").strip() or None
        reported = (payload.ncr_audit_date or "").strip() or None
        auditor_name = (payload.ncr_auditor_name or "").strip() or None
        dept = (payload.ncr_dept or "").strip() or None
        esg_json = json.dumps(payload.ncr_esg_tags or [], ensure_ascii=False)
        # upsert open NCR for this clause
        existing_ncr = db.execute(
            text(
                "SELECT id FROM audit_note_ncr "
                "WHERE note_id=:nid AND standard=:std AND clause=:cno "
                "AND status != 'closed' ORDER BY id DESC LIMIT 1"
            ),
            {"nid": note_id, "std": short, "cno": clause_no},
        ).first()
        if existing_ncr:
            ncr_id = int(existing_ncr[0])
            db.execute(
                text(
                    "UPDATE audit_note_ncr SET grade=:grade, title=:title, "
                    "description=:desc, requirement=:req, root_cause=:cause, "
                    "due_date=:due, request_date=:req_date, reported_at=:reported, "
                    "auditor_name=:aname, dept=:dept, esg_tags=:esg, evidence=:evidence, "
                    "updated_at=CURRENT_TIMESTAMP WHERE id=:id"
                ),
                {
                    "id": ncr_id,
                    "grade": grade,
                    "title": title,
                    "desc": fact,
                    "req": req,
                    "cause": cause,
                    "due": due,
                    "req_date": req_date,
                    "reported": reported,
                    "aname": auditor_name,
                    "dept": dept,
                    "esg": esg_json,
                    "evidence": fact,
                },
            )
        else:
            db.execute(
                text(
                    "INSERT INTO audit_note_ncr "
                    "(note_id, clause_id_ref, grade, standard, clause, title, description, "
                    " requirement, root_cause, due_date, request_date, reported_at, "
                    " auditor_name, dept, esg_tags, evidence, status) "
                    "VALUES (:nid, :cref, :grade, :std, :cno, :title, :desc, "
                    " :req, :cause, :due, :req_date, :reported, :aname, :dept, :esg, :evidence, 'open')"
                ),
                {
                    "nid": note_id,
                    "cref": clause_row_id,
                    "grade": grade,
                    "std": short,
                    "cno": clause_no,
                    "title": title,
                    "desc": fact,
                    "req": req,
                    "cause": cause,
                    "due": due,
                    "req_date": req_date,
                    "reported": reported,
                    "aname": auditor_name,
                    "dept": dept,
                    "esg": esg_json,
                    "evidence": fact,
                },
            )
            row = db.execute(
                text(
                    "SELECT id FROM audit_note_ncr WHERE note_id=:nid AND clause=:cno "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"nid": note_id, "cno": clause_no},
            ).first()
            ncr_id = int(row[0]) if row else None

        # also mirror dept onto audit_notes header when present
        if dept:
            try:
                db.execute(
                    text("UPDATE audit_notes SET dept=:dept WHERE id=:id"),
                    {"id": note_id, "dept": dept[:100]},
                )
            except Exception:
                pass
    elif verdict == _VERDICT_CONFORM and _table_exists(db, "audit_note_ncr"):
        # mark open NCRs for this clause as closed when judged conform
        db.execute(
            text(
                "UPDATE audit_note_ncr SET status='closed', closed_at=CURRENT_TIMESTAMP, "
                "updated_at=CURRENT_TIMESTAMP "
                "WHERE note_id=:nid AND standard=:std AND clause=:cno AND status!='closed'"
            ),
            {"nid": note_id, "std": short, "cno": clause_no},
        )

    # audit_notes.standard_code ← master standard_code (ISO9001…), not platform key
    params_hdr = {
        "id": note_id,
        "sk": (std_code or sk)[:50],
        "cno": clause_no[:20],
    }
    sql_hdr = (
        "UPDATE audit_notes SET status='in_progress', updated_at=CURRENT_TIMESTAMP, "
        "standard_code=:sk, clause_no=:cno"
    )
    if getattr(payload, "ncr_audit_date", None):
        sql_hdr += ", audit_date=:adate"
        params_hdr["adate"] = payload.ncr_audit_date
    sql_hdr += " WHERE id=:id"
    db.execute(text(sql_hdr), params_hdr)
    db.commit()

    return AuditNoteClauseSaveOut(
        ok=True,
        note_id=note_id,
        clause_row_id=clause_row_id,
        ncr_id=ncr_id,
        message="저장되었습니다." + (" (KPI 미입력 허용)" if not any(kpi_map.values()) else ""),
    )


def _column_exists_kpi_json(db: Session) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name='audit_note_clauses' "
            "AND column_name='kpi_json' LIMIT 1"
        )
    ).first()
    return bool(row)


@router.put("/method", response_model=AuditNoteMethodOut)
def save_note_method(
    payload: AuditNoteMethodIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사방식(조항심사/프로세스심사) 저장."""
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)
    if not _table_exists(db, "audit_notes"):
        raise HTTPException(status_code=500, detail="심사노트 테이블이 없습니다.")
    contract = db.query(Contracts).filter(Contracts.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")
    note_id = _get_or_create_note(
        db, contract_id=payload.contract_id, auditor_id=auditor.id
    )
    method = _normalize_note_method(payload.note_method)
    _save_note_method(db, note_id, method)
    db.commit()
    return AuditNoteMethodOut(ok=True, note_id=note_id, note_method=method)


@router.get("/matrix", response_model=AuditMatrixOut)
def get_audit_matrix(
    contract_id: int = Query(..., description="계약 ID"),
    standard_key: Optional[str] = Query(None),
    all_standards: bool = Query(
        False,
        description="통합심사 시 패키지 전체 표준 매트릭스 (audit_mode=integrated면 자동)",
    ),
    team_meeting: bool = Query(
        False, description="심사팀장 — 팀 전체 계획서 배정분 매트릭스"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """보고서 심사매트릭스 — 필수 조항 vs 작성 조항 (빠짐심사 점검).

    조항심사·프로세스심사 어느 쪽에서 쓰든 clause_no 단위로 집계한다.
    통합심사(audit_mode=integrated)이면 계약·보유 패키지의 모든 표준을 포함한다.
    계획서 배정 스코프를 적용한다 (팀장 심사팀회의 시 팀 전체).
    """
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)
    contract = db.query(Contracts).filter(Contracts.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    keys, _filter = _session_standard_keys(db, contract)
    sk = resolve_standard_key(standard_key) if standard_key else None
    if keys:
        if not sk or sk not in keys:
            if sk:
                fam = _family_of(sk)
                sk = next((k for k in keys if _family_of(k) == fam), keys[0])
            else:
                sk = keys[0]
    elif not sk:
        sk = "QMS_2015"

    package_keys = keys if keys else ([sk] if sk else [])
    amode, amode_label = _resolve_audit_mode(contract, package_keys)
    multi = bool(all_standards) or amode == "integrated"
    matrix_keys = package_keys if (multi and len(package_keys) >= 2) else [sk]

    auditor_name = (getattr(auditor, "name", None) or "").strip() or None
    scope_info = load_engagement_plan_scope(
        db,
        contract_id=int(contract_id),
        auditor_id=int(auditor.id),
        auditor_name=auditor_name,
        team_meeting=bool(team_meeting),
    )
    plan_items = scope_info.get("items") or []

    note_id = _get_or_create_note(
        db, contract_id=contract_id, auditor_id=auditor.id
    )
    db.commit()
    ensure_audit_note_longtext(db)
    method = _load_note_method(db, note_id)

    standards_out = _build_standards_out(db, matrix_keys)
    pg_code = to_process_standard_code(sk)

    # Load written rows for all package shorts once
    written_by_std: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if _table_exists(db, "audit_note_clauses"):
        has_am = _column_exists(db, "audit_note_clauses", "audit_method")
        cols = (
            "standard, clause_id, verdict, finding, evidence"
            + (", audit_method" if has_am else "")
        )
        rows = db.execute(
            text(
                f"SELECT {cols} FROM audit_note_clauses WHERE note_id = :nid"
            ),
            {"nid": note_id},
        ).mappings().all()
        for r in rows:
            cno = str(r["clause_id"] or "").strip()
            if not cno:
                continue
            has_text = bool(
                (r.get("finding") or "").strip() or (r.get("evidence") or "").strip()
            )
            has_verdict = bool(r.get("verdict"))
            if not (has_text or has_verdict):
                continue
            std_key = str(r.get("standard") or "").strip()
            written_by_std.setdefault(std_key, {})[cno] = dict(r)

    cells: List[AuditMatrixCell] = []
    missing: List[str] = []
    written_count = 0
    for msk in matrix_keys:
        master, _src, m_pg = _clauses_from_master(db, msk, plan_items=plan_items)
        master = filter_clauses_by_plan(master, plan_items)
        master = sorted(master, key=lambda c: _clause_no_sort_key(c.clause_no))
        short = _short_standard(msk)
        # Match by family short and full key prefix
        written_map: Dict[str, Dict[str, Any]] = {}
        for cand in (short, msk[:20], (m_pg or "")[:20]):
            if cand and cand in written_by_std:
                written_map.update(written_by_std[cand])
        for c in master:
            w = written_map.get(c.clause_no)
            is_written = bool(w)
            if is_written:
                written_count += 1
            else:
                miss_label = (
                    f"{m_pg or short}:{c.clause_no}"
                    if len(matrix_keys) > 1
                    else c.clause_no
                )
                missing.append(miss_label)
            cells.append(
                AuditMatrixCell(
                    clause_no=c.clause_no,
                    clause_topic=c.clause_topic or c.clause_title or "",
                    clause_title=c.clause_topic or c.clause_title or "",
                    standard_key=msk,
                    standard_code=c.standard_code or m_pg,
                    process_group_name=c.process_group_name or c.group_name,
                    group_name=c.process_group_name or c.group_name,
                    process_group_id=c.process_group_id,
                    required=True,
                    written=is_written,
                    verdict=(w.get("verdict") if w else None),
                    audit_method=(w.get("audit_method") if w else None),
                    missing=not is_written,
                )
            )

    required = len(cells)
    pct = round((written_count / required) * 100.0, 1) if required else 0.0
    return AuditMatrixOut(
        contract_id=contract_id,
        note_id=note_id,
        standard_key=sk,
        process_standard_code=pg_code,
        note_method=method,
        audit_mode=amode,
        audit_mode_label=amode_label,
        standards=standards_out,
        required_count=required,
        written_count=written_count,
        missing_count=len(missing),
        coverage_pct=pct,
        cells=cells,
        missing_clauses=missing,
    )


@router.put("/interviews", response_model=AuditInterviewSaveOut)
def save_note_interviews(
    payload: AuditInterviewSaveIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """면담 저장 → audit_notes.interview_json {entries:[…]} (구조 필드 + 단일 qa_content)."""
    _require_auditor(current_user)
    auditor = _get_auditor(db, current_user.id)

    if not _table_exists(db, "audit_notes"):
        raise HTTPException(status_code=500, detail="심사노트 테이블이 없습니다.")

    contract = db.query(Contracts).filter(Contracts.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="계약을 찾을 수 없습니다.")

    note_id = _get_or_create_note(
        db, contract_id=payload.contract_id, auditor_id=auditor.id
    )
    ensure_audit_note_longtext(db)

    if payload.entries:
        normalized: List[AuditInterviewEntry] = []
        for e in payload.entries:
            qa = _merge_legacy_answers_to_qa(e.answers or {}, e.qa_content)
            normalized.append(
                e.model_copy(update={"qa_content": qa or None, "answers": {}})
            )
        blob = json.dumps(_entries_to_storage(normalized), ensure_ascii=False)
    else:
        # Legacy single-text fallback
        content = "" if payload.content is None else str(payload.content)
        blob = json.dumps({"content": content}, ensure_ascii=False)
    db.execute(
        text(
            "UPDATE audit_notes SET interview_json=:j, status='in_progress', "
            "updated_at=CURRENT_TIMESTAMP WHERE id=:id"
        ),
        {"j": blob, "id": note_id},
    )
    db.commit()
    return AuditInterviewSaveOut(
        ok=True, note_id=note_id, message="면담이 저장되었습니다."
    )


@router.post("/formalize", response_model=AuditNoteFormalizeOut)
def formalize_note_text(
    payload: AuditNoteFormalizeIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """거친 심사노트를 표준 요구사항 정렬 보고서 문장으로 정형화."""
    _require_auditor(current_user)
    rough = (payload.rough_text or "").strip()
    if not rough:
        raise HTTPException(status_code=400, detail="정형화할 원문이 필요합니다.")

    api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("COMPLAIS_OPENAI_API_KEY") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    context_bits = []
    if payload.standard_key:
        context_bits.append(f"표준: {payload.standard_key}")
    if payload.clause_no:
        context_bits.append(f"조항: {payload.clause_no}")
    if payload.clause_title:
        context_bits.append(f"조항제목: {payload.clause_title}")
    if payload.question:
        context_bits.append(f"심사질문: {payload.question}")
    context = " / ".join(context_bits)

    if not api_key:
        # Graceful stub — deterministic tidy-up so UI still works
        cleaned = " ".join(rough.split())
        stub = (
            f"[초안·AI 미설정] {context + ' — ' if context else ''}"
            f"현장 확인 결과, {cleaned} "
            f"해당 사항은 관련 표준 요구사항과의 정합성을 기준으로 추가 검토가 필요하다."
        )
        return AuditNoteFormalizeOut(
            formalized_text=stub,
            configured=False,
            message="OPENAI_API_KEY가 설정되지 않아 로컬 초안만 반환했습니다. .env에 키를 설정하면 실제 AI 정형화가 동작합니다.",
        )

    system = (
        "당신은 ISO 경영시스템 인증 심사 보고서 작성 보조자입니다. "
        "심사원이 거칠게 적은 현장 노트를, 표준 요구사항에 부합하는 격식 있는 한국어 보고서 문장으로 "
        "정형화하세요. 사실을 과장하거나 없는 증거를 만들지 마세요. "
        "출력은 정형화된 문장만 반환하세요."
    )
    user_msg = f"{context}\n\n원문:\n{rough}" if context else f"원문:\n{rough}"

    body = {
        "model": model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text_out = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not text_out:
            raise RuntimeError("empty AI response")
        return AuditNoteFormalizeOut(
            formalized_text=text_out,
            configured=True,
            message="AI 문장 정형화 완료",
        )
    except Exception as exc:
        logger.warning("AI formalize failed: %s", exc)
        return AuditNoteFormalizeOut(
            formalized_text="",
            configured=True,
            message=f"AI 호출에 실패했습니다: {exc.__class__.__name__}",
        )


@router.get("/process-groups", response_model=ProcessGroupNavOut)
def get_process_group_nav(
    standard_code: Optional[str] = Query(
        None, description="예: ISO9001 또는 QMS_2015 — 표준별 조항 매핑 포함"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """프로세스그룹 네비게이션 (HLS + 표준별 조항 매핑)."""
    _require_auditor(current_user)
    # Auto-seed if empty (idempotent)
    if _table_exists(db, "process_group_master"):
        n = db.execute(text("SELECT COUNT(*) FROM process_group_master")).scalar() or 0
        if int(n) == 0:
            try:
                seed_process_group_masters(db)
            except Exception:
                logger.exception("auto-seed process_group masters failed")
    else:
        try:
            seed_process_group_masters(db)
        except Exception:
            logger.exception("auto-seed process_group masters failed")

    resolved = to_process_standard_code(standard_code) or standard_code
    tree = list_process_group_tree(db, standard_code=resolved)
    groups = [
        ProcessGroupItem(
            process_group_id=g["process_group_id"],
            process_group_name=g["process_group_name"],
            hls_scope_desc=g.get("hls_scope_desc"),
            hls_codes=[
                ProcessGroupHlsItem(
                    hls_code=h["hls_code"],
                    checkpoints_summary=h.get("checkpoints_summary"),
                )
                for h in (g.get("hls_codes") or [])
            ],
            standard_clauses=[
                ProcessGroupClauseItem(
                    actual_clause_no=c["actual_clause_no"],
                    clause_topic=c.get("clause_topic"),
                    guide_note=c.get("guide_note"),
                )
                for c in (g.get("standard_clauses") or [])
            ],
        )
        for g in tree
    ]
    return ProcessGroupNavOut(
        standard_code=resolved,
        process_groups=groups,
        standards=list_standard_masters_pg(db),
    )


@router.get("/audit-kpis", response_model=List[AuditKpiMasterItem])
def get_audit_kpi_master(
    hls_code: Optional[str] = Query(None),
    standard_code: Optional[str] = Query(
        None, description="COMMON + 해당 표준 KPI"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사노트용 KPI 마스터 (audit_kpi_master; ESG kpi_master와 별개)."""
    _require_auditor(current_user)
    rows = list_audit_kpis(db, hls_code=hls_code, standard_code=standard_code)
    return [AuditKpiMasterItem(**r) for r in rows]
