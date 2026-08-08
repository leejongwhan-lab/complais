# CANONICAL — 기업↔CB 인증신청 메인 경로
"""CB certification application review pipeline (계약 전 심사 수주).

Auth: require_cb_portal_user (not platform_admin).
Routes under /api/v1/cb-cert-applications
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_cb_portal_user
from app.data.cert_questionnaire_catalog import INTEGRATED_CHECK_ITEMS
from app.db.session import get_db
from app.models.audit import AuditAssignments
from app.models.certification import (
    CertificationApplicationAnswers,
    CertificationApplicationMdReviews,
    CertificationApplicationReviewLogs,
    CertificationApplicationSites,
    CertificationApplications,
    CompanyKsicCodes,
)
from app.models.auth import Notifications, Users
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.master import MasterKsicIaf
from app.schemas.enterprise_cert import (
    AuditorAssignIn,
    CompanyInfoEditIn,
    EnterpriseCertDetail,
    EnterpriseCertListItem,
    MdSaveIn,
    OkOut,
    ReviewActionIn,
)
from app.data.standards_catalog import standard_display_payload
from app.services.auditor_assignment_fees import (
    assert_auditors_exist,
    assert_conduct_signs,
    auditor_user_id_or_raise,
    build_fee_snapshot,
    default_assigned_days,
    ensure_auditor_assignment_docs,
    serialize_assignment,
)
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

STATUS_FILTER_DEFAULT = (
    "submitted",
    "under_review",
    "need_fix",
    "company_revision_requested",
)

ALLOWED_TRANSITIONS = {
    "under_review": ["submitted", "company_revision_requested"],
    "need_fix": ["submitted", "under_review", "need_fix"],
    "approved": ["under_review", "need_fix", "company_revision_requested"],
    "rejected": ["submitted", "under_review", "need_fix"],
}

STATUS_KR = {
    "draft": "작성중",
    "submitted": "제출완료",
    "under_review": "검토중",
    "need_fix": "보완요청",
    "approved": "승인(조율대기)",
    "company_revision_requested": "기업조율요청",
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


def _company_notify_user_ids(
    db: Session, company_id: int, applicant_user_id: Optional[int]
) -> List[int]:
    ids: set[int] = set()
    if applicant_user_id:
        ids.add(int(applicant_user_id))
    try:
        rows = (
            db.query(Users.id)
            .filter(Users.company_id == int(company_id), Users.is_active == True)  # noqa: E712
            .all()
        )
        for (uid,) in rows:
            if uid:
                ids.add(int(uid))
    except Exception:
        # Do not rollback — caller may already have pending writes in this session.
        logger.exception("company notify user lookup soft-fail")
    return sorted(ids)


def _notify_users(
    db: Session,
    user_ids: List[int],
    *,
    ntype: str,
    title: str,
    body: str,
    link: str,
    sent_at: datetime,
) -> None:
    for uid in user_ids:
        db.add(
            Notifications(
                user_id=int(uid),
                type=ntype,
                title=title,
                body=body,
                link=link,
                channel="in_app",
                is_read=False,
                sent_at=sent_at,
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
        standards=[standard_display_payload(s, mode="cb") for s in raw_stds],
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
                "standard_label": standard_display_payload(
                    a.standard_code, mode="cb"
                ).get("label"),
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
                standard_display_payload(s, mode="cb")
                for s in parse_standards_json(a.standards_json)
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

        if action == "approved":
            # 상태 approved 유지(= 기업 조율 대기). 기업 사용자에게 인앱 알림.
            notify_ids = _company_notify_user_ids(
                db, int(app.company_id), app.applicant_user_id
            )
            app_no = app.application_no or str(app.id)
            _notify_users(
                db,
                notify_ids,
                ntype="cert_app_approved",
                title="인증신청이 승인되었습니다",
                body=(
                    f"신청번호 {app_no} — CB 내부승인이 완료되었습니다. "
                    "기업 포털에서 확인(동의) 또는 조율 요청을 진행해 주세요."
                ),
                link="/enterprise/dashboard#cert-apply",
                sent_at=now,
            )

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


@router.post("/{app_id}/assign-auditors", response_model=OkOut)
def assign_auditors(
    app_id: int,
    payload: AuditorAssignIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    """System1 심사원 배정 — Contracts + audit_assignments (+ 수수료 스냅샷).

    cb_admin.assign_auditors(DEPRECATED) 를 참고하되 AuditApplication/audit_contracts 가 아닌
    CertificationApplications / contracts / audit_assignments 조합으로 저장한다.
    """
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    if not app.contract_id:
        raise HTTPException(
            status_code=400,
            detail="계약(Draft)이 없습니다. 승인(action=approved) 후 배정하세요.",
        )
    if payload.audit_end < payload.audit_start:
        raise HTTPException(status_code=400, detail="audit_end 는 audit_start 이후여야 합니다.")

    all_ids = [payload.lead_auditor_id, *payload.member_auditor_ids]
    if len(set(all_ids)) != len(all_ids):
        raise HTTPException(status_code=400, detail="동일 심사원을 중복 배정할 수 없습니다.")

    assert_auditors_exist(db, all_ids)
    assert_conduct_signs(db, all_ids)

    contract = db.get(Contracts, int(app.contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="연결된 계약을 찾을 수 없습니다.")
    if int(contract.cb_id) != int(current_user.cb_id):  # type: ignore[arg-type]
        raise HTTPException(status_code=403, detail="다른 CB의 계약입니다.")

    cb_id = int(app.cb_id or current_user.cb_id)
    company_id = int(app.company_id)
    agreed = float(contract.agreed_amount or contract.fee_total or 0)
    days = default_assigned_days(
        audit_start=payload.audit_start,
        audit_end=payload.audit_end,
        total_md=payload.total_md if payload.total_md is not None else float(contract.total_md or 0),
        assigned_days=payload.assigned_days,
    )
    now = datetime.now()
    status_val = "confirmed" if payload.confirm else "assigned"
    standards_raw = app.standards_json or contract.standards
    iaf_raw = app.iaf_codes_json

    # 기존 배정 교체
    db.query(AuditAssignments).filter(AuditAssignments.contract_id == contract.id).delete()

    created_rows: List[AuditAssignments] = []
    role_plan = [("lead", "team_leader", payload.lead_auditor_id)] + [
        ("auditor", "team_member", mid) for mid in payload.member_auditor_ids
    ]
    doc_ids: List[int] = []

    try:
        for role, assignment_role, auditor_id in role_plan:
            user_id = auditor_user_id_or_raise(db, auditor_id)
            fee = build_fee_snapshot(
                db,
                auditor_id=auditor_id,
                company_id=company_id,
                cb_id=cb_id,
                role=role,
                agreed_amount=agreed,
                assigned_days=days,
            )
            row = AuditAssignments(
                application_id=app.id,
                contract_id=contract.id,
                auditor_id=auditor_id,
                role=role,
                auditor_user_id=user_id,
                assignment_role=assignment_role,
                status=status_val,
                iaf_match_status="review_needed",
                conflict_check_status="pending",
                client_confirmation_status="pending",
                assignment_note=payload.note,
                created_by=current_user.id,
                created_at=now,
                updated_at=now,
                standards_json=standards_raw,
                iaf_codes_json=iaf_raw,
                assigned_at=now,
                fee_type=fee["fee_type"],
                fee_ratio=Decimal(str(fee["fee_ratio"])) if fee["fee_type"] == "PERCENTAGE" else None,
                daily_rate=int(fee["daily_rate"]) if fee["fee_type"] == "DAILY_RATE" else None,
                assigned_days=Decimal(str(fee["assigned_days"])),
                calculated_fee=Decimal(str(fee["calculated_fee"])),
            )
            db.add(row)
            db.flush()
            created_rows.append(row)
            if status_val == "confirmed":
                doc_ids.extend(
                    ensure_auditor_assignment_docs(
                        db,
                        contract_id=int(contract.id),
                        assignment=row,
                        created_by=current_user.id,
                        now=now,
                    )
                )

        contract.lead_auditor_id = payload.lead_auditor_id
        contract.member_auditor_ids = ",".join(str(i) for i in payload.member_auditor_ids) or None
        contract.audit_period_start = payload.audit_start
        contract.audit_period_end = payload.audit_end
        if payload.total_md is not None:
            contract.total_md = Decimal(str(payload.total_md))
            contract.audit_days = Decimal(str(payload.total_md))
        if status_val == "confirmed" and str(contract.status or "").lower() in (
            "draft",
            "approved",
            "",
        ):
            contract.status = "scheduled"
        contract.updated_at = now

        _add_log(
            db,
            app.id,
            current_user,
            "assign_auditors",
            app.status,
            app.status,
            f"lead={payload.lead_auditor_id}; members={payload.member_auditor_ids}; status={status_val}",
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("assign_auditors failed")
        raise HTTPException(status_code=500, detail=f"배정 실패: {e}") from e

    return OkOut(
        ok=True,
        message=f"배정 완료 (팀장 1 + 팀원 {len(payload.member_auditor_ids)}, status={status_val})",
        id=app.id,
        contract_id=contract.id,
        data={
            "assignments": [serialize_assignment(r) for r in created_rows],
            "document_ids": doc_ids,
            "status": status_val,
        },
    )


@router.post("/{app_id}/assignments/confirm", response_model=OkOut)
def confirm_assignments(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    """배정 확정(confirmed) + AUDITOR_CONTRACT / NDA 문서 초안 생성."""
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    if not app.contract_id:
        raise HTTPException(status_code=400, detail="계약이 없습니다.")
    contract = db.get(Contracts, int(app.contract_id))
    if contract is None:
        raise HTTPException(status_code=404, detail="연결된 계약을 찾을 수 없습니다.")

    rows = (
        db.query(AuditAssignments)
        .filter(AuditAssignments.contract_id == contract.id)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=400, detail="확정할 배정이 없습니다. 먼저 assign-auditors 를 호출하세요.")

    now = datetime.now()
    doc_ids: List[int] = []
    try:
        for row in rows:
            row.status = "confirmed"
            row.updated_at = now
            doc_ids.extend(
                ensure_auditor_assignment_docs(
                    db,
                    contract_id=int(contract.id),
                    assignment=row,
                    created_by=current_user.id,
                    now=now,
                )
            )
        if str(contract.status or "").lower() in ("draft", "approved", ""):
            contract.status = "scheduled"
        contract.updated_at = now
        _add_log(db, app.id, current_user, "confirm_assignments", app.status, app.status, None)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("confirm_assignments failed")
        raise HTTPException(status_code=500, detail=f"확정 실패: {e}") from e

    return OkOut(
        ok=True,
        message=f"배정 {len(rows)}건 확정 및 문서 {len(doc_ids)}건 생성",
        id=app.id,
        contract_id=contract.id,
        data={
            "assignments": [serialize_assignment(r) for r in rows],
            "document_ids": doc_ids,
        },
    )


@router.get("/{app_id}/assignments", response_model=OkOut)
def list_app_assignments(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> OkOut:
    app = _get_app_for_cb(db, app_id, int(current_user.cb_id))  # type: ignore[arg-type]
    if not app.contract_id:
        return OkOut(ok=True, id=app.id, data={"assignments": []})
    rows = (
        db.query(AuditAssignments)
        .filter(AuditAssignments.contract_id == int(app.contract_id))
        .order_by(AuditAssignments.id.asc())
        .all()
    )
    return OkOut(
        ok=True,
        id=app.id,
        contract_id=int(app.contract_id),
        data={"assignments": [serialize_assignment(r) for r in rows]},
    )
