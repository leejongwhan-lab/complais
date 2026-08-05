"""기업 맞춤형 인증기관(CB) 목록 — IAF × ISO 표준 Scope 동적 필터."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.security import CurrentUser, get_current_user
from app.core.validators import format_biz_no
from app.data.accreditation_bodies_seed import ENTERPRISE_ISO_STANDARDS
from app.models.cb import CertificationBodies, CbAccreditationScopes
from app.models.certification import Certificates
from app.models.certification_body import CbAccreditationScope
from app.models.client import AuditRequest
from app.models.company import Companies, CompanyHeadcountYearly
from app.models.standard import StandardMaster

router = APIRouter(prefix="/user", tags=["User Enterprise"])

# 사이드바 "보유 표준" — 핵심 QMS/EMS/OH&S
_HELD_STD_NUMS = frozenset({"9001", "14001", "45001"})
_ISO_STD_NUM_RE = re.compile(
    r"(9001|14001|45001|27001|27701|50001|37001|37301|22301|22000|13485|42001|19443)",
    re.IGNORECASE,
)


class AvailableCbItem(BaseModel):
    id: int
    cb_code: str
    cb_name: str
    cb_name_en: Optional[str] = None
    accreditation_body: Optional[str] = None
    reg_no: Optional[str] = None
    matched_standards: List[str] = Field(default_factory=list)
    matched_iaf_codes: List[str] = Field(default_factory=list)


class AvailableCbsResponse(BaseModel):
    company_id: int
    company_name: str
    company_iaf_codes: List[str]
    requested_standards: List[str]
    total: int
    data: List[AvailableCbItem]


class IsoStandardOption(BaseModel):
    standard_code: str
    standard_name: str


class CompanyProfileOut(BaseModel):
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
    iaf_codes: List[str] = Field(default_factory=list)
    scope_kr: Optional[str] = None
    scope_en: Optional[str] = None
    employee_count: Optional[int] = None
    headcount_outsourced: Optional[int] = None
    headcount_regular: Optional[int] = None
    headcount_non_regular: Optional[int] = None
    mapped_iaf: List[dict] = Field(default_factory=list)
    available_standards: List[IsoStandardOption] = Field(default_factory=list)
    # 사이드바 프로필 배지 — 인정기관/등록번호는 CB 전용, 여기 포함하지 않음
    held_standards: List[str] = Field(default_factory=list)
    other_certifications: List[str] = Field(default_factory=list)
    updated_at: Optional[str] = None
    # 인원현황 연도 스냅샷 (매년 심사 시 갱신)
    headcount_year: Optional[int] = None
    headcount_years: List[int] = Field(default_factory=list)
    # deprecated: 외부 API 불러오기 UX 제거 — 빈 객체 유지(하위 호환)
    field_sources: dict = Field(default_factory=dict)


def _iter_token_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        out: List[str] = []
        for item in raw:
            if isinstance(item, dict):
                for key in ("standard_code", "code", "name", "label", "cert_name"):
                    if item.get(key):
                        out.append(str(item[key]))
                        break
            elif item is not None and str(item).strip():
                out.append(str(item).strip())
        return out
    if isinstance(raw, dict):
        return _iter_token_list(list(raw.values()))
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("[") or text.startswith("{"):
            try:
                return _iter_token_list(json.loads(text))
            except Exception:  # noqa: BLE001
                pass
        return [p.strip() for p in re.split(r"[,;/|]+", text) if p.strip()]
    return [str(raw).strip()] if str(raw).strip() else []


def _classify_cert_token(token: str) -> Optional[Tuple[str, str]]:
    """(bucket, label) — bucket is 'held' | 'other'."""
    t = (token or "").strip()
    if not t:
        return None
    normalized = t.upper().replace("ＩＳＯ", "ISO")
    m = _ISO_STD_NUM_RE.search(normalized)
    if m:
        num = m.group(1)
        label = f"ISO {num}"
        return ("held" if num in _HELD_STD_NUMS else "other", label)
    # Main-Biz / ESG / 기타 인증명은 기타 배지
    return ("other", t)


def _collect_company_cert_badges(db: Session, company: Companies) -> Tuple[List[str], List[str]]:
    held: List[str] = []
    other: List[str] = []
    seen: Set[str] = set()

    def add(token: str) -> None:
        classified = _classify_cert_token(token)
        if not classified:
            return
        bucket, label = classified
        key = label.casefold()
        if key in seen:
            return
        seen.add(key)
        if bucket == "held":
            held.append(label)
        else:
            other.append(label)

    # 1) 유효 인증서
    cert_rows = (
        db.query(Certificates)
        .filter(Certificates.company_id == company.id)
        .filter(Certificates.status.in_(("active", "valid", "issued", "ACTIVE", "VALID")))
        .all()
    )
    for row in cert_rows:
        for tok in _iter_token_list(row.standards):
            add(tok)

    # 2) 설문 스냅샷
    snap = company.latest_survey_snapshot or {}
    if isinstance(snap, dict):
        for key in ("iso_standards", "held_standards", "standards"):
            for tok in _iter_token_list(snap.get(key)):
                add(tok)
        for key in ("other_certs", "other_certifications", "extra_certs", "certifications"):
            for tok in _iter_token_list(snap.get(key)):
                add(tok)

    # 3) 최근 심사신청 ISO
    reqs = (
        db.query(AuditRequest)
        .filter(AuditRequest.company_id == company.id)
        .order_by(AuditRequest.id.desc())
        .limit(5)
        .all()
    )
    for req in reqs:
        for tok in _iter_token_list(req.iso_standards):
            add(tok)

    return held, other


def _list_available_standards(db: Session) -> List[IsoStandardOption]:
    rows = (
        db.query(StandardMaster)
        .filter(StandardMaster.is_active.is_(True))
        .order_by(StandardMaster.id.asc())
        .all()
    )
    if rows:
        return [
            IsoStandardOption(standard_code=r.standard_code, standard_name=r.standard_name)
            for r in rows
        ]
    return [
        IsoStandardOption(standard_code=code, standard_name=name)
        for code, name in ENTERPRISE_ISO_STANDARDS
    ]


@router.get("/company", response_model=CompanyProfileOut)
def get_my_company_profile(
    company_id: Optional[int] = Query(None, description="platform_admin 전용"),
    headcount_year: Optional[int] = Query(None, ge=2000, le=2100, description="인원현황 조회 연도"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """개요/기업정보 — DB 저장된 기업 마스터(수정·저장 모드)."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    mapped: List[dict] = []
    try:
        from app.services.iaf_recommendation import resolve_iaf_for_company

        mapped_items = resolve_iaf_for_company(db, company) or []
        for item in mapped_items:
            if hasattr(item, "model_dump"):
                mapped.append(item.model_dump())
            elif isinstance(item, dict):
                mapped.append(item)
            else:
                mapped.append(
                    {
                        "iaf_code": getattr(item, "iaf_code", None),
                        "industry_name_ko": getattr(item, "industry_name_ko", None),
                        "source": getattr(item, "source", None),
                    }
                )
    except Exception:  # noqa: BLE001
        mapped = []

    held, other = _collect_company_cert_badges(db, company)
    biz_display = format_biz_no(company.biz_no) or company.biz_no

    year_rows = (
        db.query(CompanyHeadcountYearly.year)
        .filter(CompanyHeadcountYearly.company_id == cid)
        .order_by(CompanyHeadcountYearly.year.desc())
        .all()
    )
    years = [int(r[0]) for r in year_rows]
    current_year = datetime.now().year
    if current_year not in years:
        years = [current_year] + years
    selected_year = int(headcount_year or current_year)

    emp = company.employee_count
    hc_out = company.headcount_outsourced
    hc_reg = company.headcount_regular
    hc_non = company.headcount_non_regular
    snap = (
        db.query(CompanyHeadcountYearly)
        .filter(
            CompanyHeadcountYearly.company_id == cid,
            CompanyHeadcountYearly.year == selected_year,
        )
        .first()
    )
    if snap:
        emp = snap.employee_count if snap.employee_count is not None else emp
        hc_out = snap.headcount_outsourced if snap.headcount_outsourced is not None else hc_out
        hc_reg = snap.headcount_regular if snap.headcount_regular is not None else hc_reg
        hc_non = snap.headcount_non_regular if snap.headcount_non_regular is not None else hc_non

    return CompanyProfileOut(
        id=company.id,
        cert_no=company.cert_no,
        name=company.name,
        name_en=company.name_en,
        biz_no=biz_display,
        corp_no=company.corp_no,
        entity_type=company.entity_type,
        ceo_name=company.ceo_name,
        biz_type=company.biz_type,
        biz_class=company.biz_class,
        address=company.address,
        detail_address=company.detail_address,
        address_en=company.address_en,
        tel=company.tel,
        email=company.email,
        website=company.website,
        ksic_code=company.ksic_code,
        iaf_code=company.iaf_code,
        iaf_codes=_parse_codes(company.iaf_code),
        scope_kr=company.scope_kr,
        scope_en=company.scope_en,
        employee_count=emp,
        headcount_outsourced=hc_out,
        headcount_regular=hc_reg,
        headcount_non_regular=hc_non,
        mapped_iaf=mapped,
        available_standards=_list_available_standards(db),
        held_standards=held,
        other_certifications=other,
        updated_at=company.updated_at.isoformat(sep=" ", timespec="minutes") if company.updated_at else None,
        headcount_year=selected_year,
        headcount_years=years,
        field_sources={},
    )


