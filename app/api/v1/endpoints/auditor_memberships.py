"""심사원 → CB 소속/자격 신청 API (Identity와 Membership 분리)."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.auditor import Auditor, AuditorCbMemberships
from app.models.cb import CertificationBodies
from app.models.enums import AuditorCbMembershipsStatus, UsersRole

router = APIRouter(prefix="/auditor/memberships", tags=["Auditor Memberships"])

# DB ENUM은 requested — 요구사항의 pending 과 동일 의미
_PENDING_STATUS = AuditorCbMembershipsStatus.REQUESTED.value


class MembershipRequestBody(BaseModel):
    cb_id: int = Field(..., description="신청할 인증기관 ID")
    apply_grade: str = Field(default="auditor", description="신청 등급")
    employment_type: str = Field(default="parttime", description="fulltime | parttime")
    is_freelance: bool = False
    apply_message: Optional[str] = None
    daily_rate: Optional[int] = None
    # 학력/경력 기반 IAF 신청
    major: Optional[str] = Field(None, description="전공학과명")
    company_id: Optional[int] = Field(None, description="경력 기업 ID")
    company_name: Optional[str] = Field(None, description="경력 기업명")
    ksic_code: Optional[str] = None
    requested_iaf_codes: List[str] = Field(
        default_factory=list,
        description="신청 Scope IAF 코드 목록 (예: ['14','19'])",
    )


class MembershipRequestResponse(BaseModel):
    message: str
    membership_id: int
    auditor_id: int
    cb_id: int
    cb_name: Optional[str] = None
    status: str
    apply_grade: Optional[str] = None
    requested_iaf_codes: List[str] = Field(default_factory=list)


class MyMembershipItem(BaseModel):
    id: int
    cb_id: int
    cb_name: Optional[str] = None
    cb_code: Optional[str] = None
    status: str
    apply_grade: Optional[str] = None
    approved_grade: Optional[str] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    requested_iaf_codes: List[str] = Field(default_factory=list)
    major: Optional[str] = None
    company_name: Optional[str] = None
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None


def _require_auditor(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.AUDITOR.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="심사원 계정만 소속 신청을 할 수 있습니다.",
        )
    return current_user


def _get_auditor_for_user(db: Session, user_id: int) -> Auditor:
    auditor = db.query(Auditor).filter(Auditor.user_id == user_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 프로필이 없습니다. 심사원 가입을 먼저 완료하세요.",
        )
    return auditor


def _normalize_iaf_codes(codes: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for c in codes or []:
        text = str(c).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _build_request_metadata(payload: MembershipRequestBody) -> Dict[str, Any]:
    iaf_codes = _normalize_iaf_codes(payload.requested_iaf_codes)
    return {
        "requested_iaf_codes": iaf_codes,
        "education": {"major": payload.major.strip()} if payload.major and payload.major.strip() else None,
        "career": {
            "company_id": payload.company_id,
            "company_name": payload.company_name,
            "ksic_code": payload.ksic_code,
        }
        if payload.company_id or payload.company_name
        else None,
    }


def _meta_list(meta: Optional[dict], key: str) -> List[str]:
    if not isinstance(meta, dict):
        return []
    val = meta.get(key)
    if isinstance(val, list):
        return [str(x) for x in val if x]
    return []


def _meta_major(meta: Optional[dict]) -> Optional[str]:
    if not isinstance(meta, dict):
        return None
    edu = meta.get("education")
    if isinstance(edu, dict):
        major = edu.get("major")
        return str(major) if major else None
    return None


def _meta_company_name(meta: Optional[dict]) -> Optional[str]:
    if not isinstance(meta, dict):
        return None
    career = meta.get("career")
    if isinstance(career, dict):
        name = career.get("company_name")
        return str(name) if name else None
    return None


def _apply_request_fields(membership: AuditorCbMemberships, payload: MembershipRequestBody) -> None:
    membership.apply_grade = payload.apply_grade
    membership.employment_type = payload.employment_type
    membership.is_freelance = payload.is_freelance
    membership.apply_message = payload.apply_message
    membership.daily_rate = payload.daily_rate
    membership.extra_metadata = _build_request_metadata(payload)


@router.post("/request", response_model=MembershipRequestResponse, status_code=status.HTTP_201_CREATED)
def request_cb_membership(
    payload: MembershipRequestBody,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사원이 특정 CB에 소속/자격 신청 (status=requested ≈ pending)."""
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == payload.cb_id).first()
    if not cb:
        raise HTTPException(status_code=404, detail="선택한 인증기관을 찾을 수 없습니다.")

    existing = (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.auditor_id == auditor.id,
            AuditorCbMemberships.cb_id == payload.cb_id,
        )
        .first()
    )
    if existing:
        if existing.status in {
            AuditorCbMembershipsStatus.APPROVED.value,
            AuditorCbMembershipsStatus.REQUESTED.value,
            AuditorCbMembershipsStatus.UNDER_REVIEW.value,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"이미 해당 인증기관에 대한 신청/소속이 있습니다. (status={existing.status})",
            )
        # rejected/terminated 등은 재신청 — 동일 레코드 갱신
        now = datetime.utcnow()
        _apply_request_fields(existing, payload)
        existing.status = _PENDING_STATUS
        existing.approved_grade = None
        existing.approved_at = None
        existing.approved_by = None
        existing.reject_reason = None
        existing.requested_at = now
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return MembershipRequestResponse(
            message="인증기관 소속 신청이 재접수되었습니다.",
            membership_id=existing.id,
            auditor_id=auditor.id,
            cb_id=cb.id,
            cb_name=cb.name,
            status=existing.status,
            apply_grade=existing.apply_grade,
            requested_iaf_codes=_normalize_iaf_codes(payload.requested_iaf_codes),
        )

    now = datetime.utcnow()
    has_any = (
        db.query(AuditorCbMemberships.id)
        .filter(AuditorCbMemberships.auditor_id == auditor.id)
        .first()
        is not None
    )
    membership = AuditorCbMemberships(
        auditor_id=auditor.id,
        cb_id=payload.cb_id,
        employment_type=payload.employment_type,
        is_freelance=payload.is_freelance,
        status=_PENDING_STATUS,
        is_primary=not has_any,
        apply_grade=payload.apply_grade,
        apply_message=payload.apply_message,
        daily_rate=payload.daily_rate,
        extra_metadata=_build_request_metadata(payload),
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return MembershipRequestResponse(
        message="인증기관 소속/자격 신청이 접수되었습니다.",
        membership_id=membership.id,
        auditor_id=auditor.id,
        cb_id=cb.id,
        cb_name=cb.name,
        status=membership.status,
        apply_grade=membership.apply_grade,
        requested_iaf_codes=_normalize_iaf_codes(payload.requested_iaf_codes),
    )


@router.get("/mine", response_model=List[MyMembershipItem])
def list_my_memberships(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사원 본인의 CB 소속 신청/승인 목록 (본인만 — 전체 CB 가능)."""
    _require_auditor(current_user)
    auditor = _get_auditor_for_user(db, current_user.id)

    rows = (
        db.query(AuditorCbMemberships, CertificationBodies)
        .outerjoin(
            CertificationBodies,
            CertificationBodies.id == AuditorCbMemberships.cb_id,
        )
        .filter(AuditorCbMemberships.auditor_id == auditor.id)
        .order_by(AuditorCbMemberships.id.desc())
        .all()
    )
    return [
        MyMembershipItem(
            id=m.id,
            cb_id=m.cb_id,
            cb_name=cb.name if cb else None,
            cb_code=cb.code if cb else None,
            status=m.status,
            apply_grade=m.apply_grade,
            approved_grade=m.approved_grade,
            cert_standards=m.cert_standards,
            approved_iaf_codes=m.approved_iaf_codes,
            requested_iaf_codes=_meta_list(m.extra_metadata, "requested_iaf_codes"),
            major=_meta_major(m.extra_metadata),
            company_name=_meta_company_name(m.extra_metadata),
            requested_at=m.requested_at,
            approved_at=m.approved_at,
        )
        for m, cb in rows
    ]
