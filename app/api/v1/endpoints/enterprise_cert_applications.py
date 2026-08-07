"""Enterprise certification application (계약 전 심사 수주 — 기업 신청).

Routes under /api/v1/enterprise-cert-applications
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.security import CurrentUser, get_current_user
from app.data.cert_questionnaire_catalog import (
    COMMON_QUESTIONS,
    INTEGRATED_CHECK_INTRO,
    INTEGRATED_CHECK_ITEMS,
    STANDARD_OPTIONS,
    catalog_for_standards,
    full_catalog_payload,
)
from app.data.company_aspects_catalog import (
    INTEGRATED_MD11_INTRO,
    aspects_catalog_payload,
)
from app.data.standards_catalog import standard_display_payload
from app.db.session import get_db
from app.models.certification import (
    Certificates,
    CertificationApplicationAnswers,
    CertificationApplications,
    CompanyKsicCodes,
)
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.master import MasterKsicIaf
from app.schemas.enterprise_cert import (
    EnterpriseCertListItem,
    EnterpriseCertSubmitIn,
    OkOut,
)
from app.services.company_aspects import (
    aspects_to_dict,
    get_company_aspects,
    upsert_company_aspects,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/enterprise-cert-applications",
    tags=["enterprise-cert-applications"],
)

AUDIT_TYPES = [
    {"value": "initial", "label": "최초심사"},
    {"value": "surveillance", "label": "사후심사"},
    {"value": "recertification", "label": "갱신심사"},
    {"value": "transfer", "label": "전환심사"},
    {"value": "scope_extension", "label": "확대심사"},
    {"value": "special", "label": "특별심사"},
]

# 최초·전환 → 전체 CB / 그 외 → 기존 CB만
_CB_SHOW_ALL_TYPES = frozenset({"initial", "transfer"})


def _safe_json(raw: Optional[str], default: Any = None) -> Any:
    if default is None:
        default = None
    try:
        return json.loads(raw) if raw else default
    except Exception:
        return default


def _digits(code: Optional[str]) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())


def _normalize_codes(raw: Any) -> List[str]:
    out: List[str] = []
    if raw is None:
        return out
    if isinstance(raw, str):
        parts = raw.replace(";", ",").split(",")
    elif isinstance(raw, (list, tuple)):
        parts = list(raw)
    else:
        parts = [raw]
    for p in parts:
        c = str(p).strip()
        if c and c not in out:
            out.append(c)
    return out


def _lookup_iafs_from_ksics(
    db: Session, ksic_codes: List[str]
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Union of mapped IAFs from master_ksic_iaf for multiple KSICs."""
    iafs: List[str] = []
    matches: List[Dict[str, Any]] = []
    for ksic_code in ksic_codes:
        clean = _digits(ksic_code)
        if len(clean) < 2:
            continue
        try:
            found = False
            for length in range(min(5, len(clean)), 1, -1):
                sub = clean[:length]
                rows = (
                    db.query(MasterKsicIaf)
                    .filter(MasterKsicIaf.ksic_code == sub)
                    .all()
                )
                if not rows and length >= 3:
                    rows = (
                        db.query(MasterKsicIaf)
                        .filter(MasterKsicIaf.ksic_code.like(sub + "%"))
                        .order_by(MasterKsicIaf.ksic_code.asc())
                        .limit(20)
                        .all()
                    )
                for row in rows:
                    if not row.iaf_code:
                        continue
                    iaf = str(row.iaf_code).strip()
                    if iaf and iaf not in iafs:
                        iafs.append(iaf)
                    matches.append(
                        {
                            "ksic_code": ksic_code,
                            "matched_ksic": str(row.ksic_code),
                            "iaf_code": iaf,
                        }
                    )
                    found = True
                if found:
                    break
        except Exception:
            logger.exception("master_ksic_iaf multi lookup soft-fail")
            try:
                db.rollback()
            except Exception:
                pass
    return iafs, matches


