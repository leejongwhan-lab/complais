"""플랫폼 관리자 — 기업 마스터 목록/상세/조직 CRUD (master DB)."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_admin_user
from app.models.company import Companies
from app.services import company_org as org

router = APIRouter(prefix="/admin/companies", tags=["Admin Companies"])


# ─── List schemas ─────────────────────────────────────────────────

class CompanySummaryResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


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


class CompanyProfileUpdate(BaseModel):
    name: Optional[str] = None
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

    return CompanyListResponse(
        total=total_count,
        page=page,
        limit=limit,
        data=[CompanySummaryResponse.model_validate(c) for c in companies],
    )


# ─── Detail ───────────────────────────────────────────────────────

@router.get("/{company_id}", response_model=CompanyDetailResponse)
def get_company_detail(
    company_id: int,
    headcount_year: Optional[int] = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
) -> CompanyDetailResponse:
    """마스터 DB 기업 상세 — 기본정보 + 인원(연도) + 사업장/부서/담당자."""
    detail = org.build_company_org_detail(db, company_id, headcount_year)
    return CompanyDetailResponse.model_validate(detail)


@router.put("/{company_id}")
def update_company_detail(
    company_id: int,
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    """기업 마스터 필드 + company_headcount_yearly 갱신 (enterprise PUT /user/company 와 동일 로직)."""
    company = org.get_company_or_404(db, company_id)
    return org.update_company_profile(db, company, payload.model_dump(exclude_unset=True))


# ─── Sites ────────────────────────────────────────────────────────

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
    org.get_company_or_404(db, company_id)
    row = org.create_site(db, company_id, payload.model_dump())
    return SiteOut.model_validate(org.site_to_dict(row))


@router.put("/{company_id}/sites/{site_id}", response_model=SiteOut)
def admin_update_site(
    company_id: int,
    site_id: int,
    payload: SiteIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    row = org.update_site(db, company_id, site_id, payload.model_dump())
    return SiteOut.model_validate(org.site_to_dict(row))


@router.delete("/{company_id}/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_site(
    company_id: int,
    site_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    org.delete_site(db, company_id, site_id)


# ─── Departments ──────────────────────────────────────────────────

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
    org.get_company_or_404(db, company_id)
    rows = org.replace_departments(db, company_id, payload.names)
    return [DeptOut.model_validate(org.dept_to_dict(r)) for r in rows]


@router.delete("/{company_id}/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_department(
    company_id: int,
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    org.delete_department(db, company_id, dept_id)


# ─── Staff ────────────────────────────────────────────────────────

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
    org.get_company_or_404(db, company_id)
    rows = org.replace_staff(db, company_id, [i.model_dump() for i in payload.items])
    return [StaffOut.model_validate(org.staff_to_dict(r)) for r in rows]


@router.post("/{company_id}/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def admin_create_staff(
    company_id: int,
    payload: StaffIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    row = org.create_staff(db, company_id, payload.model_dump())
    return StaffOut.model_validate(org.staff_to_dict(row))


@router.put("/{company_id}/staff/{staff_id}", response_model=StaffOut)
def admin_update_staff(
    company_id: int,
    staff_id: int,
    payload: StaffIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    row = org.update_staff(db, company_id, staff_id, payload.model_dump())
    return StaffOut.model_validate(org.staff_to_dict(row))


@router.delete("/{company_id}/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_staff(
    company_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_admin_user),
):
    org.get_company_or_404(db, company_id)
    org.delete_staff(db, company_id, staff_id)
