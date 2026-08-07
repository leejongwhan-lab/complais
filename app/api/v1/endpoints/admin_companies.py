"""플랫폼 관리자 — 기업 마스터 목록/상세 (조회 + 상태 변경만).

기업 기본정보·인원·사업장·부서·담당자 마스터는 플랫폼 관리자가 덮어쓰지 않습니다.
상태만 PATCH /{id}/status 로 변경 가능합니다.

상태 enum (DB companies.status 코멘트와 동일):
  정상 / 휴업 / 폐업 / 인증취소
사용자 표현 승인·정지·대기 와의 정렬:
  승인 ≈ 정상, 정지 ≈ 휴업, 대기 = 해당 없음(기업 마스터에 pending 없음)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, computed_field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_admin_user
from app.models.company import Companies
from app.api.v1.endpoints.esg_master_kpis import fetch_company_esg_portal
from app.schemas.esg_master_kpi import EsgMasterKpiPortalListResponse
from app.services import company_org as org
from app.services.company_held_certs import (
    company_held_standard_labels,
    list_company_held_cert_status,
)

logger = logging.getLogger(__name__)


def _held_standards_safe(db: Session, company_id: int) -> List[Dict[str, Any]]:
    """Platform admin: full held standards + expiry fields (all CBs). Soft-fail → []."""
    try:
        return list_company_held_cert_status(
            db, int(company_id), cb_id=None, display_mode="admin_company"
        )
    except Exception:
        logger.exception("admin held_standards soft-fail company_id=%s", company_id)
        return []

router = APIRouter(prefix="/admin/companies", tags=["Admin Companies"])

# DB: companies.status — 정상/휴업/폐업/인증취소
COMPANY_STATUS_VALUES = frozenset({"정상", "휴업", "폐업", "인증취소"})

_MASTER_WRITE_BLOCKED = (
    "플랫폼 관리자는 기업 마스터 데이터를 수정할 수 없습니다. "
    "상태 변경만 PATCH /api/v1/admin/companies/{id}/status 로 가능합니다."
)


def _block_master_write() -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=_MASTER_WRITE_BLOCKED,
    )


# ─── List schemas ─────────────────────────────────────────────────

class CompanySummaryResponse(BaseModel):
    """기업 마스터 요약.

    DB 컬럼은 companies.id / companies.name 을 유지하고,
    API·UI 표준 용어는 company_id / company_name 으로 함께 노출합니다.
    """

    id: int
    name: str
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    entity_type: Optional[str] = None
    ceo_name: Optional[str] = None
    address_kr: Optional[str] = Field(default=None, validation_alias="address")
    address_en: Optional[str] = None
    website: Optional[str] = None
    biz_type: Optional[str] = None
    biz_class: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    status: Optional[str] = None
    held_standards: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def company_id(self) -> int:
        return self.id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def company_name(self) -> str:
        return self.name


class CompanyListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[CompanySummaryResponse]


# ─── Detail / org schemas ─────────────────────────────────────────

class SiteIn(BaseModel):
    site_name: str
    address: Optional[str] = None
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    zip_code: Optional[str] = None
    biz_no: Optional[str] = None
    employee_count: int = 0
    is_main: bool = False
    work_type: Optional[str] = None


class SiteOut(SiteIn):
    id: int
    company_id: int
    model_config = ConfigDict(from_attributes=True)


class DeptOut(BaseModel):
    id: int
    company_id: int
    name: str
    sort_order: int = 0
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class DeptBulkIn(BaseModel):
    names: List[str] = Field(default_factory=list)


class StaffIn(BaseModel):
    staff_name: str
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None


class StaffOut(StaffIn):
    id: int
    company_id: int
    model_config = ConfigDict(from_attributes=True)


class StaffBulkIn(BaseModel):
    items: List[StaffIn] = Field(default_factory=list)


class CompanyDetailResponse(BaseModel):
    """기업 마스터 상세 — company_id / company_name 표준 용어 포함."""

    id: int
    cert_no: Optional[str] = None
    name: str
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    entity_type: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_type: Optional[str] = None
    biz_class: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    zip_code: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    status: Optional[str] = None
    updated_at: Optional[str] = None
    employee_count: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    headcount_year: Optional[int] = None
    headcount_years: List[int] = Field(default_factory=list)
    sites: List[SiteOut] = Field(default_factory=list)
    departments: List[DeptOut] = Field(default_factory=list)
    staff: List[StaffOut] = Field(default_factory=list)
    held_standards: List[Dict[str, Any]] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def company_id(self) -> int:
        return self.id

    @computed_field  # type: ignore[prop-decorator]
    @property
    def company_name(self) -> str:
        return self.name


class CompanyProfileUpdate(BaseModel):
    """레거시 PUT 바디 스키마 — 플랫폼 관리자 PUT 은 405 로 차단됨."""

    name: Optional[str] = Field(default=None, validation_alias=AliasChoices("name", "company_name"))
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    entity_type: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_type: Optional[str] = None
    biz_class: Optional[str] = None
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    address_en: Optional[str] = None
    zip_code: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    employee_count: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    status: Optional[str] = None
    headcount_year: Optional[int] = Field(default=None, ge=2000, le=2100)

    model_config = ConfigDict(populate_by_name=True)


class CompanyStatusUpdate(BaseModel):
    """기업 상태만 변경 — 정상/휴업/폐업/인증취소."""

    status: str = Field(..., description="정상 | 휴업 | 폐업 | 인증취소")


class CompanyStatusResponse(BaseModel):
    ok: bool = True
    id: int
    status: str
    updated_at: Optional[str] = None


# ─── List ─────────────────────────────────────────────────────────

@router.get("", response_model=CompanyListResponse)
def get_companies(
    keyword: Optional[str] = Query(None, description="기업명 또는 사업자번호 검색"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> CompanyListResponse:
    query = db.query(Companies)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Companies.name.ilike(like))
            | (Companies.biz_no.ilike(like))
            | (Companies.name_en.ilike(like))
        )

    total_count = query.count()
    companies = (
        query.order_by(Companies.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    data: List[CompanySummaryResponse] = []
    for c in companies:
        item = CompanySummaryResponse.model_validate(c)
        item.held_standards = _held_standards_safe(db, int(c.id))
        data.append(item)

    return CompanyListResponse(
        total=total_count,
        page=page,
        limit=limit,
        data=data,
    )


# ─── Detail ───────────────────────────────────────────────────────

@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company_detail(
    company_id: int,
    headcount_year: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> CompanyDetailResponse:
    """마스터 DB 기업 상세 — 기본정보 + 인원(연도) + 사업장/부서/담당자 + 보유표준(전체 CB)."""
    _ = current_user
    try:
        detail = org.build_company_org_detail(db, company_id, headcount_year)
        detail["held_standards"] = _held_standards_safe(db, company_id)
        return CompanyDetailResponse.model_validate(detail)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("company detail failed for company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기업 상세 조회에 실패했습니다: {exc.__class__.__name__}",
        ) from exc


@router.get(
    "/{company_id}/esg-kpis",
    response_model=EsgMasterKpiPortalListResponse,
)
def get_company_esg_kpis(
    company_id: int,
    esg_category: Optional[str] = Query(None, description="E | S | G"),
    managed_standard_name: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    held_only: bool = Query(False),
    source_mode: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> EsgMasterKpiPortalListResponse:
    """Admin RO — Enterprise와 동일 ESG KPI 스키마 (쓰기 없음)."""
    _ = current_user
    org.get_company_or_404(db, company_id)
    held = company_held_standard_labels(
        db, company_id, cb_id=None, display_mode="admin_company"
    )
    return fetch_company_esg_portal(
        db,
        company_id,
        held_labels=held,
        esg_category=esg_category,
        managed_standard_name=managed_standard_name,
        q=q,
        held_only=held_only,
        source_mode=source_mode,
        skip=skip,
        limit=limit,
    )


@router.put("/{company_id}")
def update_company_detail(
    company_id: int,
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    """플랫폼 관리자 전체 PUT 차단 — 상태만 PATCH /{id}/status."""
    _ = (company_id, payload, db, current_user)
    _block_master_write()


@router.patch("/{company_id}/status", response_model=CompanyStatusResponse)
def patch_company_status(
    company_id: int,
    payload: CompanyStatusUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> CompanyStatusResponse:
    """기업 상태만 변경 (정상/휴업/폐업/인증취소). 마스터 필드는 보존."""
    _ = current_user
    new_status = (payload.status or "").strip()
    if new_status not in COMPANY_STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태입니다. 허용: {', '.join(sorted(COMPANY_STATUS_VALUES))}",
        )
    try:
        company = org.get_company_or_404(db, company_id)
        company.status = new_status
        company.updated_at = datetime.now()
        db.add(company)
        db.commit()
        db.refresh(company)
        return CompanyStatusResponse(
            ok=True,
            id=company.id,
            status=company.status or new_status,
            updated_at=company.updated_at.isoformat() if company.updated_at else None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("company status PATCH failed for company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"기업 상태 변경에 실패했습니다: {exc.__class__.__name__}",
        ) from exc


# ─── Sites (조회만) ────────────────────────────────────────────────

@router.get("/{company_id}/sites", response_model=List[SiteOut])
def admin_list_sites(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    return [SiteOut.model_validate(org.site_to_dict(r)) for r in org.list_additional_sites(db, company_id)]


@router.post("/{company_id}/sites", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def admin_create_site(
    company_id: int,
    payload: SiteIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, payload, db, current_user)
    _block_master_write()


@router.put("/{company_id}/sites/{site_id}", response_model=SiteOut)
def admin_update_site(
    company_id: int,
    site_id: int,
    payload: SiteIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, site_id, payload, db, current_user)
    _block_master_write()


@router.delete("/{company_id}/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_site(
    company_id: int,
    site_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, site_id, db, current_user)
    _block_master_write()


# ─── Departments (조회만) ─────────────────────────────────────────

@router.get("/{company_id}/departments", response_model=List[DeptOut])
def admin_list_departments(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    return [DeptOut.model_validate(org.dept_to_dict(r)) for r in org.list_active_departments(db, company_id)]


@router.put("/{company_id}/departments/bulk", response_model=List[DeptOut])
def admin_replace_departments(
    company_id: int,
    payload: DeptBulkIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, payload, db, current_user)
    _block_master_write()


@router.delete("/{company_id}/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_department(
    company_id: int,
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, dept_id, db, current_user)
    _block_master_write()


# ─── Staff (조회만) ───────────────────────────────────────────────

@router.get("/{company_id}/staff", response_model=List[StaffOut])
def admin_list_staff(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    return [StaffOut.model_validate(org.staff_to_dict(r)) for r in org.list_staff_members(db, company_id)]


@router.put("/{company_id}/staff/bulk", response_model=List[StaffOut])
def admin_replace_staff(
    company_id: int,
    payload: StaffBulkIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, payload, db, current_user)
    _block_master_write()


@router.post("/{company_id}/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def admin_create_staff(
    company_id: int,
    payload: StaffIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, payload, db, current_user)
    _block_master_write()


@router.put("/{company_id}/staff/{staff_id}", response_model=StaffOut)
def admin_update_staff(
    company_id: int,
    staff_id: int,
    payload: StaffIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, staff_id, payload, db, current_user)
    _block_master_write()


@router.delete("/{company_id}/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_staff(
    company_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    _ = (company_id, staff_id, db, current_user)
    _block_master_write()
