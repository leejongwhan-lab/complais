"""기업 포털 — 기업정보 CRUD, 추가사업장/부서/담당자, 인증현황."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.security import CurrentUser, get_current_user
from app.models.auth import Users
from app.models.backoffice import CompanyStaff
from app.models.cb import CertificationBodies
from app.models.certification import Certificates, CertificationApplications
from app.models.client import AuditRequest
from app.models.enterprise_audit_application import EnterpriseAuditApplication
from app.models.company import Companies, CompanyDepartments, CompanyHeadcountYearly, CompanySites
from app.services import company_org as org

router = APIRouter(prefix="/user", tags=["User Enterprise Portal"])

# master DB 단일 소스 — shared company_org 서비스 재사용
_HEADCOUNT_FIELDS = org.HEADCOUNT_FIELDS
_normalize_biz_no = org.normalize_biz_no
_upsert_headcount_yearly = org.upsert_headcount_yearly

PROCESS_STEPS = [
    {"step": 1, "key": "proposal", "label": "제안서 송부"},
    {"step": 2, "key": "review", "label": "검토중"},
    {"step": 3, "key": "coordinate", "label": "조율중"},
    {"step": 4, "key": "contract", "label": "계약서"},
    {"step": 5, "key": "audit", "label": "심사중"},
    {"step": 6, "key": "ncr", "label": "시정조치중"},
    {"step": 7, "key": "closed", "label": "심사종료"},
]

_STATUS_TO_STEP = {
    "submitted": 1,
    "proposal": 1,
    "proposal_sent": 1,
    "under_review": 2,
    "reviewing": 2,
    "reviewed": 2,
    "coordinating": 3,
    "negotiating": 3,
    "contract": 4,
    "contracted": 4,
    "signed": 4,
    "auditing": 5,
    "in_audit": 5,
    "audit": 5,
    "corrective": 6,
    "ncr": 6,
    "corrective_action": 6,
    "completed": 7,
    "closed": 7,
    "approved": 7,
    "finished": 7,
}


# ─── Company profile update ───────────────────────────────────────

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
    # 인원현황 연도 스냅샷 — 미지정 시 당해 연도
    headcount_year: Optional[int] = Field(default=None, ge=2000, le=2100)



@router.put("/company")
def update_my_company_profile(
    payload: CompanyProfileUpdate,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업정보 저장 — companies 갱신 + 인원현황 연도 스냅샷 (master DB / shared org service)."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    company = org.get_company_or_404(db, cid)
    return org.update_company_profile(db, company, payload.model_dump(exclude_unset=True))


# ─── Sites ────────────────────────────────────────────────────────

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


def _site_out(row: CompanySites) -> SiteOut:
    return SiteOut.model_validate(org.site_to_dict(row))


@router.get("/company/sites", response_model=List[SiteOut])
def list_sites(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    rows = (
        db.query(CompanySites)
        .filter(CompanySites.company_id == cid)
        .filter((CompanySites.is_main.is_(False)) | (CompanySites.is_main.is_(None)))
        .order_by(CompanySites.id.asc())
        .all()
    )
    return [_site_out(r) for r in rows]


@router.post("/company/sites", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(
    payload: SiteIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    now = datetime.now()
    row = CompanySites(
        company_id=cid,
        site_name=payload.site_name.strip(),
        address=payload.address,
        detail_address=payload.detail_address,
        address_en=payload.address_en,
        biz_no=payload.biz_no,
        employee_count=payload.employee_count or 0,
        is_main=False,
        work_type=payload.work_type,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _site_out(row)


@router.put("/company/sites/{site_id}", response_model=SiteOut)
def update_site(
    site_id: int,
    payload: SiteIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = db.query(CompanySites).filter(CompanySites.id == site_id, CompanySites.company_id == cid).first()
    if not row:
        raise HTTPException(status_code=404, detail="사업장을 찾을 수 없습니다.")
    for k, v in payload.model_dump().items():
        if k == "is_main":
            continue
        setattr(row, k, v)
    row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    return _site_out(row)


@router.delete("/company/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(
    site_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = db.query(CompanySites).filter(CompanySites.id == site_id, CompanySites.company_id == cid).first()
    if not row:
        raise HTTPException(status_code=404, detail="사업장을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


# ─── Departments ──────────────────────────────────────────────────

class DeptIn(BaseModel):
    name: str
    sort_order: int = 0


class DeptOut(BaseModel):
    id: int
    company_id: int
    name: str
    sort_order: int = 0
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class DeptBulkIn(BaseModel):
    names: List[str] = Field(default_factory=list)


@router.get("/company/departments", response_model=List[DeptOut])
def list_departments(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    rows = (
        db.query(CompanyDepartments)
        .filter(CompanyDepartments.company_id == cid, CompanyDepartments.is_active.is_(True))
        .order_by(CompanyDepartments.sort_order.asc(), CompanyDepartments.id.asc())
        .all()
    )
    return rows


@router.post("/company/departments", response_model=DeptOut, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DeptIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="부서명을 입력하세요.")
    exists = (
        db.query(CompanyDepartments)
        .filter(CompanyDepartments.company_id == cid, CompanyDepartments.name == name)
        .first()
    )
    if exists:
        if not exists.is_active:
            exists.is_active = True
            exists.updated_at = datetime.now()
            db.commit()
            db.refresh(exists)
            return exists
        raise HTTPException(status_code=400, detail="이미 등록된 부서명입니다.")
    now = datetime.now()
    row = CompanyDepartments(
        company_id=cid,
        name=name,
        sort_order=payload.sort_order or 0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/company/departments/bulk", response_model=List[DeptOut])
def replace_departments(
    payload: DeptBulkIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """부서 목록 일괄 저장 — 전달된 이름 집합으로 동기화."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    wanted = []
    seen = set()
    for n in payload.names:
        name = (n or "").strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        wanted.append(name)

    existing = db.query(CompanyDepartments).filter(CompanyDepartments.company_id == cid).all()
    by_name = {r.name.casefold(): r for r in existing}
    now = datetime.now()
    keep = set()
    for i, name in enumerate(wanted):
        key = name.casefold()
        keep.add(key)
        if key in by_name:
            row = by_name[key]
            row.name = name
            row.is_active = True
            row.sort_order = i
            row.updated_at = now
        else:
            db.add(
                CompanyDepartments(
                    company_id=cid,
                    name=name,
                    sort_order=i,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
    for row in existing:
        if row.name.casefold() not in keep:
            row.is_active = False
            row.updated_at = now
    db.commit()
    return (
        db.query(CompanyDepartments)
        .filter(CompanyDepartments.company_id == cid, CompanyDepartments.is_active.is_(True))
        .order_by(CompanyDepartments.sort_order.asc(), CompanyDepartments.id.asc())
        .all()
    )


# ─── Staff / contacts ─────────────────────────────────────────────

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


def _staff_out(row: CompanyStaff) -> StaffOut:
    return StaffOut.model_validate(org.staff_to_dict(row))


@router.delete("/company/departments/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    dept_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = (
        db.query(CompanyDepartments)
        .filter(CompanyDepartments.id == dept_id, CompanyDepartments.company_id == cid)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다.")
    row.is_active = False
    row.updated_at = datetime.now()
    db.commit()


@router.get("/company/staff", response_model=List[StaffOut])
def list_staff(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    rows = db.query(CompanyStaff).filter(CompanyStaff.company_id == cid).order_by(CompanyStaff.id.asc()).all()
    return [_staff_out(r) for r in rows]


@router.post("/company/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    name = (payload.staff_name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="성명을 입력하세요.")
    row = CompanyStaff(
        company_id=cid,
        staff_name=name,
        role=payload.role,
        department=payload.department,
        position=payload.position,
        phone=payload.phone,
        mobile=payload.mobile,
        email=payload.email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _staff_out(row)


@router.put("/company/staff/bulk", response_model=List[StaffOut])
def replace_staff(
    payload: StaffBulkIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """담당자 테이블 일괄 저장(전체 교체)."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    db.query(CompanyStaff).filter(CompanyStaff.company_id == cid).delete()
    out_rows = []
    for item in payload.items:
        name = (item.staff_name or "").strip()
        if not name:
            continue
        row = CompanyStaff(
            company_id=cid,
            staff_name=name,
            role=item.role,
            department=item.department,
            position=item.position,
            phone=item.phone,
            mobile=item.mobile,
            email=item.email,
        )
        db.add(row)
        out_rows.append(row)
    db.commit()
    for r in out_rows:
        db.refresh(r)
    return [_staff_out(r) for r in out_rows]



@router.put("/company/staff/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: int,
    payload: StaffIn,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = db.query(CompanyStaff).filter(CompanyStaff.id == staff_id, CompanyStaff.company_id == cid).first()
    if not row:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다.")
    for k, v in payload.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _staff_out(row)


@router.delete("/company/staff/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_staff(
    staff_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = db.query(CompanyStaff).filter(CompanyStaff.id == staff_id, CompanyStaff.company_id == cid).first()
    if not row:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


# ─── Portal users (직원관리 — users 테이블) ─────────────────────────

class PortalUserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    phone: Optional[str] = None
    membership_status: Optional[str] = None
    is_active: bool = True


@router.get("/company/users", response_model=List[PortalUserOut])
def list_company_users(
    q: Optional[str] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    query = db.query(Users).filter(Users.company_id == cid)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((Users.name.ilike(like)) | (Users.email.ilike(like)))
    rows = query.order_by(Users.id.asc()).limit(200).all()
    return [
        PortalUserOut(
            id=r.id,
            name=r.name,
            email=r.email,
            role=r.role,
            phone=r.phone,
            membership_status=getattr(r, "membership_status", None),
            is_active=bool(r.is_active),
        )
        for r in rows
    ]


# ─── Cert status ──────────────────────────────────────────────────

class HeldCertOut(BaseModel):
    id: int
    cert_no: Optional[str] = None
    standards: str
    scope_kr: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    status: str
    issued_at: Optional[str] = None


class CertAppOut(BaseModel):
    id: int
    source: str  # certification_applications | audit_requests | enterprise_audit_applications
    application_no: Optional[str] = None
    cb_id: Optional[int] = None
    cb_name: Optional[str] = None
    company_name: Optional[str] = None
    audit_type: Optional[str] = None
    standards: List[str] = Field(default_factory=list)
    status: str
    status_label: str
    process_step: int
    preferred_start_date: Optional[str] = None
    submitted_at: Optional[str] = None
    steps: List[dict] = Field(default_factory=list)
    documents_hint: str = "생성된 문서가 없습니다. 제안서 송부 후 이 구역에서 문서들을 확인할 수 있습니다."


class CertStatusResponse(BaseModel):
    company_id: int
    company_name: str
    held_certificates: List[HeldCertOut] = Field(default_factory=list)
    applications: List[CertAppOut] = Field(default_factory=list)
    process_steps: List[dict] = Field(default_factory=lambda: PROCESS_STEPS)


def _parse_json_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None and str(x).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                data = json.loads(text)
                return _parse_json_list(data)
            except Exception:  # noqa: BLE001
                pass
        return [p.strip() for p in re.split(r"[,;/|]+", text) if p.strip()]
    return [str(raw)]


def _step_from_status(status_val: Optional[str], explicit: Optional[int] = None) -> int:
    if explicit and 1 <= int(explicit) <= 7:
        return int(explicit)
    key = (status_val or "").strip().lower()
    return _STATUS_TO_STEP.get(key, 1)


def _status_label(status_val: Optional[str], step: int) -> str:
    for item in PROCESS_STEPS:
        if item["step"] == step:
            return item["label"]
    return status_val or "-"


def _audit_type_label(raw: Optional[str]) -> str:
    mapping = {
        "initial": "최초심사",
        "surveillance": "사후심사",
        "recertification": "갱신심사",
        "special": "특별심사",
        "transfer": "전환심사",
        "전환": "전환심사",
    }
    if not raw:
        return "심사"
    return mapping.get(str(raw).strip().lower(), str(raw))


@router.get("/cert-status", response_model=CertStatusResponse)
def get_cert_status(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """보유 인증 + 인증 신청 관리(7단계 스테퍼)."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    held_rows = (
        db.query(Certificates)
        .filter(Certificates.company_id == cid)
        .order_by(Certificates.id.desc())
        .limit(50)
        .all()
    )
    held = [
        HeldCertOut(
            id=r.id,
            cert_no=r.cert_no,
            standards=r.standards,
            scope_kr=r.scope_kr,
            valid_from=r.valid_from.isoformat() if r.valid_from else None,
            valid_until=r.valid_until.isoformat() if r.valid_until else None,
            status=r.status,
            issued_at=r.issued_at.isoformat() if r.issued_at else None,
        )
        for r in held_rows
    ]

    apps: List[CertAppOut] = []
    cb_cache: Dict[int, str] = {}

    def cb_name(cb_id: Optional[int]) -> Optional[str]:
        if not cb_id:
            return None
        if cb_id in cb_cache:
            return cb_cache[cb_id]
        cb = db.get(CertificationBodies, cb_id)
        name = getattr(cb, "cb_name", None) or getattr(cb, "name", None) if cb else None
        cb_cache[cb_id] = name or f"CB #{cb_id}"
        return cb_cache[cb_id]

    cert_apps = (
        db.query(CertificationApplications)
        .filter(CertificationApplications.company_id == cid)
        .order_by(CertificationApplications.id.desc())
        .limit(50)
        .all()
    )
    for row in cert_apps:
        step = _step_from_status(row.status)
        standards = _parse_json_list(row.standards_json)
        apps.append(
            CertAppOut(
                id=row.id,
                source="certification_applications",
                application_no=row.application_no,
                cb_id=row.cb_id,
                cb_name=cb_name(row.cb_id),
                company_name=company.name,
                audit_type=_audit_type_label(row.application_type),
                standards=standards,
                status=row.status,
                status_label=_status_label(row.status, step),
                process_step=step,
                preferred_start_date=row.desired_audit_start.isoformat() if row.desired_audit_start else None,
                submitted_at=row.submitted_at.isoformat() if row.submitted_at else (
                    row.created_at.isoformat() if row.created_at else None
                ),
                steps=PROCESS_STEPS,
            )
        )

    # audit_requests fallback / supplement
    seen_nos = {a.application_no for a in apps if a.application_no}
    reqs = (
        db.query(AuditRequest)
        .filter(AuditRequest.company_id == cid)
        .order_by(AuditRequest.id.desc())
        .limit(50)
        .all()
    )
    for row in reqs:
        app_no = getattr(row, "application_no", None) or f"APP-{row.created_at.strftime('%Y%m%d') if row.created_at else '----'}-{row.id:04d}"
        if app_no in seen_nos:
            continue
        step = _step_from_status(row.status, getattr(row, "process_step", None))
        apps.append(
            CertAppOut(
                id=row.id,
                source="audit_requests",
                application_no=app_no,
                cb_id=row.cb_id,
                cb_name=cb_name(row.cb_id),
                company_name=company.name,
                audit_type=_audit_type_label(row.audit_type),
                standards=_parse_json_list(row.iso_standards),
                status=row.status,
                status_label=_status_label(row.status, step),
                process_step=step,
                preferred_start_date=(
                    row.preferred_start_date.isoformat()
                    if getattr(row, "preferred_start_date", None)
                    else None
                ),
                submitted_at=row.submitted_at.isoformat() if row.submitted_at else (
                    row.created_at.isoformat() if row.created_at else None
                ),
                steps=PROCESS_STEPS,
            )
        )


    # enterprise_audit_applications (MD snapshot history)
    _STATUS_STEP = {"SUBMITTED": 1, "REVIEWING": 2, "PROPOSED": 3, "CONTRACTED": 4}
    eaa_rows = (
        db.query(EnterpriseAuditApplication)
        .filter(EnterpriseAuditApplication.enterprise_id == cid)
        .order_by(EnterpriseAuditApplication.application_id.desc())
        .limit(50)
        .all()
    )
    for row in eaa_rows:
        step = _STATUS_STEP.get(row.status, 1)
        stds = row.applied_standards if isinstance(row.applied_standards, list) else _parse_json_list(row.applied_standards)
        apps.append(
            CertAppOut(
                id=row.application_id,
                source="enterprise_audit_applications",
                application_no=f"MD-{row.application_id:05d}",
                cb_id=row.cb_id,
                cb_name=cb_name(row.cb_id),
                company_name=company.name,
                audit_type=_audit_type_label(row.audit_type),
                standards=[str(s) for s in stds],
                status=row.status,
                status_label={"SUBMITTED": "제출", "REVIEWING": "검토중", "PROPOSED": "제안", "CONTRACTED": "계약"}.get(row.status, row.status),
                process_step=step,
                preferred_start_date=None,
                submitted_at=row.created_at.isoformat() if row.created_at else None,
                steps=PROCESS_STEPS,
            )
        )

    return CertStatusResponse(
        company_id=cid,
        company_name=company.name,
        held_certificates=held,
        applications=apps,
        process_steps=PROCESS_STEPS,
    )
