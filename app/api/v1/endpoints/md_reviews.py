"""MD(Man-Day) 산출 및 행정 가감 검토 API.

레거시 md_save_base.php / cb_application_review.php 를 대체하는 엔드포인트.
AuditMdReview / AuditMdReviewLog 모델과 md_calculator 계산 로직을 연결한다.

CB(인증원) 단위 데이터 격리: AuditApplication.auditor_id -> AuditorCbMemberships.cb_id 경로로
소속을 판단하여, 로그인한 인증원 소속 심사원의 신청건 MD 정보만 접근을 허용한다 (platform_admin 제외).
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.cb_scope import assert_auditor_in_cb_scope
from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.audit_md import AuditMdReview, AuditMdReviewLog
from app.models.auditor import AuditApplication
from app.schemas.audit_md import BaseMdSaveRequest, MdReviewResponse, MdReviewUpdateRequest
from app.services.md_calculator import calculate_review_md

router = APIRouter(prefix="/md-reviews", tags=["MD Review"])

# action -> 검토 상태 매핑 (AuditMdReview 자체에는 status 컬럼이 없어
# AuditMdReviewLog.after_status 이력으로 현재 상태를 추적한다)
ACTION_STATUS_MAP = {
    "save_md": "MD_SAVED",
    "under_review": "UNDER_REVIEW",
    "approved": "APPROVED",
    "need_fix": "NEED_FIX",
    "rejected": "REJECTED",
}


class MdReviewLogResponse(BaseModel):
    id: int
    md_review_id: int
    actor_user_id: Optional[int]
    actor_role: Optional[str]
    action: str
    before_status: Optional[str]
    after_status: Optional[str]
    memo: Optional[str]
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


def _get_application_or_404(db: Session, application_id: int) -> AuditApplication:
    application = db.query(AuditApplication).filter(AuditApplication.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail=f"심사 신청서(application_id={application_id})를 찾을 수 없습니다.")
    return application


def _get_review_or_404(db: Session, application_id: int) -> AuditMdReview:
    review = db.query(AuditMdReview).filter(AuditMdReview.application_id == application_id).first()
    if not review:
        raise HTTPException(
            status_code=404,
            detail=f"application_id={application_id}에 대한 MD 산출 정보가 없습니다. 먼저 기본 MD를 저장해 주세요.",
        )
    return review


def _current_status(review: AuditMdReview) -> str:
    """가장 최근 로그의 after_status를 현재 검토 상태로 간주 (로그 없으면 초기 상태)."""
    latest_log = (
        max(review.review_logs, key=lambda log: log.created_at or datetime.min)
        if review.review_logs
        else None
    )
    if latest_log:
        return latest_log.after_status or "MD_SAVED"
    return "MD_SAVED" if review.base_md else "DRAFT"


@router.get("/applications/{application_id}", response_model=MdReviewResponse)
def get_md_review(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """신청건의 MD 산출/검토 현황을 조회합니다. 타 인증원 소속 심사원의 신청건은 조회할 수 없습니다."""
    application = _get_application_or_404(db, application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)
    review = _get_review_or_404(db, application_id)
    return review


@router.get("/applications/{application_id}/logs", response_model=List[MdReviewLogResponse])
def get_md_review_logs(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """신청건 MD 검토의 상태 변경/저장 이력을 조회합니다. 타 인증원 소속 심사원의 신청건은 조회할 수 없습니다."""
    application = _get_application_or_404(db, application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)
    review = _get_review_or_404(db, application_id)
    return sorted(review.review_logs, key=lambda log: log.created_at or datetime.min)


@router.post("/applications/{application_id}/base", response_model=MdReviewResponse)
def save_base_md(
    application_id: int,
    payload: BaseMdSaveRequest,
    calculated_by: Optional[int] = None,  # 실환경에서는 JWT에서 유저 ID 추출
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """MD 계산기 산출 결과를 저장/갱신합니다 (md_save_base.php 대체).
    타 인증원 소속 심사원의 신청건은 저장할 수 없습니다."""
    if payload.application_id != application_id:
        raise HTTPException(status_code=400, detail="경로의 application_id와 요청 본문의 application_id가 일치하지 않습니다.")

    application = _get_application_or_404(db, application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)

    review = db.query(AuditMdReview).filter(AuditMdReview.application_id == application_id).first()
    is_new = review is None
    if is_new:
        review = AuditMdReview(application_id=application_id)
        db.add(review)

    before_status = _current_status(review) if not is_new else "DRAFT"

    review.base_md = payload.base_md
    review.base_md_detail_json = payload.base_md_detail_json or {}
    review.base_md_calculated_at = datetime.now(timezone.utc)
    review.base_md_calculated_by = calculated_by

    # 기존 가감 비율을 유지한 채 기본 MD만 갱신 -> 최종 MD 재계산
    add_md, subtract_md, final_md = calculate_review_md(
        base_md=review.base_md,
        add_pct=review.add_pct or 0,
        subtract_pct=review.subtract_pct or 0,
    )
    review.add_md = add_md
    review.subtract_md = subtract_md
    review.final_md = final_md

    db.flush()
    db.add(
        AuditMdReviewLog(
            md_review_id=review.id,
            actor_user_id=calculated_by,
            actor_role="calculator",
            action="save_md",
            before_status=before_status,
            after_status="MD_SAVED",
            memo="MD 계산기 기본 산출 저장",
        )
    )
    db.commit()
    db.refresh(review)
    return review


@router.post("/applications/{application_id}/review", response_model=MdReviewResponse)
def update_md_review(
    application_id: int,
    payload: MdReviewUpdateRequest,
    actor_user_id: Optional[int] = None,  # 실환경에서는 JWT에서 유저 ID 추출
    actor_role: str = "cb_admin",
    is_integrated: bool = False,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """인증기관 담당자의 행정 가감 검토 저장/승인 처리 (cb_application_review.php POST 대체).
    타 인증원 소속 심사원의 신청건은 검토할 수 없습니다."""
    if payload.action not in ACTION_STATUS_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"올바르지 않은 action입니다. 허용값: {list(ACTION_STATUS_MAP.keys())}",
        )

    application = _get_application_or_404(db, application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)

    review = _get_review_or_404(db, application_id)
    before_status = _current_status(review)

    review.add_pct = payload.add_pct
    review.subtract_pct = payload.subtract_pct
    if payload.calculation_note is not None:
        review.calculation_note = payload.calculation_note

    add_md, subtract_md, final_md = calculate_review_md(
        base_md=review.base_md,
        add_pct=review.add_pct,
        subtract_pct=review.subtract_pct,
        is_integrated=is_integrated,
    )
    review.add_md = add_md
    review.subtract_md = subtract_md
    review.final_md = final_md

    after_status = ACTION_STATUS_MAP[payload.action]
    if payload.action == "approved":
        review.reviewer_user_id = actor_user_id
        review.reviewer_role = actor_role
        review.reviewed_at = datetime.now(timezone.utc)

    db.add(
        AuditMdReviewLog(
            md_review_id=review.id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=payload.action,
            before_status=before_status,
            after_status=after_status,
            memo=payload.memo,
        )
    )
    db.commit()
    db.refresh(review)
    return review
