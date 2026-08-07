"""플랫폼 관리자 — 심사원 마스터 목록/상세 + 근무 상태.

개인정보·자격·경력 마스터 전체 PUT 은 차단합니다.
허용:
  PATCH /{id}/status          — 근무 상태 (active/leave/suspended)

자격 승인/거절은 인증기관(CB) 권한입니다
(PATCH /api/v1/cb/memberships/{id}/approve).
"""
import logging
from datetime import date, datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_platform_admin
from app.models.auditor import (
    Auditor,
    AuditorEducation,
    AuditorExternalCert,
    AuditorWorkExperience,
)
from app.models.cb import CertificationBodies

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/auditors", tags=["Admin Auditors"])

# DB ENUM: auditors.status — active/leave/suspended
AUDITOR_STATUS_VALUES = frozenset({"active", "leave", "suspended"})

_MASTER_WRITE_BLOCKED = (
    "플랫폼 관리자는 심사원 마스터 프로필을 수정할 수 없습니다. "
    "상태 변경은 PATCH /api/v1/admin/auditors/{id}/status 를 사용하세요. "
    "자격 승인/거절은 인증기관(CB)에서 처리합니다."
)

_QUALIFY_CB_ONLY = (
    "자격 승인/거절은 인증기관(CB) 권한입니다. "
    "CB 포털에서 PATCH /api/v1/cb/memberships/{id}/approve 를 사용하세요."
)


def _block_master_write() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=_MASTER_WRITE_BLOCKED,
    )

# Live MySQL may lag ORM extensions on auditor_cb_memberships — select only known cols.
_MEMBERSHIP_SQL = text(
    """
    SELECT
      id, auditor_id, cb_id, employment_type, is_freelance, status, is_primary,
      apply_grade, approved_grade, grade_at_cb, approved_iaf_codes, cert_standards,
      kar_no, daily_rate, fee_ratio, reject_reason, cb_review_note, memo,
      requested_at, approved_at, created_at, updated_at
    FROM auditor_cb_memberships
    WHERE auditor_id = :auditor_id
    ORDER BY id DESC
    """
)


def _query_memberships(db: Session, auditor_id: int) -> List[dict]:
    rows = db.execute(_MEMBERSHIP_SQL, {"auditor_id": auditor_id}).mappings().all()
    return [dict(r) for r in rows]


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
    complais_no: Optional[str] = None
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
    primary_cb_name: Optional[str] = None
    primary_cb_code: Optional[str] = None
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
    total_working_days: Optional[int] = None
    cb_affiliation: Optional[str] = None
    income_type: Optional[str] = None
    commission_type: Optional[str] = None
    security_pledge_agreed: Optional[bool] = None
    subcontract_agreed: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditorProfileUpdate(BaseModel):
    """레거시 PUT 바디 — 플랫폼 관리자 PUT 은 405 로 차단됨."""

    name: Optional[str] = None
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
    cb_affiliation: Optional[str] = None
    income_type: Optional[str] = None
    commission_type: Optional[str] = None
    complais_no: Optional[str] = None


class AuditorStatusUpdate(BaseModel):
    """근무 상태만 — active | leave | suspended."""

    status: str = Field(..., description="active | leave | suspended")


class AuditorActionResponse(BaseModel):
    ok: bool = True
    id: int
    status: Optional[str] = None
    profile_status: Optional[str] = None
    updated_at: Optional[datetime] = None
    message: Optional[str] = None


class MembershipItem(BaseModel):
    id: int
    auditor_id: int
    cb_id: int
    cb_name: Optional[str] = None
    cb_code: Optional[str] = None
    employment_type: str
    is_freelance: bool
    status: str
    is_primary: bool
    apply_grade: Optional[str] = None
    approved_grade: Optional[str] = None
    grade_at_cb: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    cert_standards: Optional[str] = None
    kar_no: Optional[str] = None
    daily_rate: Optional[int] = None
    fee_ratio: Optional[Any] = None
    reject_reason: Optional[str] = None
    cb_review_note: Optional[str] = None
    memo: Optional[str] = None
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


class ExternalCertItem(BaseModel):
    id: int
    auditor_id: int
    cert_name: str
    issuer: str
    cert_no: str
    grade: str
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditorDetailResponse(BaseModel):
    profile: AuditorProfileDetail
    memberships: List[MembershipItem]
    educations: List[EducationItem]
    careers: List[CareerItem]
    external_certs: List[ExternalCertItem] = Field(default_factory=list)


def _cb_map(db: Session, cb_ids: List[int]) -> dict[int, CertificationBodies]:
    ids = sorted({i for i in cb_ids if i})
    if not ids:
        return {}
    rows = db.query(CertificationBodies).filter(CertificationBodies.id.in_(ids)).all()
    return {r.id: r for r in rows}


def _profile_detail(db: Session, auditor: Auditor) -> AuditorProfileDetail:
    data = AuditorProfileDetail.model_validate(auditor)
    if auditor.primary_cb_id:
        cb = (
            db.query(CertificationBodies)
            .filter(CertificationBodies.id == auditor.primary_cb_id)
            .first()
        )
        if cb:
            data.primary_cb_name = cb.name
            data.primary_cb_code = cb.code
    return data


