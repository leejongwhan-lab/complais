"""CB certification application review pipeline (계약 전 심사 수주).

Auth: require_cb_portal_user (not platform_admin).
Routes under /api/v1/cb-cert-applications
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_cb_portal_user
from app.data.cert_questionnaire_catalog import INTEGRATED_CHECK_ITEMS
from app.db.session import get_db
from app.models.certification import (
    CertificationApplicationAnswers,
    CertificationApplicationMdReviews,
    CertificationApplicationReviewLogs,
    CertificationApplicationSites,
    CertificationApplications,
    CompanyKsicCodes,
)
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.master import MasterKsicIaf
from app.schemas.enterprise_cert import (
    CompanyInfoEditIn,
    EnterpriseCertDetail,
    EnterpriseCertListItem,
    MdSaveIn,
    OkOut,
    ReviewActionIn,
)
from app.data.standards_catalog import standard_display_payload
from app.services.cert_app_md import (
    compute_base_md_for_app,
    md_review_to_dict,
    parse_codes_json,
    parse_standards_json,
    upsert_md_review,
)
from app.services.company_aspects import aspects_to_dict, get_company_aspects
from app.services.scope_expiry import enforce_scope_not_expired

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cb-cert-applications", tags=["cb-cert-applications"])

STATUS_FILTER_DEFAULT = ("submitted", "under_review", "need_fix")

ALLOWED_TRANSITIONS = {
    "under_review": ["submitted"],
    "need_fix": ["submitted", "under_review", "need_fix"],
    "approved": ["under_review", "need_fix"],
    "rejected": ["submitted", "under_review", "need_fix"],
}

STATUS_KR = {
    "draft": "작성중",
    "submitted": "제출완료",
    "under_review": "검토중",
    "need_fix": "보완요청",
    "approved": "승인",
    "rejected": "반려",
    "contracted": "계약완료",
    "withdrawn": "취소",
}


def _draft_lead_auditor_id(db: Session, cb_id: int) -> int:
    """contracts.lead_auditor_id FK 충족용 — 실제 배정 전 임시 값."""
    try:
        from app.models.auditor import Auditor

        row = db.query(Auditor.id).order_by(Auditor.id.asc()).first()
        if row:
            return int(row[0])
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        from sqlalchemy import text

        val = db.execute(text("SELECT id FROM auditors ORDER BY id ASC LIMIT 1")).scalar()
        if val:
            return int(val)
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    raise HTTPException(
        status_code=400,
        detail="Draft 계약 생성에 필요한 심사원(auditors) 마스터가 없습니다.",
    )


def _safe_json(raw: Optional[str], default: Any = None) -> Any:
    try:
        return json.loads(raw) if raw else default
    except Exception:
        return default


def _get_app_for_cb(
    db: Session, app_id: int, cb_id: int
) -> CertificationApplications:
    app = db.get(CertificationApplications, app_id)
    if app is None:
        raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")
    if app.cb_id and int(app.cb_id) != int(cb_id):
        raise HTTPException(status_code=403, detail="다른 CB의 신청서입니다.")
    return app


def _ksic_list(db: Session, company_id: int, fallback: Optional[str] = None) -> List[str]:
    try:
        rows = (
            db.query(CompanyKsicCodes)
            .filter(CompanyKsicCodes.company_id == company_id)
            .all()
        )
        codes = [r.ksic_code for r in rows if r.ksic_code]
        if codes:
            return codes
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    if fallback:
        return [c.strip() for c in str(fallback).split(",") if c.strip()]
    return []


def _integrated_summary(integrated: Any) -> Dict[str, Any]:
    yes = no = 0
    items = []
    label_map = {i["key"]: i["label"] for i in INTEGRATED_CHECK_ITEMS}
    if isinstance(integrated, dict):
        for k, v in integrated.items():
            val = str(v or "").lower()
            if val in ("yes", "y", "true", "1", "예"):
                yes += 1
                ans = "yes"
            elif val in ("no", "n", "false", "0", "아니오"):
                no += 1
                ans = "no"
            else:
                ans = val
            items.append({"key": k, "label": label_map.get(k, k), "answer": ans})
    return {
        "yes_count": yes,
        "no_count": no,
        "warn": no >= 3,
        "items": items,
    }


def _add_log(
    db: Session,
    app_id: int,
    user: CurrentUser,
    action: str,
    before: Optional[str],
    after: Optional[str],
    memo: Optional[str] = None,
) -> None:
    db.add(
        CertificationApplicationReviewLogs(
            application_id=app_id,
            actor_user_id=user.id,
            actor_role=user.role,
            action=action,
            before_status=before,
            after_status=after,
            memo=memo,
            created_at=datetime.now(),
        )
    )


def _build_detail(db: Session, app: CertificationApplications) -> EnterpriseCertDetail:
    company = db.get(Companies, app.company_id)
    cb = db.get(CertificationBodies, app.cb_id) if app.cb_id else None
    answers = (
        db.query(CertificationApplicationAnswers)
        .filter(CertificationApplicationAnswers.application_id == app.id)
        .order_by(
            CertificationApplicationAnswers.standard_code.asc(),
            CertificationApplicationAnswers.question_key.asc(),
        )
        .all()
    )
    sites = (
        db.query(CertificationApplicationSites)
        .filter(CertificationApplicationSites.application_id == app.id)
        .order_by(CertificationApplicationSites.site_no.asc())
        .all()
    )
    logs = (
        db.query(CertificationApplicationReviewLogs)
        .filter(CertificationApplicationReviewLogs.application_id == app.id)
        .order_by(CertificationApplicationReviewLogs.id.desc())
        .limit(50)
        .all()
    )
    md = (
        db.query(CertificationApplicationMdReviews)
        .filter(CertificationApplicationMdReviews.application_id == app.id)
        .first()
    )
    ksic_codes = parse_codes_json(getattr(app, "ksic_codes_json", None)) or _ksic_list(
        db, app.company_id, (company.ksic_code if company else None) or app.ksic_code
    )
    integrated = _safe_json(app.integrated_check_json, {})
    snapshot = _safe_json(getattr(app, "snapshot_json", None), {}) or {}
    aspects_live = aspects_to_dict(get_company_aspects(db, app.company_id))
    aspects_snap = snapshot.get("aspects") if isinstance(snapshot, dict) else None
    aspects = {
        "ems": (aspects_live.get("ems") if aspects_live.get("ems") is not None else None)
        or (aspects_snap.get("ems") if isinstance(aspects_snap, dict) else None),
        "ohs": (aspects_live.get("ohs") if aspects_live.get("ohs") is not None else None)
        or (aspects_snap.get("ohs") if isinstance(aspects_snap, dict) else None),
        "enms": (aspects_live.get("enms") if aspects_live.get("enms") is not None else None)
        or (aspects_snap.get("enms") if isinstance(aspects_snap, dict) else None),
        "source": "company_aspects" if aspects_live.get("ems") or aspects_live.get("ohs") or aspects_live.get("enms") else "snapshot",
    }
    raw_stds = parse_standards_json(app.standards_json)
    return EnterpriseCertDetail(
        id=app.id,
        application_no=app.application_no,
        company_id=app.company_id,
        company_name=company.name if company else None,
        ceo_name=company.ceo_name if company else None,
        biz_no=company.biz_no if company else None,
        address=company.address if company else None,
        detail_address=company.detail_address if company else None,
        zip_code=getattr(company, "zip_code", None) if company else None,
        address_en=company.address_en if company else None,
        name_en=company.name_en if company else None,
        company_iaf_code=company.iaf_code if company else None,
        company_ksic_code=company.ksic_code if company else None,
        ksic_codes=ksic_codes,
        cb_id=app.cb_id,
        cb_name=cb.name if cb else None,
        contract_id=app.contract_id,
        application_type=app.application_type,
        status=app.status,
        standards=[standard_display_payload(s) for s in raw_stds],
        standard_audit_types=_safe_json(app.standard_audit_types_json, {}) or {},
        iaf_codes=_safe_json(app.iaf_codes_json, []) or [],
        audit_mode=app.audit_mode,
        scope_kr=app.scope_kr,
        scope_en=app.scope_en,
        employee_count=app.employee_count,
        site_count=app.site_count,
        work_type=app.work_type,
        desired_audit_start=app.desired_audit_start,
        desired_audit_end=app.desired_audit_end,
        note=app.note,
        questionnaire=_safe_json(app.questionnaire_json),
        integrated_check=integrated,
        aspects=aspects,
        snapshot=snapshot,
        answers=[
            {
                "standard_code": a.standard_code,
                "standard_label": standard_display_payload(a.standard_code).get("label"),
                "question_key": a.question_key,
                "answer_value": a.answer_value,
                "answer_text": a.answer_text,
            }
            for a in answers
        ],
        sites=[
            {
                "site_name": s.site_name,
                "address_kr": s.address_kr,
                "work_type": s.work_type,
                "total_count": s.total_count,
            }
            for s in sites
        ],
        md_review=md_review_to_dict(md),
        review_logs=[
            {
                "created_at": l.created_at.isoformat() if l.created_at else None,
                "actor_role": l.actor_role,
                "action": l.action,
                "before_status": l.before_status,
                "after_status": l.after_status,
                "memo": l.memo,
            }
            for l in logs
        ],
        integrated_summary=_integrated_summary(integrated),
        is_design_excluded=bool(
            getattr(app, "is_design_excluded", False)
            or (getattr(md, "is_design_excluded", False) if md else False)
        ),
        exclusion_note=(
            getattr(app, "exclusion_note", None)
            or (getattr(md, "exclusion_note", None) if md else None)
        ),
        submitted_at=app.submitted_at,
        reviewed_at=app.reviewed_at,
        review_note=app.review_note,
    )


@router.get("", response_model=List[EnterpriseCertListItem])
def list_applications(
    status_filter: Optional[str] = Query(
        None, alias="status", description="comma statuses"
    ),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> List[EnterpriseCertListItem]:
    cb_id = int(current_user.cb_id)  # type: ignore[arg-type]
    q = db.query(CertificationApplications, Companies.name).outerjoin(
        Companies, Companies.id == CertificationApplications.company_id
    ).filter(CertificationApplications.cb_id == cb_id)

    statuses = [
        s.strip()
        for s in (status_filter or ",".join(STATUS_FILTER_DEFAULT)).split(",")
        if s.strip()
    ]
    if statuses:
        q = q.filter(CertificationApplications.status.in_(statuses))

    rows = q.order_by(CertificationApplications.id.desc()).limit(200).all()
    return [
        EnterpriseCertListItem(
            id=a.id,
            application_no=a.application_no,
            company_id=a.company_id,
            company_name=name,
            cb_id=a.cb_id,
            standards=[
                standard_display_payload(s) for s in parse_standards_json(a.standards_json)
            ],
            audit_mode=a.audit_mode,
            application_type=a.application_type,
            employee_count=a.employee_count,
            desired_audit_start=a.desired_audit_start,
            status=a.status,
            submitted_at=a.submitted_at,
        )
        for a, name in rows
    ]


@router.get("/{app_id}", response_model=EnterpriseCertDetail)
def get_application(
    app_id: int,
    auto_md: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> EnterpriseCertDetail:
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    company = db.get(Companies, app.company_id)
    md = (
        db.query(CertificationApplicationMdReviews)
        .filter(CertificationApplicationMdReviews.application_id == app.id)
        .first()
    )
    if auto_md and (md is None or not md.base_md or float(md.base_md) <= 0):
        try:
            ksic_codes = parse_codes_json(getattr(app, "ksic_codes_json", None)) or _ksic_list(
                db,
                app.company_id,
                (company.ksic_code if company else None) or app.ksic_code,
            )
            iaf_codes = parse_codes_json(app.iaf_codes_json)
            base, detail = compute_base_md_for_app(
                app, company, ksic_codes=ksic_codes, iaf_codes=iaf_codes
            )
            if base > 0:
                upsert_md_review(
                    db,
                    app.id,
                    base_md=base,
                    detail=detail,
                    add_pct=int(md.add_pct) if md else 0,
                    subtract_pct=int(md.subtract_pct) if md else 0,
                    note=md.calculation_note if md else None,
                    reviewer_user_id=current_user.id,
                    reviewer_role=current_user.role,
                    calculated_by=current_user.role,
                )
                db.commit()
        except Exception:
            logger.exception("auto MD compute failed app_id=%s", app_id)
            try:
                db.rollback()
            except Exception:
                pass
    return _build_detail(db, app)


@router.patch("/{app_id}/company-info", response_model=OkOut)
def edit_company_info(
    app_id: int,
    payload: CompanyInfoEditIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    company = db.get(Companies, app.company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    company.employee_count = max(0, int(payload.employee_count))
    if payload.address is not None:
        company.address = payload.address
    if payload.detail_address is not None:
        company.detail_address = payload.detail_address
    if payload.zip_code is not None and hasattr(company, "zip_code"):
        try:
            company.zip_code = payload.zip_code
        except Exception:
            pass
    app.employee_count = company.employee_count
    app.total_count = company.employee_count
    app.regular_count = company.employee_count

    ksic_list = [k.strip() for k in (payload.ksic_codes or []) if k and str(k).strip()]
    if ksic_list:
        company.ksic_code = ksic_list[0][:100]
        app.ksic_code = ksic_list[0][:20]
        try:
            app.ksic_codes_json = json.dumps(ksic_list, ensure_ascii=False)
        except Exception:
            pass
        try:
            db.query(CompanyKsicCodes).filter(
                CompanyKsicCodes.company_id == company.id
            ).delete()
            now = datetime.now()
            for kc in ksic_list:
                db.add(
                    CompanyKsicCodes(
                        company_id=company.id, ksic_code=kc[:20], created_at=now
                    )
                )
        except Exception:
            logger.exception("company_ksic_codes update soft-fail")

        # recompute IAF via master_ksic_iaf (union)
        try:
            iaf_codes: List[str] = []
            for kc in ksic_list:
                rows = (
                    db.query(MasterKsicIaf)
                    .filter(MasterKsicIaf.ksic_code == kc)
                    .all()
                )
                if not rows:
                    digits = "".join(ch for ch in kc if ch.isdigit())
                    if len(digits) >= 3:
                        rows = (
                            db.query(MasterKsicIaf)
                            .filter(MasterKsicIaf.ksic_code.like(digits[:3] + "%"))
                            .limit(10)
                            .all()
                        )
                for row in rows:
                    if row and row.iaf_code and str(row.iaf_code) not in iaf_codes:
                        iaf_codes.append(str(row.iaf_code).strip())
            if iaf_codes:
                company.iaf_code = ",".join(iaf_codes)
                app.iaf_codes_json = json.dumps(iaf_codes, ensure_ascii=False)
        except Exception:
            logger.exception("IAF recompute soft-fail")

    company.updated_at = datetime.now()
    app.updated_at = datetime.now()
    _add_log(
        db,
        app.id,
        current_user,
        "edit_company_info",
        app.status,
        app.status,
        "기업정보 보정(직원수·주소·KSIC)",
    )
    db.commit()
    return OkOut(ok=True, message="기업정보가 저장되었습니다.", id=app.id)


@router.post("/{app_id}/md", response_model=OkOut)
def save_md(
    app_id: int,
    payload: MdSaveIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    company = db.get(Companies, app.company_id)
    ksic_codes = parse_codes_json(getattr(app, "ksic_codes_json", None)) or _ksic_list(
        db, app.company_id, (company.ksic_code if company else None) or app.ksic_code
    )
    iaf_codes = parse_codes_json(app.iaf_codes_json)
    existing = (
        db.query(CertificationApplicationMdReviews)
        .filter(CertificationApplicationMdReviews.application_id == app.id)
        .first()
    )
    base = float(existing.base_md) if existing and existing.base_md else 0.0
    detail = None
    if payload.recompute_base or base <= 0:
        base, detail = compute_base_md_for_app(
            app, company, ksic_codes=ksic_codes, iaf_codes=iaf_codes
        )
    if base <= 0:
        raise HTTPException(status_code=400, detail="기본 MD를 계산할 수 없습니다.")

    row = upsert_md_review(
        db,
        app.id,
        base_md=base,
        detail=detail,
        add_pct=payload.md_plus_pct,
        subtract_pct=payload.md_minus_pct,
        note=payload.md_note,
        is_design_excluded=bool(payload.is_design_excluded),
        exclusion_note=payload.exclusion_note,
        reviewer_user_id=current_user.id,
        reviewer_role=current_user.role,
        calculated_by=current_user.role,
    )
    app.is_design_excluded = bool(payload.is_design_excluded)
    app.exclusion_note = payload.exclusion_note
    app.updated_at = datetime.now()
    summary = (
        f"기본 {float(row.base_md):.1f} / 가산 {row.add_pct}%"
        f"({float(row.add_md):.2f}) / 감산 {row.subtract_pct}%"
        f"({float(row.subtract_md):.2f}) / 최종 {float(row.final_md):.1f}"
    )
    _add_log(db, app.id, current_user, "md_save", app.status, app.status, summary)
    db.commit()
    return OkOut(
        ok=True,
        message="MD가 저장되었습니다.",
        id=app.id,
        data=md_review_to_dict(row),
    )


@router.post("/{app_id}/action", response_model=OkOut)
def review_action(
    app_id: int,
    payload: ReviewActionIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    action = (payload.action or "").strip()
    before = app.status

    if action == "save_md":
        return save_md(
            app_id,
            MdSaveIn(
                md_plus_pct=payload.md_plus_pct,
                md_minus_pct=payload.md_minus_pct,
                md_note=payload.md_note,
                is_design_excluded=bool(payload.is_design_excluded),
                exclusion_note=payload.exclusion_note,
                recompute_base=True,
            ),
            db=db,
            current_user=current_user,
        )

    if action not in ALLOWED_TRANSITIONS:
        raise HTTPException(status_code=400, detail="허용되지 않은 동작입니다.")
    if before not in ALLOWED_TRANSITIONS[action]:
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({STATUS_KR.get(before, before)})에서는 해당 동작을 수행할 수 없습니다.",
        )

    company = db.get(Companies, app.company_id)
    ksic_codes = _ksic_list(
        db, app.company_id, (company.ksic_code if company else None) or app.ksic_code
    )
    md_row = (
        db.query(CertificationApplicationMdReviews)
        .filter(CertificationApplicationMdReviews.application_id == app.id)
        .first()
    )
    base = float(md_row.base_md) if md_row and md_row.base_md else 0.0
    detail = None
    if base <= 0:
        iaf_codes = parse_codes_json(app.iaf_codes_json)
        base, detail = compute_base_md_for_app(
            app, company, ksic_codes=ksic_codes, iaf_codes=iaf_codes
        )
    md_row = upsert_md_review(
        db,
        app.id,
        base_md=base,
        detail=detail,
        add_pct=payload.md_plus_pct,
        subtract_pct=payload.md_minus_pct,
        note=payload.md_note,
        is_design_excluded=bool(payload.is_design_excluded),
        exclusion_note=payload.exclusion_note,
        reviewer_user_id=current_user.id,
        reviewer_role=current_user.role,
        calculated_by=current_user.role,
    )
    app.is_design_excluded = bool(payload.is_design_excluded)
    app.exclusion_note = payload.exclusion_note
    app.updated_at = datetime.now()
    final_md = float(md_row.final_md or 0)

    if action == "approved":
        if final_md <= 0:
            raise HTTPException(status_code=400, detail="승인 전에 MD를 먼저 확정해 주세요.")
        standards = parse_standards_json(app.standards_json)
        std_codes = [
            (s.get("code") if isinstance(s, dict) else s) for s in standards
        ]
        try:
            enforce_scope_not_expired(db, int(app.cb_id or current_user.cb_id), std_codes)
        except HTTPException:
            raise
        except Exception:
            logger.exception("scope expiry soft-fail on approve")

    now = datetime.now()
    md_summary = (
        f"MD 기본 {float(md_row.base_md):.1f} / 가산 {float(md_row.add_md):.1f}"
        f" / 감산 {float(md_row.subtract_md):.1f} / 최종 {final_md:.1f}"
    )
    memo_final = (payload.memo or "").strip()
    if md_summary:
        memo_final = (memo_final + " / " if memo_final else "") + md_summary

    new_contract_id: Optional[int] = None
    try:
        app.status = action
        app.reviewed_at = now
        app.reviewed_by = current_user.id
        app.review_note = memo_final
        app.updated_at = now

        if action == "approved" and not app.contract_id:
            contract_no = app.application_no or f"CTR-{now.strftime('%Y%m%d')}-{app.id}"
            standards_raw = app.standards_json or "[]"
            # lead_auditor_id NOT NULL + FK → auditors.id — draft placeholder (배정 전)
            lead_id = _draft_lead_auditor_id(db, int(app.cb_id or current_user.cb_id or 0))
            contract = Contracts(
                contract_id=contract_no,
                cb_id=int(app.cb_id or current_user.cb_id),
                company_id=int(app.company_id),
                lead_auditor_id=lead_id,
                audit_type=app.application_type or "initial",
                standards=standards_raw,
                scope_kr=app.scope_kr,
                scope_en=app.scope_en,
                audit_period_start=app.desired_audit_start,
                audit_period_end=app.desired_audit_end,
                current_stage=1,
                total_md=Decimal(str(final_md)),
                agreed_amount=Decimal("0"),
                status="draft",
                created_at=now,
                updated_at=now,
                contract_type="certification",
                audit_days=Decimal(str(final_md)),
                applied_standards=standards_raw,
                audit_mode=app.audit_mode or "single",
            )
            db.add(contract)
            db.flush()
            app.contract_id = contract.id
            new_contract_id = contract.id

        _add_log(db, app.id, current_user, action, before, action, memo_final)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("review action failed")
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}") from e

    return OkOut(
        ok=True,
        message="처리가 저장되었습니다.",
        id=app.id,
        contract_id=new_contract_id,
        data={"status": action, "status_label": STATUS_KR.get(action, action)},
    )
