"""심사원 → CB 소속/자격 신청 API (Identity와 Membership 분리)."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.auditor import Auditor, AuditorCbMemberships
from app.models.cb import CertificationBodies
from app.models.enums import AuditorCbMembershipsStatus, UsersRole
from app.services.auditor_grade import to_db_grade, to_ui_grade
from app.services.auditor_profile_persist import (
    add_educations,
    add_qualifications,
    add_work_experiences,
    career_from_affiliation,
    normalize_iaf_codes,
)

router = APIRouter(prefix="/auditor/memberships", tags=["Auditor Memberships"])

# DB ENUM은 requested — 요구사항의 pending 과 동일 의미
_PENDING_STATUS = AuditorCbMembershipsStatus.REQUESTED.value


class EducationApplyItem(BaseModel):
    """auth.EducationItem 과 동일 형상 — 학력 다중 행."""

    school_name: str
    degree: str = "bachelor"  # high_school|associate|bachelor|master|doctor|other
    major: Optional[str] = None
    entered_at: Optional[str] = None
    graduated_at: Optional[str] = None


class CareerApplyItem(BaseModel):
    """auth.WorkExperienceItem 과 동일 형상 — 경력 다중 행."""

    company_name: str
    company_id: Optional[int] = None
    biz_no: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    is_temporary: bool = False
    duties: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    note: Optional[str] = None


class QualificationApplyItem(BaseModel):
    standard_code: str
    cert_body_name: Optional[str] = None
    cert_no: Optional[str] = None
    auditor_grade: Optional[str] = None
    iaf_codes: List[str] = Field(default_factory=list)
    major_name: Optional[str] = None


class MembershipRequestBody(BaseModel):
    cb_id: int = Field(..., description="신청할 인증기관 ID")
    apply_grade: str = Field(default="auditor", description="신청 등급")
    employment_type: str = Field(default="parttime", description="fulltime | parttime")
    is_freelance: bool = False
    apply_message: Optional[str] = None
    daily_rate: Optional[int] = None
    # 학력/경력 다중 행 (register/auth 와 동일 형상)
    educations: List[EducationApplyItem] = Field(
        default_factory=list,
        description="학력 목록 (degree/school_name/major)",
    )
    work_experiences: List[CareerApplyItem] = Field(
        default_factory=list,
        description="경력 목록 (register work_experiences 와 동일)",
    )
    # 레거시 단일 필드 — 목록이 비어 있을 때만 폴백
    major: Optional[str] = Field(None, description="[legacy] 전공학과명")
    company_id: Optional[int] = Field(None, description="[legacy] 경력 기업 ID")
    company_name: Optional[str] = Field(None, description="[legacy] 경력 기업명")
    biz_no: Optional[str] = None
    ksic_code: Optional[str] = None
    is_temporary: bool = Field(False, description="[legacy] 미등록 기업 직접입력")
    career_start_date: Optional[str] = None
    career_end_date: Optional[str] = None
    duties: Optional[str] = None
    position: Optional[str] = None
    requested_iaf_codes: List[str] = Field(
        default_factory=list,
        description="신청 Scope IAF 코드 목록 (예: ['14','19'])",
    )
    qualifications: List[QualificationApplyItem] = Field(
        default_factory=list,
        description="심사 자격 정보 (표준별 발급기관/번호/등급)",
    )
    cert_standards: Optional[List[str]] = Field(
        default=None,
        description="신청 표준 코드 목록 (없으면 qualifications에서 도출)",
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
    qualification_count: int = 0
    career_saved: bool = False


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


def _item_get(item: Any, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _primary_major(payload: MembershipRequestBody) -> Optional[str]:
    for edu in payload.educations or []:
        major = (_item_get(edu, "major") or "").strip()
        if major:
            return major
    major = (payload.major or "").strip()
    return major or None


def _normalize_education_items(payload: MembershipRequestBody) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for edu in payload.educations or []:
        school = (_item_get(edu, "school_name") or "").strip()
        major = (_item_get(edu, "major") or "").strip() or None
        if not school and not major:
            continue
        out.append(
            {
                "school_name": school or "미입력",
                "degree": (_item_get(edu, "degree") or "bachelor") or "bachelor",
                "major": major,
                "entered_at": _item_get(edu, "entered_at"),
                "graduated_at": _item_get(edu, "graduated_at"),
            }
        )
    if out:
        return out
    major = (payload.major or "").strip()
    if major:
        return [{"school_name": "미입력", "degree": "bachelor", "major": major}]
    return []


def _normalize_career_items(payload: MembershipRequestBody) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for work in payload.work_experiences or []:
        name = (_item_get(work, "company_name") or "").strip()
        company_id = _item_get(work, "company_id")
        if not name and not company_id:
            continue
        start = _item_get(work, "start_date") or date.today().isoformat()
        end = _item_get(work, "end_date")
        out.append(
            {
                "company_id": company_id,
                "company_name": name or f"company#{company_id}",
                "biz_no": _item_get(work, "biz_no"),
                "department": _item_get(work, "department"),
                "position": _item_get(work, "position"),
                "start_date": start,
                "end_date": end,
                "is_current": bool(_item_get(work, "is_current")) or not bool(end),
                "is_temporary": bool(_item_get(work, "is_temporary"))
                or (company_id is None and bool(name)),
                "duties": _item_get(work, "duties"),
                "ksic_code": _item_get(work, "ksic_code"),
                "iaf_code": _item_get(work, "iaf_code"),
                "note": _item_get(work, "note") or _item_get(work, "duties"),
            }
        )
    if out:
        return out
    legacy = career_from_affiliation(
        company_id=payload.company_id,
        company_name=payload.company_name,
        biz_no=payload.biz_no,
        ksic_code=payload.ksic_code,
        is_temporary=payload.is_temporary,
        start_date=payload.career_start_date,
        end_date=payload.career_end_date,
        duties=payload.duties,
        position=payload.position,
        iaf_codes=payload.requested_iaf_codes,
    )
    return [legacy] if legacy else []


def _build_request_metadata(payload: MembershipRequestBody) -> Dict[str, Any]:
    iaf_codes = normalize_iaf_codes(payload.requested_iaf_codes)
    primary_major = _primary_major(payload)
    educations = _normalize_education_items(payload)
    careers = _normalize_career_items(payload)
    quals = [
        {
            "standard_code": q.standard_code,
            "cert_body_name": q.cert_body_name,
            "cert_no": q.cert_no,
            "auditor_grade": q.auditor_grade or payload.apply_grade,
            "iaf_codes": normalize_iaf_codes(q.iaf_codes or iaf_codes),
            "major_name": q.major_name or primary_major,
        }
        for q in (payload.qualifications or [])
    ]
    first_career = careers[0] if careers else None
    return {
        "requested_iaf_codes": iaf_codes,
        "educations": educations or None,
        "work_experiences": careers or None,
        # 레거시 단일 스냅샷 (목록 UI/어드민 호환)
        "education": {"major": primary_major} if primary_major else None,
        "career": {
            "company_id": first_career.get("company_id") if first_career else payload.company_id,
            "company_name": first_career.get("company_name") if first_career else payload.company_name,
            "biz_no": first_career.get("biz_no") if first_career else payload.biz_no,
            "ksic_code": first_career.get("ksic_code") if first_career else payload.ksic_code,
            "is_temporary": first_career.get("is_temporary") if first_career else payload.is_temporary,
            "duties": first_career.get("duties") if first_career else payload.duties,
            "start_date": first_career.get("start_date") if first_career else payload.career_start_date,
            "end_date": first_career.get("end_date") if first_career else payload.career_end_date,
        }
        if first_career or payload.company_id or payload.company_name
        else None,
        "qualifications": quals or None,
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
    for edu in meta.get("educations") or []:
        if isinstance(edu, dict) and edu.get("major"):
            return str(edu["major"])
    edu = meta.get("education")
    if isinstance(edu, dict):
        major = edu.get("major")
        return str(major) if major else None
    return None


def _meta_company_name(meta: Optional[dict]) -> Optional[str]:
    if not isinstance(meta, dict):
        return None
    for key in ("work_experiences", "careers"):
        for career in meta.get(key) or []:
            if isinstance(career, dict) and career.get("company_name"):
                return str(career["company_name"])
    career = meta.get("career")
    if isinstance(career, dict):
        name = career.get("company_name")
        return str(name) if name else None
    return None


def _standards_csv(payload: MembershipRequestBody) -> Optional[str]:
    codes: List[str] = []
    seen = set()
    for s in payload.cert_standards or []:
        t = str(s).strip().upper()
        if t and t not in seen:
            seen.add(t)
            codes.append(t)
    for q in payload.qualifications or []:
        t = (q.standard_code or "").strip().upper()
        if t and t not in seen:
            seen.add(t)
            codes.append(t)
    return ",".join(codes) if codes else None


def _persist_affiliation_rows(
    db: Session,
    *,
    auditor: Auditor,
    membership: AuditorCbMemberships,
    payload: MembershipRequestBody,
    now: datetime,
) -> tuple[int, bool]:
    """학력/경력/자격 행을 실제 테이블에 저장. (metadata 스냅샷과 병행)"""
    edu_items = _normalize_education_items(payload)
    major = _primary_major(payload)
    if major:
        auditor.major = major
    if edu_items:
        # IAF 매핑은 add_educations → resolve_iaf_from_major 내부 처리
        add_educations(db, auditor_id=auditor.id, items=edu_items, now=now)

    career_items = _normalize_career_items(payload)
    career_saved = False
    if career_items:
        # 요청 Scope의 첫 IAF를 경력 행에 보강 (없을 때만)
        iaf_hint = normalize_iaf_codes(payload.requested_iaf_codes)
        primary_iaf = iaf_hint[0] if iaf_hint else None
        for item in career_items:
            if primary_iaf and not item.get("iaf_code"):
                item["iaf_code"] = primary_iaf
        add_work_experiences(db, auditor_id=auditor.id, items=career_items, now=now)
        career_saved = True

    iaf_codes = normalize_iaf_codes(payload.requested_iaf_codes)
    qual_items: List[Any] = list(payload.qualifications or [])
    if not qual_items and _standards_csv(payload):
        # cert_standards only
        for s in (payload.cert_standards or []):
            qual_items.append(
                {
                    "standard_code": s,
                    "auditor_grade": payload.apply_grade,
                    "iaf_codes": iaf_codes,
                    "major_name": major,
                }
            )
    # 자격 미입력 + IAF만 있는 경우에도 표준 없으면 스킵
    for q in qual_items:
        if isinstance(q, dict):
            if not q.get("auditor_grade"):
                q["auditor_grade"] = payload.apply_grade
            if not q.get("major_name") and major:
                q["major_name"] = major
            if not q.get("iaf_codes"):
                q["iaf_codes"] = iaf_codes
        else:
            if not q.auditor_grade:
                q.auditor_grade = payload.apply_grade
            if not q.major_name and major:
                q.major_name = major
            if not q.iaf_codes:
                q.iaf_codes = iaf_codes

    qual_count = add_qualifications(
        db,
        auditor_id=auditor.id,
        items=qual_items,
        now=now,
        cb_id=payload.cb_id,
        membership_id=membership.id,
        default_major=major,
        default_iaf_codes=iaf_codes,
    )
    return qual_count, career_saved


def _apply_request_fields(membership: AuditorCbMemberships, payload: MembershipRequestBody) -> None:
    membership.apply_grade = to_db_grade(payload.apply_grade)
    membership.employment_type = payload.employment_type
    membership.is_freelance = payload.is_freelance
    membership.apply_message = payload.apply_message
    membership.daily_rate = payload.daily_rate
    membership.cert_standards = _standards_csv(payload)
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
        db.flush()
        qual_count, career_saved = _persist_affiliation_rows(
            db, auditor=auditor, membership=existing, payload=payload, now=now
        )
        db.commit()
        db.refresh(existing)
        return MembershipRequestResponse(
            message="인증기관 소속 신청이 재접수되었습니다.",
            membership_id=existing.id,
            auditor_id=auditor.id,
            cb_id=cb.id,
            cb_name=cb.name,
            status=existing.status,
            apply_grade=to_ui_grade(existing.apply_grade),
            requested_iaf_codes=normalize_iaf_codes(payload.requested_iaf_codes),
            qualification_count=qual_count,
            career_saved=career_saved,
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
        apply_grade=to_db_grade(payload.apply_grade),
        apply_message=payload.apply_message,
        daily_rate=payload.daily_rate,
        cert_standards=_standards_csv(payload),
        extra_metadata=_build_request_metadata(payload),
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(membership)
    db.flush()
    qual_count, career_saved = _persist_affiliation_rows(
        db, auditor=auditor, membership=membership, payload=payload, now=now
    )
    db.commit()
    db.refresh(membership)

    return MembershipRequestResponse(
        message="인증기관 소속/자격 신청이 접수되었습니다.",
        membership_id=membership.id,
        auditor_id=auditor.id,
        cb_id=cb.id,
        cb_name=cb.name,
        status=membership.status,
        apply_grade=to_ui_grade(membership.apply_grade),
        requested_iaf_codes=normalize_iaf_codes(payload.requested_iaf_codes),
        qualification_count=qual_count,
        career_saved=career_saved,
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
            apply_grade=to_ui_grade(m.apply_grade),
            approved_grade=to_ui_grade(m.approved_grade),
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
