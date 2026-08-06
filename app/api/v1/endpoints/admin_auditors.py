"""플랫폼 관리자 — 심사원 마스터 목록/상세 API."""
from datetime import date, datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_platform_admin
from app.models.auditor import (
    Auditor,
    AuditorCbMemberships,
    AuditorEducation,
    AuditorWorkExperience,
)

router = APIRouter(prefix="/admin/auditors", tags=["Admin Auditors"])


class AuditorSummaryResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    status: Optional[str] = None
    profile_status: Optional[str] = None
    primary_cb_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AuditorListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[AuditorSummaryResponse]


class AuditorProfileDetail(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    name_en: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    grade: Optional[str] = None
    employment_type: Optional[str] = None
    is_freelance: Optional[bool] = None
    primary_cb_id: Optional[int] = None
    registration_no: Optional[str] = None
    iaf_codes: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None
    profile_status: Optional[str] = None
    contract_type: Optional[str] = None
    daily_rate: Optional[float] = None
    fee_ratio: Optional[float] = None
    monthly_fee: Optional[float] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    intro: Optional[str] = None
    education_level: Optional[str] = None
    school_name: Optional[str] = None
    major: Optional[str] = None
    career_summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MembershipItem(BaseModel):
    id: int
    auditor_id: int
    cb_id: int
    employment_type: str
    is_freelance: bool
    status: str
    is_primary: bool
    apply_grade: Optional[str] = None
    approved_grade: Optional[str] = None
    grade_at_cb: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    cert_standards: Optional[str] = None
    daily_rate: Optional[int] = None
    fee_ratio: Optional[Any] = None
    reject_reason: Optional[str] = None
    cb_review_note: Optional[str] = None
    qualification_granted_at: Optional[date] = None
    qualification_expires_at: Optional[date] = None
    knowledge_eval_score: Optional[int] = None
    cpd_hours_completed: Optional[int] = 0
    conflict_of_interest_cleared: Optional[bool] = False
    extra_metadata: Optional[dict] = None
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EducationItem(BaseModel):
    id: int
    auditor_id: int
    school_name: str
    degree: str
    major: str
    entered_at: Optional[date] = None
    graduated_at: Optional[date] = None
    is_verified: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class CareerItem(BaseModel):
    id: int
    auditor_id: int
    company_name: str
    position: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    note: Optional[str] = Field(default=None, description="부서/비고")

    model_config = ConfigDict(from_attributes=True)


class AuditorDetailResponse(BaseModel):
    profile: AuditorProfileDetail
    memberships: List[MembershipItem]
    educations: List[EducationItem]
    careers: List[CareerItem]


@router.get("", response_model=AuditorListResponse)
def get_admin_auditors(
    keyword: Optional[str] = Query(None, description="이름, 이메일, 연락처 검색"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> AuditorListResponse:
    """플랫폼 관리자용 심사원 목록 (검색·페이징)."""
    query = db.query(Auditor)

    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter(
            (Auditor.name.ilike(like))
            | (Auditor.email.ilike(like))
            | (Auditor.phone.ilike(like))
        )

    total_count = query.count()
    auditors = (
        query.order_by(Auditor.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return AuditorListResponse(
        total=total_count,
        page=page,
        limit=limit,
        data=[AuditorSummaryResponse.model_validate(a) for a in auditors],
    )


@router.get("/{auditor_id}", response_model=AuditorDetailResponse)
def get_admin_auditor_detail(
    auditor_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> AuditorDetailResponse:
    """플랫폼 관리자용 심사원 상세 (프로필·소속·학력·경력)."""
    auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 정보를 찾을 수 없습니다.",
        )

    memberships = (
        db.query(AuditorCbMemberships)
        .filter(AuditorCbMemberships.auditor_id == auditor_id)
        .order_by(AuditorCbMemberships.id.desc())
        .all()
    )
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

    return AuditorDetailResponse(
        profile=AuditorProfileDetail.model_validate(auditor),
        memberships=[MembershipItem.model_validate(m) for m in memberships],
        educations=[EducationItem.model_validate(e) for e in educations],
        careers=[CareerItem.model_validate(c) for c in careers],
    )