def _existing_cb_ids(db: Session, company_id: int) -> List[int]:
    ids: Set[int] = set()
    try:
        for (cb_id,) in (
            db.query(Contracts.cb_id)
            .filter(Contracts.company_id == company_id, Contracts.cb_id.isnot(None))
            .distinct()
            .all()
        ):
            if cb_id:
                ids.add(int(cb_id))
    except Exception:
        logger.exception("existing CB: contracts soft-fail")
        try:
            db.rollback()
        except Exception:
            pass
    try:
        rows = (
            db.query(Contracts.cb_id)
            .join(Certificates, Certificates.contract_id == Contracts.id)
            .filter(Certificates.company_id == company_id, Contracts.cb_id.isnot(None))
            .distinct()
            .all()
        )
        for (cb_id,) in rows:
            if cb_id:
                ids.add(int(cb_id))
    except Exception:
        logger.exception("existing CB: certificates soft-fail")
        try:
            db.rollback()
        except Exception:
            pass
    try:
        for (cb_id,) in (
            db.query(CertificationApplications.cb_id)
            .filter(
                CertificationApplications.company_id == company_id,
                CertificationApplications.cb_id.isnot(None),
                CertificationApplications.status.in_(
                    ["approved", "contracted", "submitted", "under_review"]
                ),
            )
            .distinct()
            .all()
        ):
            if cb_id:
                ids.add(int(cb_id))
    except Exception:
        logger.exception("existing CB: applications soft-fail")
        try:
            db.rollback()
        except Exception:
            pass
    return sorted(ids)


def _filter_cbs_for_audit_type(
    db: Session,
    company_id: int,
    audit_type: str,
) -> Tuple[List[CertificationBodies], List[int], str]:
    """
    CB visibility matrix:
    - initial (최초) + transfer (전환) → ALL active CBs
    - other types: existing CB only if any; else all
    """
    atype = (audit_type or "initial").strip().lower()
    existing = _existing_cb_ids(db, company_id)
    all_cbs = (
        db.query(CertificationBodies)
        .filter(CertificationBodies.is_active == True)  # noqa: E712
        .order_by(CertificationBodies.name.asc())
        .all()
    )
    if atype in _CB_SHOW_ALL_TYPES or not existing:
        return all_cbs, existing, "all"
    filtered = [c for c in all_cbs if c.id in set(existing)]
    if not filtered:
        return all_cbs, existing, "all"
    return filtered, existing, "existing_only"


def _company_ksic_list(db: Session, company: Companies) -> List[str]:
    codes: List[str] = []
    try:
        rows = (
            db.query(CompanyKsicCodes)
            .filter(CompanyKsicCodes.company_id == company.id)
            .order_by(CompanyKsicCodes.id.asc())
            .all()
        )
        for r in rows:
            c = (r.ksic_code or "").strip()
            if c and c not in codes:
                codes.append(c)
    except Exception:
        logger.exception("company_ksic_codes read soft-fail")
        try:
            db.rollback()
        except Exception:
            pass
    if company.ksic_code:
        for c in _normalize_codes(company.ksic_code):
            if c not in codes:
                codes.append(c)
    return codes


def _persist_company_ksic_iaf(
    db: Session,
    company: Companies,
    ksic_codes: List[str],
    iaf_codes: List[str],
    now: datetime,
) -> Tuple[List[str], List[str]]:
    ksics = [k[:20] for k in ksic_codes if k]
    iafs = [i[:20] for i in iaf_codes if i]
    if ksics:
        company.ksic_code = ksics[0][:100]
        try:
            db.query(CompanyKsicCodes).filter(
                CompanyKsicCodes.company_id == company.id
            ).delete()
            for kc in ksics:
                db.add(
                    CompanyKsicCodes(
                        company_id=company.id, ksic_code=kc[:20], created_at=now
                    )
                )
        except Exception:
            logger.exception("company_ksic_codes persist soft-fail")
    if iafs:
        company.iaf_code = ",".join(iafs)[:100]
    try:
        company.updated_at = now
    except Exception:
        pass
    return ksics, iafs