@router.get("/meta/iso-standards", response_model=List[IsoStandardOption])
def meta_enterprise_iso_standards(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    return _list_available_standards(db)


def _normalize_iaf(token: str) -> Optional[str]:
    t = (token or "").strip().upper().replace("IAF", "").strip()
    if not t:
        return None
    m = re.search(r"(\d{1,2})", t)
    if not m:
        return None
    return m.group(1).zfill(2)


def _normalize_standard(token: str) -> Optional[str]:
    t = (token or "").strip().upper().replace("ＩＳＯ", "ISO")
    m = re.search(r"(9001|14001|45001|27001|22000|50001|37001|13485)", t)
    if not m:
        return None
    return f"ISO {m.group(1)}"


def _parse_codes(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,;/|\s]+", str(raw))
    out: List[str] = []
    seen: Set[str] = set()
    for p in parts:
        code = _normalize_iaf(p)
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def _cb_scope_pairs(db: Session, cb_id: int) -> Set[tuple]:
    """(standard_code, iaf_code) 집합 — matrix + legacy 병합."""
    pairs: Set[tuple] = set()
    matrix = (
        db.query(CbAccreditationScope)
        .filter(CbAccreditationScope.cb_id == cb_id, CbAccreditationScope.is_active.is_(True))
        .all()
    )
    for row in matrix:
        std = _normalize_standard(row.standard_code) or (row.standard_code or "").strip()
        iaf = _normalize_iaf(row.iaf_code) or (row.iaf_code or "").strip()
        if std and iaf:
            pairs.add((std, iaf))

    legacy = (
        db.query(CbAccreditationScopes)
        .filter(CbAccreditationScopes.cb_id == cb_id, CbAccreditationScopes.is_active.is_(True))
        .all()
    )
    for row in legacy:
        std = _normalize_standard(row.standard_code) or (row.standard_code or "").strip()
        for iaf in _parse_codes(row.iaf_codes):
            if std:
                pairs.add((std, iaf))
    return pairs


@router.get("/available-cbs", response_model=AvailableCbsResponse)
def list_available_cbs(
    standards: Optional[str] = Query(
        None,
        description="신청 ISO 표준 콤마 구분 (예: ISO 9001,ISO 14001)",
    ),
    iaf_codes: Optional[str] = Query(
        None,
        description="필터용 IAF 코드(미지정 시 기업 마스터 iaf_code 사용)",
    ),
    company_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업의 KSIC/IAF + 신청 표준에 대해 인정범위를 보유한 CB만 반환."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)

    company = db.get(Companies, cid)
    if not company:
        raise HTTPException(status_code=404, detail="기업 정보를 찾을 수 없습니다.")

    company_iafs = _parse_codes(iaf_codes) if iaf_codes else _parse_codes(company.iaf_code)
    requested_standards: List[str] = []
    if standards:
        for part in re.split(r"[,;/|]+", standards):
            std = _normalize_standard(part)
            if std and std not in requested_standards:
                requested_standards.append(std)

    if not requested_standards:
        raise HTTPException(
            status_code=400,
            detail="신청 ISO 표준(standards)을 1개 이상 지정해야 합니다.",
        )

    cbs = (
        db.query(CertificationBodies)
        .filter(CertificationBodies.is_active.is_(True))
        .order_by(CertificationBodies.name.asc())
        .all()
    )

    data: List[AvailableCbItem] = []
    for cb in cbs:
        pairs = _cb_scope_pairs(db, cb.id)
        if not pairs:
            continue

        matched_stds: Set[str] = set()
        matched_iafs: Set[str] = set()
        ok = True
        for std in requested_standards:
            std_pairs = {iaf for s, iaf in pairs if s == std}
            if not std_pairs:
                ok = False
                break
            if company_iafs:
                # 기업 IAF 전부가 해당 표준에서 커버되어야 함
                if not set(company_iafs).issubset(std_pairs):
                    ok = False
                    break
                matched_iafs |= set(company_iafs)
            else:
                matched_iafs |= std_pairs
            matched_stds.add(std)

        if not ok:
            continue

        data.append(
            AvailableCbItem(
                id=cb.id,
                cb_code=cb.code,
                cb_name=cb.name,
                cb_name_en=cb.name_en,
                accreditation_body=cb.accreditation_body or cb.accreditation,
                reg_no=cb.reg_no or cb.accreditation_no,
                matched_standards=sorted(matched_stds),
                matched_iaf_codes=sorted(matched_iafs, key=lambda x: (len(x), x)),
            )
        )

    return AvailableCbsResponse(
        company_id=cid,
        company_name=company.name,
        company_iaf_codes=company_iafs,
        requested_standards=requested_standards,
        total=len(data),
        data=data,
    )
