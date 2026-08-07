"""Certification application MD helpers — Python engine (no PHP iframe)."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.models.certification import (
    CertificationApplicationMdReviews,
    CertificationApplications,
)
from app.models.company import Companies
from app.services.md_calculator import (
    CalcInput,
    apply_iaf_to_input,
    base_md_for_audit_type,
    calculate_base_md,
    calculate_review_md,
    map_api_audit_type_to_engine,
    resolve_iaf,
)

_STD_RE = re.compile(
    r"(9001|14001|45001|27001|22000|50001|13485|22301|37001|37301)",
    re.I,
)


def to_md_std_code(raw: Any) -> str:
    s = str(raw or "").strip()
    m = _STD_RE.search(s)
    if m:
        return m.group(1).lower()
    return re.sub(r"[^0-9a-z-]", "", s.lower())


def parse_standards_json(raw: Optional[str]) -> List[Any]:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def parse_codes_json(raw: Optional[str]) -> List[str]:
    """Parse JSON array or comma-separated string into unique code list."""
    out: List[str] = []
    if not raw:
        return out
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            for x in data:
                c = str(x).strip()
                if c and c not in out:
                    out.append(c)
            return out
        if isinstance(data, str) and data.strip():
            raw = data
    except Exception:
        pass
    for part in str(raw).replace(";", ",").split(","):
        c = part.strip()
        if c and c not in out:
            out.append(c)
    return out


def extract_std_codes(standards: Sequence[Any]) -> List[str]:
    out: List[str] = []
    for item in standards:
        if isinstance(item, dict):
            code = to_md_std_code(item.get("code") or item.get("standard") or "")
        else:
            code = to_md_std_code(item)
        if code and code not in out:
            out.append(code)
    return out


def extract_std_atype_map(
    standards: Sequence[Any],
    fallback_type: str = "initial",
    type_json: Optional[str] = None,
) -> Dict[str, str]:
    type_map: Dict[str, str] = {}
    try:
        parsed = json.loads(type_json or "{}")
        if isinstance(parsed, dict):
            for k, v in parsed.items():
                code = to_md_std_code(k)
                if code:
                    type_map[code] = map_api_audit_type_to_engine(str(v))
    except Exception:
        pass
    for item in standards:
        if isinstance(item, dict):
            code = to_md_std_code(item.get("code") or "")
            at = item.get("audit_type") or fallback_type
            if code:
                type_map[code] = map_api_audit_type_to_engine(str(at))
    return type_map


def _base_from_result(app: CertificationApplications, result: Any) -> float:
    return float(
        base_md_for_audit_type(
            (app.application_type or "INITIAL").upper(),
            result.stage1_md,
            result.stage2_md,
            result.surveillance_md,
            result.recertification_md,
            result.final_days,
        )
        or 0
    )


def compute_base_md_for_app(
    app: CertificationApplications,
    company: Optional[Companies] = None,
    *,
    ksic_codes: Optional[Sequence[str]] = None,
    iaf_codes: Optional[Sequence[str]] = None,
    site_count: Optional[int] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Compute base MD for a cert application.

    Multi-IAF rule: evaluate base MD once per applicable IAF code (complexity
    from iaf39 / ksic_iaf_map). Persist the **maximum** among those results as
    ``base_md``. Falls back to single KSIC-driven calc when no IAF codes.
    """
    standards = parse_standards_json(app.standards_json)
    std_codes = extract_std_codes(standards)
    if not std_codes:
        std_codes = ["9001"]
    atype_map = extract_std_atype_map(
        standards,
        fallback_type=app.application_type or "initial",
        type_json=app.standard_audit_types_json,
    )
    emp = int(app.employee_count or (company.employee_count if company else 0) or 0)

    ksics: List[str] = []
    if ksic_codes:
        ksics = [str(k).strip() for k in ksic_codes if str(k).strip()]
    else:
        ksics = parse_codes_json(getattr(app, "ksic_codes_json", None))
        if not ksics and app.ksic_code:
            ksics = [str(app.ksic_code).strip()]
        if not ksics and company and company.ksic_code:
            ksics = [c.strip() for c in str(company.ksic_code).split(",") if c.strip()]
    primary_ksic = ksics[0] if ksics else ""

    iafs: List[str] = []
    if iaf_codes:
        iafs = [str(i).strip() for i in iaf_codes if str(i).strip()]
    else:
        iafs = parse_codes_json(app.iaf_codes_json)
        if not iafs and company and company.iaf_code:
            iafs = [c.strip() for c in str(company.iaf_code).replace(";", ",").split(",") if c.strip()]

    mode = "integrated" if (app.audit_mode or "") == "integrated" or len(std_codes) > 1 else "single"
    engine_atype = map_api_audit_type_to_engine(app.application_type or "initial")
    sites = max(1, int(site_count or app.site_count or 1))

    def _make_input() -> CalcInput:
        return CalcInput(
            standards=list(std_codes),
            employees=max(1, emp),
            audit_type=engine_atype,
            std_atype_overrides=dict(atype_map),
            mode=mode,
            ksic_code=primary_ksic,
            site_total=sites,
            intg_level=100.0 if mode == "integrated" else 40.0,
        )

    candidates: List[Dict[str, Any]] = []

    if iafs:
        # IAF-driven: one calc per IAF complexity → take max MD
        for iaf in iafs:
            inp = _make_input()
            apply_iaf_to_input(inp, iaf)
            # auto_ksic=False so KSIC map does not overwrite IAF complexity
            result = calculate_base_md(inp, auto_ksic=False)
            base = _base_from_result(app, result)
            iaf_meta = resolve_iaf(iaf)
            candidates.append(
                {
                    "iaf_code": iaf,
                    "base_md": base,
                    "complexity": result.complexity_key,
                    "complexity_level": result.complexity_level,
                    "iaf_meta": iaf_meta,
                    "result": result,
                }
            )
    else:
        inp = _make_input()
        result = calculate_base_md(inp, auto_ksic=True)
        base = _base_from_result(app, result)
        candidates.append(
            {
                "iaf_code": result.iaf_main,
                "base_md": base,
                "complexity": result.complexity_key,
                "complexity_level": result.complexity_level,
                "iaf_meta": None,
                "result": result,
            }
        )

    if not candidates:
        return 0.0, {"error": "no_candidates", "iaf_codes": iafs, "ksic_codes": ksics}

    winner = max(candidates, key=lambda c: float(c["base_md"] or 0))
    result = winner["result"]
    base = float(winner["base_md"] or 0)

    detail = {
        "final_days": result.final_days,
        "stage1_md": result.stage1_md,
        "stage2_md": result.stage2_md,
        "surveillance_md": result.surveillance_md,
        "recertification_md": result.recertification_md,
        "complexity_level": result.complexity_level,
        "iaf_main": result.iaf_main or winner.get("iaf_code"),
        "ksic_code": result.ksic_code or primary_ksic,
        "ksic_codes": ksics,
        "iaf_codes": iafs,
        "standards": result.standards,
        "per_standard": result.per_standard,
        "detail_log": result.detail_log,
        # multi-IAF max rule provenance
        "md_rule": "max_among_iaf_complexity",
        "selected_iaf": winner.get("iaf_code"),
        "selected_base_md": base,
        "iaf_candidates": [
            {
                "iaf_code": c.get("iaf_code"),
                "base_md": c.get("base_md"),
                "complexity": c.get("complexity"),
                "complexity_level": c.get("complexity_level"),
            }
            for c in candidates
        ],
    }
    return base, detail