@router.get("/catalog")
def get_catalog(
    standards: Optional[str] = Query(None, description="comma-separated std codes"),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    require_enterprise_user(current_user)
    codes = [c.strip() for c in (standards or "").split(",") if c.strip()]
    payload = full_catalog_payload(codes)
    payload["audit_types"] = AUDIT_TYPES
    payload["aspects_catalog"] = aspects_catalog_payload()
    payload["integrated_check_intro"] = INTEGRATED_MD11_INTRO or INTEGRATED_CHECK_INTRO
    return payload


@router.get("/ksic-iaf")
def get_ksic_iaf(
    ksic_code: str = Query(..., min_length=2, description="one or comma-separated"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """KSIC(s) → IAF suggestion union from master_ksic_iaf (editable on form)."""
    require_enterprise_user(current_user)
    ksics = _normalize_codes(ksic_code)
    iafs, matches = _lookup_iafs_from_ksics(db, ksics)
    return {
        "ok": True,
        "ksic_codes": ksics,
        "iaf_codes": iafs,
        "iaf_code": iafs[0] if iafs else None,  # legacy
        "matches": matches,
        "suggested": bool(iafs),
    }


@router.get("/available-cbs")
def get_available_cbs(
    audit_type: str = Query("initial"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    require_enterprise_user(current_user)
    company_id = resolve_company_id(current_user)
    cbs, existing, mode = _filter_cbs_for_audit_type(db, company_id, audit_type)
    return {
        "audit_type": (audit_type or "initial").strip().lower(),
        "filter_mode": mode,
        "existing_cb_ids": existing,
        "cbs": [{"id": c.id, "name": c.name} for c in cbs],
    }


@router.get("/prefill")
def get_prefill(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Dict[str, Any]:
    require_enterprise_user(current_user)
    company_id = resolve_company_id(current_user)
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    ksic_codes = _company_ksic_list(db, company)
    iaf_codes = _normalize_codes(company.iaf_code)
    suggested_iafs, matches = _lookup_iafs_from_ksics(db, ksic_codes)
    if not iaf_codes and suggested_iafs:
        iaf_codes = suggested_iafs

    aspects_row = get_company_aspects(db, company_id)
    cbs, existing, mode = _filter_cbs_for_audit_type(db, company_id, "initial")

    return {
        "company": {
            "id": company.id,
            "name": company.name,
            "ceo_name": company.ceo_name,
            "biz_no": company.biz_no,
            "address": company.address,
            "detail_address": company.detail_address,
            "zip_code": getattr(company, "zip_code", None),
            "address_en": company.address_en,
            "name_en": company.name_en,
            "ksic_code": ksic_codes[0] if ksic_codes else None,
            "ksic_codes": ksic_codes,
            "iaf_code": iaf_codes[0] if iaf_codes else None,
            "iaf_codes": iaf_codes,
            "suggested_iaf_codes": suggested_iafs,
            "ksic_iaf_matches": matches,
            "employee_count": company.employee_count,
            "email": company.email,
            "tel": company.tel,
            "scope_kr": company.scope_kr,
            "scope_en": company.scope_en,
        },
        "aspects": aspects_to_dict(aspects_row),
        "aspects_catalog": aspects_catalog_payload(),
        "cbs": [{"id": c.id, "name": c.name} for c in cbs],
        "existing_cb_ids": existing,
        "cb_filter_mode": mode,
        "standards": STANDARD_OPTIONS,
        "audit_types": AUDIT_TYPES,
        "common_questions": COMMON_QUESTIONS,
        "integrated_check_intro": INTEGRATED_MD11_INTRO,
        "integrated_check_items": INTEGRATED_CHECK_ITEMS,
    }


@router.get("", response_model=List[EnterpriseCertListItem])
def list_my_applications(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> List[EnterpriseCertListItem]:
    require_enterprise_user(current_user)
    company_id = resolve_company_id(current_user)
    rows = (
        db.query(CertificationApplications)
        .filter(CertificationApplications.company_id == company_id)
        .order_by(CertificationApplications.id.desc())
        .limit(100)
        .all()
    )
    company = db.get(Companies, company_id)
    out: List[EnterpriseCertListItem] = []
    for a in rows:
        stds = _safe_json(a.standards_json, []) or []
        out.append(
            EnterpriseCertListItem(
                id=a.id,
                application_no=a.application_no,
                company_id=a.company_id,
                company_name=company.name if company else None,
                cb_id=a.cb_id,
                standards=[standard_display_payload(s) for s in stds],
                audit_mode=a.audit_mode,
                application_type=a.application_type,
                employee_count=a.employee_count,
                desired_audit_start=a.desired_audit_start,
                status=a.status,
                submitted_at=a.submitted_at,
            )
        )
    return out


@router.post("", response_model=OkOut, status_code=status.HTTP_201_CREATED)
def submit_application(
    payload: EnterpriseCertSubmitIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> OkOut:
    require_enterprise_user(current_user)
    company_id = resolve_company_id(current_user)
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    standards = []
    for s in payload.standards:
        code = str(s).strip()
        if code and code not in standards:
            standards.append(code)
    if not standards:
        raise HTTPException(status_code=400, detail="인증 표준을 하나 이상 선택하세요.")
    if not (payload.scope_kr or "").strip():
        raise HTTPException(status_code=400, detail="국문 인증범위를 입력하세요.")
    if payload.cb_id <= 0:
        raise HTTPException(status_code=400, detail="인증기관을 선택하세요.")
    if not payload.desired_audit_start:
        raise HTTPException(status_code=400, detail="희망 심사 시작일을 입력하세요.")

    app_type = (payload.application_type or "initial").strip().lower()
    allowed_types = {t["value"] for t in AUDIT_TYPES}
    if app_type not in allowed_types:
        raise HTTPException(status_code=400, detail="심사유형이 올바르지 않습니다.")

    avail, _, _ = _filter_cbs_for_audit_type(db, company_id, app_type)
    avail_ids = {c.id for c in avail}
    if payload.cb_id not in avail_ids:
        raise HTTPException(
            status_code=400,
            detail="선택한 인증기관은 현재 심사유형에서 선택할 수 없습니다.",
        )

    audit_mode = "integrated" if len(standards) >= 2 else "single"
    now = datetime.now()
    try:
        cnt = db.query(CertificationApplications).count() + 1
    except Exception:
        cnt = 1
    app_no = f"APP-{now.strftime('%Y%m%d')}-{cnt:04d}"

    type_map = dict(payload.standard_types or {})
    for code in standards:
        type_map.setdefault(code, app_type)

    ksic_list = _normalize_codes(payload.ksic_codes) or _normalize_codes(payload.ksic_code)
    if not ksic_list:
        ksic_list = _company_ksic_list(db, company)
    iaf_list = _normalize_codes(payload.iaf_codes) or _normalize_codes(payload.iaf_code)
    if not iaf_list and ksic_list:
        iaf_list, _ = _lookup_iafs_from_ksics(db, ksic_list)
    if not iaf_list:
        iaf_list = _normalize_codes(company.iaf_code)

    ksic_saved, iaf_saved = _persist_company_ksic_iaf(
        db, company, ksic_list, iaf_list, now
    )

    emp = max(0, int(payload.employee_count or company.employee_count or 0))
    try:
        company.employee_count = emp
    except Exception:
        logger.exception("company.employee_count update soft-fail")

    site_count = max(1, int(payload.site_count or 1))

    # Aspects UPSERT
    std_set = {s.lower().replace("iso", "").strip() for s in standards}
    std_digits = {"".join(ch for ch in s if ch.isdigit()) for s in standards}
    want_ems = "14001" in std_digits or any("14001" in s for s in std_set)
    want_ohs = "45001" in std_digits or any("45001" in s for s in std_set)
    want_enms = "50001" in std_digits or any("50001" in s for s in std_set)

    ems_in = payload.ems if want_ems else None
    ohs_in = payload.ohs if want_ohs else None
    enms_in = payload.enms if want_enms else None
    # also accept nested aspects
    if payload.aspects:
        if ems_in is None and want_ems:
            ems_in = payload.aspects.get("ems")
        if ohs_in is None and want_ohs:
            ohs_in = payload.aspects.get("ohs")
        if enms_in is None and want_enms:
            enms_in = payload.aspects.get("enms")

    aspects_row = None
    try:
        if ems_in is not None or ohs_in is not None or enms_in is not None:
            aspects_row, _ = upsert_company_aspects(
                db, company_id, ems=ems_in, ohs=ohs_in, enms=enms_in, merge=True
            )
        else:
            aspects_row = get_company_aspects(db, company_id)
    except Exception:
        logger.exception("company_aspects upsert soft-fail")

    aspects_data = aspects_to_dict(aspects_row)

    snapshot = {
        "company_name": company.name,
        "biz_no": company.biz_no,
        "ceo_name": company.ceo_name,
        "address": company.address,
        "email": company.email,
        "tel": company.tel,
        "iaf_codes": iaf_saved,
        "ksic_codes": ksic_saved,
        "employee_count": emp,
        "site_count": site_count,
        "scope_kr": payload.scope_kr,
        "scope_en": payload.scope_en,
        "application_type": app_type,
        "aspects": {
            "ems": aspects_data.get("ems") if want_ems else None,
            "ohs": aspects_data.get("ohs") if want_ohs else None,
            "enms": aspects_data.get("enms") if want_enms else None,
        },
        "integrated_check": payload.integrated_check if audit_mode == "integrated" else None,
    }

    q_catalog = catalog_for_standards(standards)
    questionnaire_payload = {
        "common_questions": COMMON_QUESTIONS,
        "catalog": q_catalog,
        "answers": [a.model_dump() for a in payload.answers],
    }
    integrated_json = None
    if audit_mode == "integrated" and payload.integrated_check:
        integrated_json = json.dumps(payload.integrated_check, ensure_ascii=False)

    app = CertificationApplications(
        application_no=app_no,
        company_id=company_id,
        applicant_user_id=current_user.id,
        cb_id=payload.cb_id,
        application_type=app_type,
        status="submitted",
        standards_json=json.dumps(standards, ensure_ascii=False),
        standard_audit_types_json=json.dumps(type_map, ensure_ascii=False),
        iaf_codes_json=json.dumps(iaf_saved, ensure_ascii=False),
        ksic_codes_json=json.dumps(ksic_saved, ensure_ascii=False),
        snapshot_json=json.dumps(snapshot, ensure_ascii=False),
        questionnaire_json=json.dumps(questionnaire_payload, ensure_ascii=False),
        company_snapshot_json=json.dumps(
            {k: snapshot[k] for k in snapshot if k != "aspects"},
            ensure_ascii=False,
        ),
        integrated_check_json=integrated_json,
        scope_kr=payload.scope_kr,
        scope_en=payload.scope_en,
        ksic_code=(ksic_saved[0] if ksic_saved else None),
        employee_count=emp,
        regular_count=emp,
        irregular_count=0,
        total_count=emp,
        work_type=payload.work_type,
        desired_audit_start=payload.desired_audit_start,
        desired_audit_end=payload.desired_audit_end,
        site_count=site_count,
        note=payload.note,
        submitted_at=now,
        created_at=now,
        updated_at=now,
        audit_mode=audit_mode,
    )
    db.add(app)
    db.flush()

    for ans in payload.answers:
        db.add(
            CertificationApplicationAnswers(
                application_id=app.id,
                standard_code=ans.standard_code,
                question_key=ans.question_key,
                answer_value=ans.answer_value,
                answer_text=ans.answer_text,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()
    db.refresh(app)
    return OkOut(
        ok=True,
        message="인증신청이 제출되었습니다.",
        id=app.id,
        application_no=app.application_no,
        data={
            "ksic_codes": ksic_saved,
            "iaf_codes": iaf_saved,
            "application_type": app.application_type,
            "cb_id": app.cb_id,
            "audit_mode": app.audit_mode,
            "company_id": company_id,
            "aspects_saved": bool(aspects_row),
        },
    )
