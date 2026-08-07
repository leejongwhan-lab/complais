"""CB 어드민 프로필 + Scope 통합 조회/수정 API.

프로필 소스는 certification_bodies (명세의 cb_profiles 역할).
승인 Scope는 cb_accredited_scopes 를 LEFT JOIN 형태로 함께 반환한다.
표준별 인정/MD단가는 cb_standard_accreditations (CB만 md_rate 쓰기).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.api.v1.endpoints.admin_cb import (
    StandardAccreditationItem,
    StandardAccreditationUpdate,
    _list_standard_accreditations,
    _upsert_standard_accreditations,
)
from app.core.security import CurrentUser, require_cb_scope
from app.models.cb import CertificationBodies
from app.models.certification_body import cb_to_spec_dict
from app.models.enums import UsersRole
from app.models.master_data import CbAccreditedScope

router = APIRouter(prefix="/cb", tags=["CB Profile"])

_STATUS_LABEL = {
    "active": "정상",
    "suspended": "정지",
    "withdrawn": "철회",
}


class CbProfileScopeItem(BaseModel):
    scope_id: int
    standard_id: int
    iaf_code_id: int
    standard_code: Optional[str] = None
    standard_name_ko: Optional[str] = None
    iaf_code: Optional[str] = None
    industry_name_ko: Optional[str] = None
    accreditation_body: Optional[str] = None
    approval_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "active"
    status_label: str = "정상"


class CbProfileOut(BaseModel):
    """CB 프로필 — Admin ``cb_to_spec_dict`` 와 동일 마스터 별칭 포함."""

    cb_id: int
    code: Optional[str] = None
    cb_code: Optional[str] = None
    name: Optional[str] = None
    cb_name: Optional[str] = None
    name_en: Optional[str] = None
    cb_name_en: Optional[str] = None
    cb_initial: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    biz_reg_no: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    intro: Optional[str] = None
    accreditation_body: Optional[str] = None
    accreditation_no: Optional[str] = None
    reg_no: Optional[str] = None
    accreditation_region: Optional[str] = None
    accreditation_country: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = None
    tax_email: Optional[str] = None
    logo_path: Optional[str] = None
    is_active: bool = True
    scopes: List[CbProfileScopeItem] = Field(default_factory=list)
    scope_count: int = 0
    has_profile: bool = True
    message: Optional[str] = None


class CbProfileUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    intro: Optional[str] = None
    accreditation_body: Optional[str] = None
    accreditation_no: Optional[str] = None
    accreditation_region: Optional[str] = None
    accreditation_country: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = None
    tax_email: Optional[str] = None


def _require_cb_manager(current_user: CurrentUser) -> CurrentUser:
    if current_user.role not in {
        UsersRole.CB_ADMIN.value,
        UsersRole.CB_MANAGER.value,
        UsersRole.PLATFORM_ADMIN.value,
    }:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    return current_user


def _resolve_cb_id(current_user: CurrentUser, cb_id: Optional[int]) -> int:
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        if not cb_id:
            raise HTTPException(status_code=400, detail="platform_admin은 cb_id가 필요합니다.")
        return cb_id
    if current_user.cb_id is None:
        raise HTTPException(status_code=403, detail="소속 인증원(CB) 정보가 없습니다.")
    if cb_id and cb_id != current_user.cb_id:
        raise HTTPException(status_code=403, detail="다른 인증기관 정보는 접근할 수 없습니다.")
    return current_user.cb_id


def _sync_denormalized_scope_summary(db: Session, cb: CertificationBodies) -> None:
    """레거시 컬럼(accredited_standards / iaf_scopes)을 최신 Scope 기준으로 동기화."""
    rows = (
        db.query(CbAccreditedScope)
        .options(
            joinedload(CbAccreditedScope.standard),
            joinedload(CbAccreditedScope.iaf_code),
        )
        .filter(
            CbAccreditedScope.cb_id == cb.id,
            CbAccreditedScope.status == "active",
        )
        .all()
    )
    standards = sorted(
        {
            r.standard.standard_code
            for r in rows
            if r.standard and r.standard.standard_code
        }
    )
    iafs = sorted({r.iaf_code.code for r in rows if r.iaf_code and r.iaf_code.code})
    cb.accredited_standards = ", ".join(standards) if standards else None
    cb.iaf_scopes = ", ".join(iafs) if iafs else None


def _load_scopes(db: Session, cb_id: int) -> List[CbProfileScopeItem]:
    rows = (
        db.query(CbAccreditedScope)
        .options(
            joinedload(CbAccreditedScope.standard),
            joinedload(CbAccreditedScope.iaf_code),
        )
        .filter(CbAccreditedScope.cb_id == cb_id)
        .order_by(CbAccreditedScope.id.desc())
        .all()
    )
    out: List[CbProfileScopeItem] = []
    for r in rows:
        out.append(
            CbProfileScopeItem(
                scope_id=r.id,
                standard_id=r.standard_id,
                iaf_code_id=r.iaf_code_id,
                standard_code=r.standard.standard_code if r.standard else None,
                standard_name_ko=r.standard.standard_name_ko if r.standard else None,
                iaf_code=r.iaf_code.code if r.iaf_code else None,
                industry_name_ko=r.iaf_code.name_ko if r.iaf_code else None,
                accreditation_body=r.accreditation_body,
                approval_date=r.approval_date.isoformat() if r.approval_date else None,
                expiry_date=r.expiry_date.isoformat() if r.expiry_date else None,
                status=r.status or "active",
                status_label=_STATUS_LABEL.get(r.status or "active", r.status or "active"),
            )
        )
    return out


def _to_profile_out(cb: CertificationBodies, scopes: List[CbProfileScopeItem]) -> CbProfileOut:
    """Admin CB detail 과 동일 ``cb_to_spec_dict`` 베이스 + 포털 Scope."""
    spec = cb_to_spec_dict(cb)
    has_basic = bool(
        (spec.get("cb_name") or spec.get("name") or "").strip()
        or (spec.get("ceo_name") or "").strip()
        or (spec.get("address") or "").strip()
    )
    expire = getattr(cb, "expire_date", None)
    return CbProfileOut(
        cb_id=int(spec["id"]),
        code=spec.get("cb_code") or spec.get("code"),
        cb_code=spec.get("cb_code") or spec.get("code"),
        name=spec.get("cb_name") or spec.get("name"),
        cb_name=spec.get("cb_name") or spec.get("name"),
        name_en=spec.get("cb_name_en") or spec.get("name_en"),
        cb_name_en=spec.get("cb_name_en") or spec.get("name_en"),
        cb_initial=spec.get("cb_initial"),
        ceo_name=spec.get("ceo_name"),
        biz_no=spec.get("biz_reg_no") or spec.get("biz_no"),
        biz_reg_no=spec.get("biz_reg_no") or spec.get("biz_no"),
        address=spec.get("address"),
        tel=spec.get("tel"),
        phone=getattr(cb, "phone", None) or spec.get("tel"),
        fax=getattr(cb, "fax", None),
        email=spec.get("email"),
        website=spec.get("website"),
        intro=getattr(cb, "intro", None),
        accreditation_body=spec.get("accreditation_body"),
        accreditation_no=spec.get("reg_no") or getattr(cb, "accreditation_no", None),
        reg_no=spec.get("reg_no"),
        accreditation_region=getattr(cb, "accreditation_region", None),
        accreditation_country=getattr(cb, "accreditation_country", None),
        expire_date=expire.isoformat() if hasattr(expire, "isoformat") and expire else expire,
        status=spec.get("status") or getattr(cb, "status", None),
        tax_email=getattr(cb, "tax_email", None),
        logo_path=spec.get("logo_path"),
        is_active=bool(getattr(cb, "is_active", True)),
        scopes=scopes,
        scope_count=len(scopes),
        has_profile=has_basic,
        message=None
        if has_basic
        else "등록된 인증기관 정보가 없습니다. 정보를 입력하거나 CSV를 업로드해 주세요.",
    )


@router.get(
    "/standard-accreditations",
    response_model=List[StandardAccreditationItem],
)
def get_my_standard_accreditations(
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """소속 CB의 보유 표준·인정번호·만료일·MD단가 조회."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, cb_id)
    cb = db.get(CertificationBodies, scope_cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    return _list_standard_accreditations(db, scope_cb_id)


@router.put(
    "/standard-accreditations",
    response_model=List[StandardAccreditationItem],
)
def put_my_standard_accreditations(
    payload: StandardAccreditationUpdate,
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """소속 CB 보유 표준 저장 — md_rate(표준별 MD단가) 쓰기 허용."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, cb_id)
    cb = db.get(CertificationBodies, scope_cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    _upsert_standard_accreditations(
        db,
        cb.id,
        payload.items,
        replace_all=payload.replace_all,
        allow_md_rate=True,
    )
    cb.updated_at = datetime.utcnow()
    db.commit()
    return _list_standard_accreditations(db, scope_cb_id)


@router.get("/profile", response_model=CbProfileOut)
def get_cb_profile(
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """세션 cb_id 기준 기관 정보 + 승인 Scope(LEFT JOIN) 최신 조회."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, cb_id)

    # 캐시된 세션 객체 잔존 방지 — 최신 스냅샷
    db.expire_all()

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == scope_cb_id).first()
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 인증기관 정보가 없습니다. 정보를 입력하거나 CSV를 업로드해 주세요.",
        )

    scopes = _load_scopes(db, scope_cb_id)
    return _to_profile_out(cb, scopes)


@router.put("/profile", response_model=CbProfileOut)
def update_cb_profile(
    payload: CbProfileUpdate,
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """인증기관 기본 정보 수정 후 최신 프로필(+Scope) 반환."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, cb_id)

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == scope_cb_id).first()
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록된 인증기관 정보가 없습니다. 정보를 입력하거나 CSV를 업로드해 주세요.",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(cb, field, value)

    # phone/tel 상호 보정
    if "phone" in data and data["phone"] and not data.get("tel"):
        cb.tel = data["phone"]
    if "tel" in data and data["tel"] and not data.get("phone"):
        cb.phone = data["tel"]

    _sync_denormalized_scope_summary(db, cb)
    cb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cb)
    db.expire_all()

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == scope_cb_id).first()
    scopes = _load_scopes(db, scope_cb_id)
    return _to_profile_out(cb, scopes)