def upsert_md_review(
    db: Session,
    application_id: int,
    *,
    base_md: float,
    detail: Optional[Dict[str, Any]] = None,
    add_pct: int = 0,
    subtract_pct: int = 0,
    note: Optional[str] = None,
    is_design_excluded: Optional[bool] = None,
    exclusion_note: Optional[str] = None,
    reviewer_user_id: Optional[int] = None,
    reviewer_role: Optional[str] = None,
    calculated_by: Optional[str] = None,
) -> CertificationApplicationMdReviews:
    # PHP review page: ±30% always (MD11 integrated discount already in base)
    add_md, sub_md, final_md = calculate_review_md(
        base_md, add_pct, subtract_pct, is_integrated=False
    )
    now = datetime.now()
    row = (
        db.query(CertificationApplicationMdReviews)
        .filter(CertificationApplicationMdReviews.application_id == application_id)
        .first()
    )
    if row is None:
        row = CertificationApplicationMdReviews(
            application_id=application_id,
            base_md=base_md,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    row.base_md = base_md
    if detail is not None:
        # strip non-serializable result objects if any slipped in
        safe = deepcopy(detail)
        safe.pop("result", None)
        row.base_md_detail_json = json.dumps(safe, ensure_ascii=False, default=str)
        row.base_md_calculated_at = now
        if calculated_by:
            row.base_md_calculated_by = calculated_by
    row.add_pct = int(add_pct)
    row.subtract_pct = int(subtract_pct)
    row.add_md = add_md
    row.subtract_md = sub_md
    row.final_md = final_md
    if note is not None:
        row.calculation_note = note
    if is_design_excluded is not None:
        row.is_design_excluded = bool(is_design_excluded)
    if exclusion_note is not None:
        row.exclusion_note = exclusion_note
    row.reviewer_user_id = reviewer_user_id
    row.reviewer_role = reviewer_role
    row.reviewed_at = now
    row.updated_at = now
    return row


def md_review_to_dict(row: Optional[CertificationApplicationMdReviews]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {
        "application_id": row.application_id,
        "base_md": float(row.base_md or 0),
        "add_pct": int(row.add_pct or 0),
        "subtract_pct": int(row.subtract_pct or 0),
        "add_md": float(row.add_md or 0),
        "subtract_md": float(row.subtract_md or 0),
        "final_md": float(row.final_md or 0),
        "calculation_note": row.calculation_note,
        "is_design_excluded": bool(getattr(row, "is_design_excluded", False) or False),
        "exclusion_note": getattr(row, "exclusion_note", None),
        "base_md_calculated_at": row.base_md_calculated_at.isoformat()
        if row.base_md_calculated_at
        else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }
