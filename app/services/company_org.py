"""기업 조직 마스터 CRUD — companies / sites / departments / staff / headcount_yearly.

Enterprise 포털과 Platform Admin이 동일 테이블·동일 로직으로 읽고 쓴다.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.orm import Session

from app.core.validators import format_biz_no
from app.models.backoffice import CompanyStaff
from app.models.company import Companies, CompanyDepartments, CompanyHeadcountYearly, CompanySites

logger = logging.getLogger(__name__)

HEADCOUNT_FIELDS = (
    "employee_count",
    "headcount_outsourced",
    "headcount_regular",
    "headcount_non_regular",
)

COMPANY_PROFILE_FIELDS = (
    "name",
    "name_en",
    "biz_no",
    "corp_no",
    "entity_type",
    "ceo_name",
    "biz_type",
    "biz_class",
    "scope_kr",
    "scope_en",
    "address",
    "detail_address",
    "address_en",
    "zip_code",
    "tel",
    "email",
    "website",
    "ksic_code",
    "iaf_code",
)


def normalize_biz_no(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if len(digits) != 10:
        raise HTTPException(
            status_code=422,
            detail="사업자등록번호는 10자리여야 합니다. (형식: 000-00-00000)",
        )
    return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"


def upsert_headcount_yearly(
    db: Session,
    company: Companies,
    year: int,
    values: Dict[str, Any],
) -> None:
    """companies 최신 캐시 + company_headcount_yearly 연도 스냅샷 동시 반영."""
    now = datetime.now()
    row = (
        db.query(CompanyHeadcountYearly)
        .filter(CompanyHeadcountYearly.company_id == company.id, CompanyHeadcountYearly.year == year)
        .first()
    )
    if not row:
        row = CompanyHeadcountYearly(
            company_id=company.id,
            year=year,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    for field in HEADCOUNT_FIELDS:
        if field not in values:
            continue
        val = values[field]
        setattr(row, field, val)
        if year == now.year:
            if field == "employee_count":
                setattr(company, field, 0 if val is None else int(val))
            else:
                setattr(company, field, val)
    row.updated_at = now


def get_company_or_404(db: Session, company_id: int) -> Companies:
    company = db.get(Companies, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")
    return company


def company_to_spec_dict(
    company: Companies,
    *,
    headcount: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """마스터 기업 필드 + 포털 공통 별칭.

    Admin / CB / Enterprise 가 동일 키로 읽고 채우도록 한다.
    DB 컬럼명(name, address, …)과 API 표준 용어(company_id, company_name,
    address_kr, cert_scope_kr, …)를 함께 제공한다.
    """
    biz_display = format_biz_no(company.biz_no) or company.biz_no
    out: Dict[str, Any] = {
        "id": company.id,
        "company_id": company.id,
        "cert_no": company.cert_no,
        "name": company.name,
        "company_name": company.name,
        "name_en": company.name_en,
        "company_name_en": company.name_en,
        "biz_no": biz_display,
        "corp_no": company.corp_no,
        "entity_type": company.entity_type,
        "ceo_name": company.ceo_name,
        "biz_type": company.biz_type,
        "biz_class": company.biz_class,
        "biz_item": company.biz_class,
        "address": company.address,
        "address_kr": company.address,
        "detail_address": company.detail_address,
        "address_en": company.address_en,
        "zip_code": getattr(company, "zip_code", None),
        "tel": company.tel,
        "email": company.email,
        "website": company.website,
        "ksic_code": company.ksic_code,
        "ksic": company.ksic_code,
        "iaf_code": company.iaf_code,
        "iaf": company.iaf_code,
        "scope_kr": company.scope_kr,
        "scope_en": company.scope_en,
        "cert_scope_kr": company.scope_kr,
        "cert_scope_en": company.scope_en,
        "status": company.status,
        "updated_at": (
            company.updated_at.isoformat(sep=" ", timespec="minutes")
            if company.updated_at
            else None
        ),
    }
    if headcount:
        out.update(headcount)
    return out


def resolve_headcount_snapshot(
    db: Session,
    company: Companies,
    headcount_year: Optional[int] = None,
) -> Dict[str, Any]:
    """연도별 인원 스냅샷. 테이블 미존재/스키마 드리프트 시 companies 캐시로 soft-fail."""
    current_year = datetime.now().year
    selected_year = int(headcount_year or current_year)
    emp = company.employee_count
    hc_out = company.headcount_outsourced
    hc_reg = company.headcount_regular
    hc_non = company.headcount_non_regular
    years = [current_year]

    try:
        year_rows = (
            db.query(CompanyHeadcountYearly.year)
            .filter(CompanyHeadcountYearly.company_id == company.id)
            .order_by(CompanyHeadcountYearly.year.desc())
            .all()
        )
        years = [int(r[0]) for r in year_rows]
        if current_year not in years:
            years = [current_year] + years

        snap = (
            db.query(CompanyHeadcountYearly)
            .filter(
                CompanyHeadcountYearly.company_id == company.id,
                CompanyHeadcountYearly.year == selected_year,
            )
            .first()
        )
        if snap:
            emp = snap.employee_count if snap.employee_count is not None else emp
            hc_out = snap.headcount_outsourced if snap.headcount_outsourced is not None else hc_out
            hc_reg = snap.headcount_regular if snap.headcount_regular is not None else hc_reg
            hc_non = snap.headcount_non_regular if snap.headcount_non_regular is not None else hc_non
    except (ProgrammingError, OperationalError):
        logger.warning(
            "company_headcount_yearly unavailable; falling back to companies cache (company_id=%s)",
            company.id,
            exc_info=True,
        )
        try:
            db.rollback()
        except Exception:
            pass
        years = [current_year]

    return {
        "headcount_year": selected_year,
        "headcount_years": years,
        "employee_count": emp,
        "headcount_outsourced": hc_out,
        "headcount_regular": hc_reg,
        "headcount_non_regular": hc_non,
    }


def site_to_dict(row: CompanySites) -> Dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "site_name": row.site_name,
        "address": row.address,
        "detail_address": getattr(row, "detail_address", None),
        "address_en": getattr(row, "address_en", None),
        "zip_code": getattr(row, "zip_code", None),
        "biz_no": row.biz_no,
        "employee_count": row.employee_count or 0,
        "is_main": bool(row.is_main),
        "work_type": row.work_type,
    }


def staff_to_dict(row: CompanyStaff) -> Dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "staff_name": row.staff_name,
        "role": getattr(row, "role", None),
        "department": row.department,
        "position": row.position,
        "phone": getattr(row, "phone", None),
        "mobile": row.mobile,
        "email": row.email,
    }


def dept_to_dict(row: CompanyDepartments) -> Dict[str, Any]:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "name": row.name,
        "sort_order": row.sort_order or 0,
        "is_active": bool(row.is_active),
    }


def list_additional_sites(db: Session, company_id: int) -> List[CompanySites]:
    try:
        return (
            db.query(CompanySites)
            .filter(CompanySites.company_id == company_id)
            .filter((CompanySites.is_main.is_(False)) | (CompanySites.is_main.is_(None)))
            .order_by(CompanySites.id.asc())
            .all()
        )
    except (ProgrammingError, OperationalError):
        logger.warning("company_sites list failed for company_id=%s", company_id, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return []


def list_active_departments(db: Session, company_id: int) -> List[CompanyDepartments]:
    try:
        return (
            db.query(CompanyDepartments)
            .filter(CompanyDepartments.company_id == company_id, CompanyDepartments.is_active.is_(True))
            .order_by(CompanyDepartments.sort_order.asc(), CompanyDepartments.id.asc())
            .all()
        )
    except (ProgrammingError, OperationalError):
        logger.warning("company_departments list failed for company_id=%s", company_id, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return []


def list_staff_members(db: Session, company_id: int) -> List[CompanyStaff]:
    try:
        return (
            db.query(CompanyStaff)
            .filter(CompanyStaff.company_id == company_id)
            .order_by(CompanyStaff.id.asc())
            .all()
        )
    except (ProgrammingError, OperationalError):
        logger.warning("company_staff list failed for company_id=%s", company_id, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return []


def build_company_org_detail(
    db: Session,
    company_id: int,
    headcount_year: Optional[int] = None,
) -> Dict[str, Any]:
    """Admin/CB/Enterprise 공통 — 마스터 기업 상세 + org 연관 데이터."""
    company = get_company_or_404(db, company_id)
    hc = resolve_headcount_snapshot(db, company, headcount_year)
    detail = company_to_spec_dict(company, headcount=hc)
    detail["sites"] = [site_to_dict(r) for r in list_additional_sites(db, company_id)]
    detail["departments"] = [
        dept_to_dict(r) for r in list_active_departments(db, company_id)
    ]
    detail["staff"] = [staff_to_dict(r) for r in list_staff_members(db, company_id)]
    return detail


def update_company_profile(
    db: Session,
    company: Companies,
    data: Dict[str, Any],
    *,
    commit: bool = True,
) -> Dict[str, Any]:
    """기업 마스터 필드 + 연도별 인원 스냅샷 갱신. data는 unset 제외된 dict."""
    payload = dict(data)
    headcount_year = payload.pop("headcount_year", None) or datetime.now().year
    if "biz_no" in payload:
        payload["biz_no"] = normalize_biz_no(payload.get("biz_no"))

    headcount_vals = {k: payload.pop(k) for k in list(payload.keys()) if k in HEADCOUNT_FIELDS}
    for field, value in payload.items():
        if field in COMPANY_PROFILE_FIELDS or field == "status":
            if not hasattr(company, field):
                continue
            setattr(company, field, value)
    if headcount_vals:
        upsert_headcount_yearly(db, company, int(headcount_year), headcount_vals)
    company.updated_at = datetime.now()
    if commit:
        try:
            db.commit()
            db.refresh(company)
        except (ProgrammingError, OperationalError):
            # zip_code 컬럼 미적용 환경에서도 기존 저장이 깨지지 않도록 soft-fail
            logger.warning("company profile commit failed; retry without zip_code", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            if "zip_code" not in data:
                raise
            payload2 = {k: v for k, v in data.items() if k != "zip_code"}
            company = get_company_or_404(db, company.id)
            return update_company_profile(db, company, payload2, commit=commit)
    return {
        "ok": True,
        "id": company.id,
        "headcount_year": int(headcount_year),
        "updated_at": company.updated_at.isoformat() if company.updated_at else None,
    }


def create_site(db: Session, company_id: int, payload: Dict[str, Any]) -> CompanySites:
    now = datetime.now()
    row = CompanySites(
        company_id=company_id,
        site_name=str(payload.get("site_name") or "").strip(),
        address=payload.get("address"),
        detail_address=payload.get("detail_address"),
        address_en=payload.get("address_en"),
        biz_no=payload.get("biz_no"),
        employee_count=payload.get("employee_count") or 0,
        is_main=False,
        work_type=payload.get("work_type"),
        created_at=now,
        updated_at=now,
    )
    if hasattr(row, "zip_code") and "zip_code" in payload:
        row.zip_code = payload.get("zip_code")
    if not row.site_name:
        raise HTTPException(status_code=422, detail="사업장명을 입력하세요.")
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except (ProgrammingError, OperationalError):
        logger.warning("create_site commit failed; retry without zip_code", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        if "zip_code" not in payload:
            raise
        payload2 = {k: v for k, v in payload.items() if k != "zip_code"}
        return create_site(db, company_id, payload2)
    return row


def update_site(db: Session, company_id: int, site_id: int, payload: Dict[str, Any]) -> CompanySites:
    row = (
        db.query(CompanySites)
        .filter(CompanySites.id == site_id, CompanySites.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="사업장을 찾을 수 없습니다.")
    for k, v in payload.items():
        if k == "is_main":
            continue
        if k == "zip_code" and not hasattr(row, "zip_code"):
            continue
        if k == "site_name" and v is not None:
            v = str(v).strip()
        if hasattr(row, k):
            setattr(row, k, v)
    row.updated_at = datetime.now()
    try:
        db.commit()
        db.refresh(row)
    except (ProgrammingError, OperationalError):
        logger.warning("update_site commit failed; retry without zip_code", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        if "zip_code" not in payload:
            raise
        payload2 = {k: v for k, v in payload.items() if k != "zip_code"}
        return update_site(db, company_id, site_id, payload2)
    return row


def delete_site(db: Session, company_id: int, site_id: int) -> None:
    row = (
        db.query(CompanySites)
        .filter(CompanySites.id == site_id, CompanySites.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="사업장을 찾을 수 없습니다.")
    db.delete(row)
    db.commit()


def replace_departments(db: Session, company_id: int, names: Sequence[str]) -> List[CompanyDepartments]:
    wanted: List[str] = []
    seen = set()
    for n in names:
        name = (n or "").strip()
        if not name or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        wanted.append(name)

    existing = db.query(CompanyDepartments).filter(CompanyDepartments.company_id == company_id).all()
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
                    company_id=company_id,
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
    return list_active_departments(db, company_id)


def delete_department(db: Session, company_id: int, dept_id: int) -> None:
    row = (
        db.query(CompanyDepartments)
        .filter(CompanyDepartments.id == dept_id, CompanyDepartments.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="부서를 찾을 수 없습니다.")
    row.is_active = False
    row.updated_at = datetime.now()
    db.commit()


def replace_staff(db: Session, company_id: int, items: Sequence[Dict[str, Any]]) -> List[CompanyStaff]:
    db.query(CompanyStaff).filter(CompanyStaff.company_id == company_id).delete()
    out_rows: List[CompanyStaff] = []
    for item in items:
        name = str(item.get("staff_name") or "").strip()
        if not name:
            continue
        row = CompanyStaff(
            company_id=company_id,
            staff_name=name,
            role=item.get("role"),
            department=item.get("department"),
            position=item.get("position"),
            phone=item.get("phone"),
            mobile=item.get("mobile"),
            email=item.get("email"),
        )
        db.add(row)
        out_rows.append(row)
    db.commit()
    for r in out_rows:
        db.refresh(r)
    return out_rows


def create_staff(db: Session, company_id: int, payload: Dict[str, Any]) -> CompanyStaff:
    name = str(payload.get("staff_name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="성명을 입력하세요.")
    row = CompanyStaff(
        company_id=company_id,
        staff_name=name,
        role=payload.get("role"),
        department=payload.get("department"),
        position=payload.get("position"),
        phone=payload.get("phone"),
        mobile=payload.get("mobile"),
        email=payload.get("email"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_staff(db: Session, company_id: int, staff_id: int, payload: Dict[str, Any]) -> CompanyStaff:
    row = (
        db.query(CompanyStaff)
        .filter(CompanyStaff.id == staff_id, CompanyStaff.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다.")
    for k, v in payload.items():
        if k == "staff_name" and v is not None:
            v = str(v).strip()
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_staff(db: Session, company_id: int, staff_id: int) -> None:
    row = (
        db.query(CompanyStaff)
        .filter(CompanyStaff.id == staff_id, CompanyStaff.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="담당자를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