def _membership_items(
    memberships: List[dict],
    cbs: dict[int, CertificationBodies],
) -> List[MembershipItem]:
    items: List[MembershipItem] = []
    for m in memberships:
        item = MembershipItem(
            id=m["id"],
            auditor_id=m["auditor_id"],
            cb_id=m["cb_id"],
            employment_type=m["employment_type"],
            is_freelance=bool(m["is_freelance"]),
            status=m["status"],
            is_primary=bool(m["is_primary"]),
            apply_grade=m.get("apply_grade"),
            approved_grade=m.get("approved_grade"),
            grade_at_cb=m.get("grade_at_cb"),
            approved_iaf_codes=m.get("approved_iaf_codes"),
            cert_standards=m.get("cert_standards"),
            kar_no=m.get("kar_no"),
            daily_rate=m.get("daily_rate"),
            fee_ratio=m.get("fee_ratio"),
            reject_reason=m.get("reject_reason"),
            cb_review_note=m.get("cb_review_note"),
            memo=m.get("memo"),
            requested_at=m.get("requested_at"),
            approved_at=m.get("approved_at"),
            created_at=m.get("created_at"),
            updated_at=m.get("updated_at"),
        )
        cb = cbs.get(m["cb_id"])
        if cb:
            item.cb_name = cb.name
            item.cb_code = cb.code
        items.append(item)
    return items


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
    """플랫폼 관리자용 심사원 상세 (프로필·소속·학력·경력·외부자격)."""
    auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 정보를 찾을 수 없습니다.",
        )

    return _build_detail_response(db, auditor)


def _build_detail_response(db: Session, auditor: Auditor) -> AuditorDetailResponse:
    auditor_id = int(auditor.id)
    memberships = _query_memberships(db, auditor_id)
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
    try:
        external_certs = (
            db.query(AuditorExternalCert)
            .filter(AuditorExternalCert.auditor_id == auditor_id)
            .order_by(AuditorExternalCert.id.desc())
            .all()
        )
    except Exception:
        db.rollback()
        external_certs = []
    cbs = _cb_map(
        db,
        [m["cb_id"] for m in memberships]
        + ([auditor.primary_cb_id] if auditor.primary_cb_id else []),
    )
    return AuditorDetailResponse(
        profile=_profile_detail(db, auditor),
        memberships=_membership_items(memberships, cbs),
        educations=[EducationItem.model_validate(e) for e in educations],
        careers=[CareerItem.model_validate(c) for c in careers],
        external_certs=[ExternalCertItem.model_validate(x) for x in external_certs],
    )


@router.put("/{auditor_id}", response_model=AuditorDetailResponse)
def update_admin_auditor(
    auditor_id: int,
    payload: AuditorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> AuditorDetailResponse:
    """플랫폼 관리자 전체 PUT 차단 — 상태 전용 PATCH 사용."""
    _ = (auditor_id, payload, db, current_user)
    _block_master_write()


def _get_auditor_or_404(db: Session, auditor_id: int) -> Auditor:
    auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 정보를 찾을 수 없습니다.",
        )
    return auditor


@router.patch("/{auditor_id}/status", response_model=AuditorActionResponse)
def patch_admin_auditor_status(
    auditor_id: int,
    payload: AuditorStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> AuditorActionResponse:
    """심사원 근무 상태만 변경 (active/leave/suspended)."""
    _ = current_user
    new_status = (payload.status or "").strip()
    if new_status not in AUDITOR_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태입니다. 허용: {', '.join(sorted(AUDITOR_STATUS_VALUES))}",
        )
    try:
        auditor = _get_auditor_or_404(db, auditor_id)
        auditor.status = new_status
        auditor.is_active = new_status == "active"
        auditor.updated_at = datetime.utcnow()
        db.add(auditor)
        db.commit()
        db.refresh(auditor)
        return AuditorActionResponse(
            ok=True,
            id=int(auditor.id),
            status=auditor.status,
            profile_status=auditor.profile_status,
            updated_at=auditor.updated_at,
            message="근무 상태가 변경되었습니다.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("auditor status PATCH failed for auditor_id=%s", auditor_id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"심사원 상태 변경에 실패했습니다: {exc.__class__.__name__}",
        ) from exc


@router.patch("/{auditor_id}/approve")
def approve_admin_auditor_forbidden(
    auditor_id: int,
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> None:
    """자격 승인은 CB 전용 — 플랫폼 관리자 호출은 거부."""
    _ = auditor_id
    _ = current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_QUALIFY_CB_ONLY,
    )


@router.patch("/{auditor_id}/reject")
def reject_admin_auditor_forbidden(
    auditor_id: int,
    current_user: CurrentUser = Depends(get_current_platform_admin),
) -> None:
    """자격 거절은 CB 전용 — 플랫폼 관리자 호출은 거부."""
    _ = auditor_id
    _ = current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_QUALIFY_CB_ONLY,
    )
