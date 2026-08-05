"""CB 포털용 심사원 목록/상세 + 소속 승인 — Strict Tenant Isolation."""
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.auditor import Auditor, AuditorCbMemberships, AuditorEducation, AuditorWorkExperience
from app.models.enums import AuditorCbMembershipsStatus, UsersRole

router = APIRouter(prefix="/cb", tags=["CB Auditors"])


class CbMembershipScoped(BaseModel):
    """타 CB 필드는 절대 포함하지 않는 스코프 멤버십 DTO."""

    id: int
    auditor_id: int
    cb_id: int
    status: str
    apply_grade: Optional[str] = None
    approved_grade: Optional[str] = None
    grade_at_cb: Optional[str] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    kar_no: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    is_primary: Optional[bool] = None
    apply_message: Optional[str] = None
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    qualification_granted_at: Optional[date] = None
    conflict_of_interest_cleared: Optional[bool] = None


class CbAuditorListItem(BaseModel):
    auditor_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    membership: CbMembershipScoped


class CbAuditorDetailResponse(BaseModel):
    """CB 관리자용 상세 — 해당 CB membership 1건만 + 공용 프로필(학력/경력).

    타 CB 소속/등급/IAF/이력은 반환하지 않는다.
    """

    auditor_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    # 공용 Identity 프로필 (CB 비종속)
    educations: List[dict] = Field(default_factory=list)
    careers: List[dict] = Field(default_factory=list)
    # 세션 CB 소속만
    membership: CbMembershipScoped


class MembershipApproveBody(BaseModel):
    decision: str = Field(..., description="approved | rejected")
    approved_grade: Optional[str] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    note: Optional[str] = None


def _require_cb_manager(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.CB_ADMIN.value,
        UsersRole.CB_MANAGER.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다.",
        )
    if (
        current_user.role != UsersRole.PLATFORM_ADMIN.value
        and current_user.cb_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 인증원(CB) 정보가 없습니다.",
        )
    return current_user


def _session_cb_id(current_user: CurrentUser) -> int:
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="플랫폼 관리자는 cb_id 쿼리 파라미터가 필요합니다.",
        )
    assert current_user.cb_id is not None
    return current_user.cb_id


def _membership_to_dto(m: AuditorCbMemberships) -> CbMembershipScoped:
    return CbMembershipScoped(
        id=m.id,
        auditor_id=m.auditor_id,
        cb_id=m.cb_id,
        status=m.status,
        apply_grade=m.apply_grade,
        approved_grade=m.approved_grade,
        grade_at_cb=m.grade_at_cb,
        cert_standards=m.cert_standards,
        approved_iaf_codes=m.approved_iaf_codes,
        kar_no=m.kar_no,
        employment_type=m.employment_type,
        is_freelance=m.is_freelance,
        is_primary=m.is_primary,
        apply_message=m.apply_message,
        requested_at=m.requested_at,
        approved_at=m.approved_at,
        approved_by=m.approved_by,
        qualification_granted_at=m.qualification_granted_at,
        conflict_of_interest_cleared=m.conflict_of_interest_cleared,
    )


@router.get("/auditors", response_model=List[CbAuditorListItem])
def list_cb_auditors(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="requested|under_review|approved|rejected|pending",
    ),
    keyword: Optional[str] = Query(None, description="이름/이메일/연락처"),
    cb_id: Optional[int] = Query(None, description="platform_admin 전용 CB 지정"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB 소속 심사원 목록 — WHERE membership.cb_id = :session_cb_id 강제."""
    _require_cb_manager(current_user)
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        scope_cb_id = cb_id
    else:
        scope_cb_id = _session_cb_id(current_user)
    if not scope_cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")

    # 타 CB 레코드는 JOIN 단계에서 제외
    query = (
        db.query(Auditor, AuditorCbMemberships)
        .join(
            AuditorCbMemberships,
            (AuditorCbMemberships.auditor_id == Auditor.id)
            & (AuditorCbMemberships.cb_id == scope_cb_id),
        )
    )

    if status_filter:
        st = status_filter.strip().lower()
        if st == "pending":
            query = query.filter(
                AuditorCbMemberships.status.in_(
                    [
                        AuditorCbMembershipsStatus.REQUESTED.value,
                        AuditorCbMembershipsStatus.UNDER_REVIEW.value,
                    ]
                )
            )
        else:
            query = query.filter(AuditorCbMemberships.status == st)

    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(
            (Auditor.name.ilike(like))
            | (Auditor.email.ilike(like))
            | (Auditor.phone.ilike(like))
        )

    rows = query.order_by(AuditorCbMemberships.id.desc()).limit(200).all()
    return [
        CbAuditorListItem(
            auditor_id=a.id,
            name=a.name,
            email=a.email,
            phone=a.phone,
            birth_date=a.birth_date.isoformat() if a.birth_date else None,
            membership=_membership_to_dto(m),
        )
        for a, m in rows
    ]


@router.get("/auditors/{auditor_id}", response_model=CbAuditorDetailResponse)
def get_cb_auditor_detail(
    auditor_id: int,
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB 심사원 상세 — 세션 CB membership만 반환 (타 CB 완전 배제)."""
    _require_cb_manager(current_user)
    scope_cb_id = (
        cb_id
        if current_user.role == UsersRole.PLATFORM_ADMIN.value and cb_id
        else current_user.cb_id
    )
    if not scope_cb_id:
        raise HTTPException(status_code=400, detail="cb_id가 필요합니다.")

    membership = (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.auditor_id == auditor_id,
            AuditorCbMemberships.cb_id == scope_cb_id,
        )
        .first()
    )
    if not membership:
        # 존재 여부조차 타 CB에 누설하지 않도록 동일 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소속 심사원 정보를 찾을 수 없습니다.",
        )

    auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
    if not auditor:
        raise HTTPException(status_code=404, detail="소속 심사원 정보를 찾을 수 없습니다.")

    educations = (
        db.query(AuditorEducation)
        .filter(AuditorEducation.auditor_id == auditor_id)
        .order_by(AuditorEducation.id.desc())
        .all()
    )
    careers = (
        db.query(AuditorWorkExperience)
        .filter(AuditorWorkExperience.auditor_id == auditor_id)
        .order_by(AuditorWorkExperience.id.desc())
        .all()
    )

    return CbAuditorDetailResponse(
        auditor_id=auditor.id,
        name=auditor.name,
        email=auditor.email,
        phone=auditor.phone,
        birth_date=auditor.birth_date.isoformat() if auditor.birth_date else None,
        gender=auditor.gender,
        address=auditor.address,
        educations=[
            {
                "id": e.id,
                "school_name": e.school_name,
                "degree": e.degree,
                "major": e.major,
            }
            for e in educations
        ],
        careers=[
            {
                "id": c.id,
                "company_name": c.company_name,
                "position": c.position,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
            }
            for c in careers
        ],
        membership=_membership_to_dto(membership),
    )


@router.patch("/memberships/{membership_id}/approve")
def approve_cb_membership(
    membership_id: int,
    payload: MembershipApproveBody,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB 관리자의 소속/자격 신청 승인·거절."""
    _require_cb_manager(current_user)
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=400,
            detail="플랫폼 관리자는 CB 스코프 계정으로 승인하세요.",
        )

    decision = payload.decision.strip().lower()
    if decision not in {
        AuditorCbMembershipsStatus.APPROVED.value,
        AuditorCbMembershipsStatus.REJECTED.value,
    }:
        raise HTTPException(
            status_code=400,
            detail="decision은 approved 또는 rejected 만 가능합니다.",
        )

    membership = (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.id == membership_id,
            AuditorCbMemberships.cb_id == current_user.cb_id,  # 격리 강제
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=404,
            detail="소속 신청을 찾을 수 없습니다.",
        )

    now = datetime.utcnow()
    membership.status = decision
    membership.updated_at = now
    if decision == AuditorCbMembershipsStatus.APPROVED.value:
        membership.approved_at = now
        membership.approved_by = current_user.id
        if payload.approved_grade:
            membership.approved_grade = payload.approved_grade
            membership.grade_at_cb = payload.approved_grade
        elif membership.apply_grade:
            membership.approved_grade = membership.apply_grade
            membership.grade_at_cb = membership.apply_grade
        if payload.cert_standards is not None:
            membership.cert_standards = payload.cert_standards
        if payload.approved_iaf_codes is not None:
            membership.approved_iaf_codes = payload.approved_iaf_codes
        membership.qualification_granted_at = (
            membership.qualification_granted_at or now.date()
        )
        membership.reject_reason = None

        # 심사원 Identity의 primary_cb 는 '첫 승인 CB'만 설정 (타 CB 덮어쓰기 금지)
        auditor = db.query(Auditor).filter(Auditor.id == membership.auditor_id).first()
        if auditor and not auditor.primary_cb_id:
            auditor.primary_cb_id = membership.cb_id
            auditor.updated_at = now
            if membership.approved_grade:
                auditor.grade = membership.approved_grade
    else:
        membership.approved_at = None
        membership.approved_by = None
        membership.reject_reason = payload.note

    if payload.note and decision == AuditorCbMembershipsStatus.APPROVED.value:
        membership.cb_review_note = payload.note

    db.commit()
    db.refresh(membership)

    return {
        "message": "소속 승인 상태가 갱신되었습니다.",
        "membership_id": membership.id,
        "auditor_id": membership.auditor_id,
        "cb_id": membership.cb_id,
        "status": membership.status,
        "approved_grade": membership.approved_grade,
    }
