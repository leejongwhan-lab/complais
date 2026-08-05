"""플랫폼 관리자 — 인증기관(CB) 통합 관리 API."""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import CurrentUser, get_current_admin_user
from app.core.validators import sanitize_contact_fields
from app.data.accreditation_bodies_seed import (
    ENTERPRISE_ISO_STANDARDS,
    ensure_accreditation_bodies,
)
from app.data.scope_taxonomies import (
    TAXONOMY_LABELS,
    codes_for_taxonomy,
    normalize_scope_code,
    standard_scope_meta,
    taxonomy_for_standard,
    uses_iaf39,
    SCOPE_CODE_SEED,
)

from app.models.admin import CBContract, CBTier
from app.models.auditor import Auditor, AuditorCbMemberships
from app.models.cb import CertificationBodies, CbAccreditationScopes
from app.models.certification_body import (
    CbAccreditationScope,
    CbStandardAccreditation,
    ScopeCodeMaster,
    apply_spec_fields,
    cb_to_spec_dict,
    normalize_cb_status,
)
from app.models.master import AccreditationBodies
from app.models.standard import StandardMaster
from app.services.cb_billing import ensure_default_cb_contract

router = APIRouter(prefix="/admin/certification-bodies", tags=["Admin Certification Bodies"])

DEFAULT_STANDARDS = [code for code, _ in ENTERPRISE_ISO_STANDARDS]
DEFAULT_IAF_CODES = [f"{i:02d}" for i in range(1, 40)]


def ensure_scope_code_masters(db: Session) -> int:
    """스토리보드 시드 → scope_code_masters UPSERT. 반환: 신규 건수."""
    now = datetime.utcnow()
    created = 0
    for taxonomy, code, ko, en, parent, group, sort_order, meta in SCOPE_CODE_SEED:
        row = (
            db.query(ScopeCodeMaster)
            .filter(ScopeCodeMaster.taxonomy == taxonomy, ScopeCodeMaster.code == code)
            .first()
        )
        meta_json = json.dumps(meta, ensure_ascii=False) if meta else None
        if row:
            row.name_ko = ko
            row.name_en = en
            row.parent_code = parent
            row.group_label = group
            row.sort_order = sort_order
            row.meta_json = meta_json
            row.is_active = True
            row.updated_at = now
            continue
        db.add(
            ScopeCodeMaster(
                taxonomy=taxonomy,
                code=code,
                name_ko=ko,
                name_en=en,
                parent_code=parent,
                group_label=group,
                sort_order=sort_order,
                meta_json=meta_json,
                is_active=True,
                created_at=now,
            )
        )
        created += 1
    db.flush()
    return created



# ---------- Schemas ----------

class ScopeItem(BaseModel):
    """1행 = 표준 1 + 수행범위 코드 1.

    scope_code가 정식 필드. iaf_code는 하위호환 별칭(동일 값).
    """

    id: Optional[int] = None
    standard_code: str
    scope_code: Optional[str] = None
    iaf_code: Optional[str] = None  # legacy alias
    is_active: bool = True
    granted_date: Optional[date] = None
    expiry_date: Optional[date] = None

    def resolved_code(self) -> str:
        raw = (self.scope_code or self.iaf_code or "").strip()
        tax = taxonomy_for_standard(self.standard_code)
        return normalize_scope_code(tax, raw)


class StandardAccreditationItem(BaseModel):
    """CB × ISO 표준별 인정기관(AB) + 인정번호 + 인증수행범위.

    수행범위 택소노미는 표준별로 다름 (IAF39 / MDQMS / FSMS / NQMS / BCMS / none).
    """

    standard_code: str
    standard_name: Optional[str] = None
    ab_code: Optional[str] = None
    ab_name_en: Optional[str] = None
    registration_no: Optional[str] = None  # 인정번호
    scope_taxonomy: Optional[str] = None
    scope_taxonomy_label: Optional[str] = None
    has_scope_codes: bool = True
    scope_codes: List[str] = Field(default_factory=list)  # 표준별 인증수행범위
    iaf_codes: List[str] = Field(default_factory=list)  # 하위호환(iaf39만 의미)
    is_active: bool = True


class CbListItem(BaseModel):
    id: int
    cb_code: str
    cb_name: str
    cb_name_en: Optional[str] = None
    accreditation_body: Optional[str] = None
    reg_no: Optional[str] = None
    biz_reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    status: str = "active"
    standard_count: int = 0
    held_standard_count: int = 0
    held_standards: List[str] = Field(default_factory=list)
    ab_summary: str = ""
    scope_count: int = 0
    iaf_summary: str = ""
    standards_summary: str = ""
    billing_tier: Optional[str] = None
    contract_year: Optional[int] = None


class CbListResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[CbListItem]


class ContractPayload(BaseModel):
    contract_year: Optional[int] = None
    tier: Optional[str] = None
    annual_base_fee: Optional[Decimal] = None
    price_per_md: Optional[Decimal] = None
    is_active: Optional[bool] = None


class CbUpsertBody(BaseModel):
    cb_code: str
    cb_name: str
    cb_name_en: Optional[str] = None
    cb_initial: Optional[str] = None
    reg_no: Optional[str] = None
    accreditation_body: str = "KAB"
    biz_reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    status: str = "active"
    scopes: Optional[List[ScopeItem]] = None
    standard_accreditations: Optional[List[StandardAccreditationItem]] = None
    contract: Optional[ContractPayload] = None


class CbDetailResponse(BaseModel):
    id: int
    cb_code: str
    cb_name: str
    cb_name_en: Optional[str] = None
    cb_initial: Optional[str] = None
    reg_no: Optional[str] = None
    accreditation_body: Optional[str] = None
    biz_reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    status: str = "active"
    scopes: List[ScopeItem] = Field(default_factory=list)
    standard_accreditations: List[StandardAccreditationItem] = Field(default_factory=list)
    standard_count: int = 0
    scope_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContractInfo(BaseModel):
    id: Optional[int] = None
    contract_year: int
    tier: str = "MEDIUM"
    annual_base_fee: Decimal = Decimal("0")
    price_per_md: Decimal = Decimal("0")
    contract_start_date: Optional[datetime] = None
    contract_end_date: Optional[datetime] = None
    is_active: bool = True


class AuditorMemberItem(BaseModel):
    membership_id: int
    auditor_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    grade: Optional[str] = None
    approved_grade: Optional[str] = None
    status: str
    employment_type: Optional[str] = None
    iaf_codes: Optional[str] = None
    kar_no: Optional[str] = None
    is_primary: bool = False


class CbFullDetailResponse(CbDetailResponse):
    """기업 DB 스타일 통합 상세 — 기본정보 + Scope + 과금 + 소속 심사원."""

    contract: Optional[ContractInfo] = None
    auditor_count: int = 0
    auditors: List[AuditorMemberItem] = Field(default_factory=list)


class ScopeMatrixUpdate(BaseModel):
    """체크된 (standard_code, iaf_code) 목록으로 활성 Scope를 교체/머지."""

    scopes: List[ScopeItem]
    replace_all: bool = True


class BulkImportResult(BaseModel):
    message: str
    created: int
    updated: int
    scopes_upserted: int
    error_count: int
    errors: List[dict] = Field(default_factory=list)


class ExcelUploadResponse(BaseModel):
    """institutionData.ods / XLSX 백엔드 전용 업로드 응답."""

    success: bool = True
    imported_count: int
    created: int = 0
    updated: int = 0
    scopes_upserted: int = 0
    error_count: int = 0
    errors: List[dict] = Field(default_factory=list)
    message: Optional[str] = None


# ---------- Helpers ----------

def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _new_cb_defaults(now: datetime) -> dict:
    return {
        "cb_type": "certification",
        "is_active": True,
        "fee_per_md": Decimal("0"),
        "fee_travel": Decimal("0"),
        "fee_cert": Decimal("0"),
        "max_consecutive": 3,
        "impartiality_cycle_months": 12,
        "doc_rule_contract": "CB-QE-{YYMMDD}-{SEQ3}",
        "status": "정상",
        "created_at": now,
        "updated_at": now,
    }


def _scope_counts(db: Session, cb_ids: List[int]) -> Dict[int, Tuple[int, int, str, str]]:
    """cb_id -> (standard_count, scope_count, standards_summary, iaf_summary)."""
    if not cb_ids:
        return {}
    rows = (
        db.query(
            CbAccreditationScope.cb_id,
            CbAccreditationScope.standard_code,
            CbAccreditationScope.iaf_code,
        )
        .filter(
            CbAccreditationScope.cb_id.in_(cb_ids),
            CbAccreditationScope.is_active.is_(True),
        )
        .all()
    )
    standards: Dict[int, Set[str]] = {}
    iafs: Dict[int, Set[str]] = {}
    scopes: Dict[int, int] = {}
    for cb_id, std, iaf in rows:
        standards.setdefault(cb_id, set()).add(std)
        iafs.setdefault(cb_id, set()).add(iaf)
        scopes[cb_id] = scopes.get(cb_id, 0) + 1

    # 행렬이 비어 있는 CB는 레거시 콤마 스코프로 보완
    missing = [cid for cid in cb_ids if scopes.get(cid, 0) == 0]
    if missing:
        legacy = (
            db.query(
                CbAccreditationScopes.cb_id,
                CbAccreditationScopes.standard_code,
                CbAccreditationScopes.iaf_codes,
            )
            .filter(
                CbAccreditationScopes.cb_id.in_(missing),
                CbAccreditationScopes.is_active.is_(True),
            )
            .all()
        )
        for cb_id, std, iaf_codes in legacy:
            for raw in (iaf_codes or "").split(","):
                iaf = raw.strip()
                if not iaf:
                    continue
                if iaf.isdigit():
                    iaf = iaf.zfill(2)
                standards.setdefault(cb_id, set()).add(std)
                iafs.setdefault(cb_id, set()).add(iaf)
                scopes[cb_id] = scopes.get(cb_id, 0) + 1

    out: Dict[int, Tuple[int, int, str, str]] = {}
    for cid in cb_ids:
        stds = sorted(standards.get(cid, set()))
        iaf_set = sorted(iafs.get(cid, set()), key=lambda x: (len(x), x))
        out[cid] = (
            len(stds),
            scopes.get(cid, 0),
            ", ".join(stds),
            ", ".join(iaf_set),
        )
    return out


def _sync_legacy_accreditation_scopes(db: Session, cb_id: int, scopes: List[ScopeItem]) -> int:
    """행렬 Scope를 레거시 cb_accreditation_scopes(표준당 콤마 IAF)에도 UPSERT."""
    by_std: Dict[str, Set[str]] = {}
    for item in scopes:
        if not item.is_active:
            continue
        std = (item.standard_code or "").strip()
        if not std or not uses_iaf39(std):
            continue  # 레거시 콤마 IAF 테이블은 QMS/EMS/OHSMS만
        code = item.resolved_code()
        if not code:
            continue
        by_std.setdefault(std, set()).add(code)

    if not by_std:
        return 0

    now = datetime.utcnow()
    touched = 0
    for std, iaf_set in by_std.items():
        row = (
            db.query(CbAccreditationScopes)
            .filter(
                CbAccreditationScopes.cb_id == cb_id,
                CbAccreditationScopes.standard_code == std,
            )
            .first()
        )
        if row:
            existing = {x.strip() for x in (row.iaf_codes or "").split(",") if x.strip()}
            merged = sorted(existing | iaf_set, key=lambda x: (len(x), x))
            row.iaf_codes = ",".join(merged)
            row.standard_name = row.standard_name or std
            row.is_active = True
            row.updated_at = now
        else:
            db.add(
                CbAccreditationScopes(
                    cb_id=cb_id,
                    standard_code=std,
                    standard_name=std,
                    iaf_codes=",".join(sorted(iaf_set, key=lambda x: (len(x), x))),
                    use_nace=0,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        touched += 1
    return touched


def _list_scopes(db: Session, cb_id: int) -> List[ScopeItem]:
    """cb_scope_matrix + 레거시 cb_accreditation_scopes(콤마 IAF)를 합쳐 반환."""
    by_key: Dict[Tuple[str, str], ScopeItem] = {}

    rows = (
        db.query(CbAccreditationScope)
        .filter(CbAccreditationScope.cb_id == cb_id)
        .order_by(CbAccreditationScope.standard_code.asc(), CbAccreditationScope.iaf_code.asc())
        .all()
    )
    for r in rows:
        std = (r.standard_code or "").strip()
        iaf = (r.iaf_code or "").strip()
        if iaf.isdigit():
            iaf = iaf.zfill(2)
        if not std or not iaf:
            continue
        by_key[(std, iaf)] = ScopeItem(
            id=r.id,
            standard_code=std,
            scope_code=iaf,
            iaf_code=iaf,
            is_active=bool(r.is_active),
            granted_date=r.granted_date,
            expiry_date=r.expiry_date,
        )

    legacy_rows = (
        db.query(CbAccreditationScopes)
        .filter(CbAccreditationScopes.cb_id == cb_id)
        .all()
    )
    for row in legacy_rows:
        std = (row.standard_code or "").strip()
        if not std:
            continue
        for raw in (row.iaf_codes or "").split(","):
            iaf = raw.strip()
            if iaf.isdigit():
                iaf = iaf.zfill(2)
            if not iaf:
                continue
            key = (std, iaf)
            if key not in by_key:
                # 레거시는 IAF 콤마 문자열 — iaf39 표준만 인정
                if not uses_iaf39(std):
                    continue
                by_key[key] = ScopeItem(
                    standard_code=std,
                    scope_code=iaf,
                    iaf_code=iaf,
                    is_active=bool(getattr(row, "is_active", True)),
                )

    return sorted(by_key.values(), key=lambda s: (s.standard_code, s.iaf_code))


def _upsert_scopes(
    db: Session,
    cb_id: int,
    scopes: List[ScopeItem],
    *,
    replace_all: bool = False,
) -> int:
    now = datetime.utcnow()
    upserted = 0
    incoming_keys: Set[Tuple[str, str]] = set()

    for item in scopes:
        std = (item.standard_code or "").strip()
        tax = taxonomy_for_standard(std)
        if tax == "none":
            continue  # 수행범위 코드 없는 표준
        iaf = item.resolved_code()
        if not std or not iaf:
            continue
        incoming_keys.add((std, iaf))
        row = (
            db.query(CbAccreditationScope)
            .filter(
                CbAccreditationScope.cb_id == cb_id,
                CbAccreditationScope.standard_code == std,
                CbAccreditationScope.iaf_code == iaf,
            )
            .first()
        )
        if row:
            row.is_active = item.is_active
            if item.granted_date is not None:
                row.granted_date = item.granted_date
            if item.expiry_date is not None:
                row.expiry_date = item.expiry_date
            row.updated_at = now
        else:
            db.add(
                CbAccreditationScope(
                    cb_id=cb_id,
                    standard_code=std,
                    iaf_code=iaf,
                    is_active=item.is_active,
                    granted_date=item.granted_date,
                    expiry_date=item.expiry_date,
                    created_at=now,
                    updated_at=now,
                )
            )
        upserted += 1

    if replace_all:
        existing = db.query(CbAccreditationScope).filter(CbAccreditationScope.cb_id == cb_id).all()
        for row in existing:
            key = (row.standard_code, row.iaf_code)
            if key not in incoming_keys:
                row.is_active = False
                row.updated_at = now

    return upserted


def _platform_standard_codes(db: Session) -> List[str]:
    rows = (
        db.query(StandardMaster)
        .filter(StandardMaster.is_active.is_(True))
        .order_by(StandardMaster.id.asc())
        .all()
    )
    if rows:
        return [r.standard_code for r in rows]
    return list(DEFAULT_STANDARDS)


def _iaf_by_standard(db: Session, cb_id: int) -> Dict[str, List[str]]:
    """표준코드 → 활성 수행범위 코드 목록. 행렬 우선, 레거시(IAF39만) 보완."""
    out: Dict[str, List[str]] = {}

    def _add(std: str, iaf: str) -> None:
        s = (std or "").strip()
        tax = taxonomy_for_standard(s)
        if tax == "none":
            return
        i = normalize_scope_code(tax, iaf)
        if not s or not i:
            return
        out.setdefault(s, [])
        if i not in out[s]:
            out[s].append(i)

    rows = (
        db.query(CbAccreditationScope.standard_code, CbAccreditationScope.iaf_code)
        .filter(
            CbAccreditationScope.cb_id == cb_id,
            CbAccreditationScope.is_active.is_(True),
        )
        .order_by(CbAccreditationScope.standard_code.asc(), CbAccreditationScope.iaf_code.asc())
        .all()
    )
    for std, iaf in rows:
        _add(std, iaf)

    legacy_rows = (
        db.query(CbAccreditationScopes.standard_code, CbAccreditationScopes.iaf_codes)
        .filter(
            CbAccreditationScopes.cb_id == cb_id,
            CbAccreditationScopes.is_active.is_(True),
        )
        .all()
    )
    for std, iaf_codes in legacy_rows:
        if not uses_iaf39(std or ""):
            continue
        for raw in (iaf_codes or "").split(","):
            _add(std, raw)
    return out


def _list_standard_accreditations(db: Session, cb_id: int) -> List[StandardAccreditationItem]:
    """운용 15개 표준 골격 + 저장된 인정기관/인정번호 + 표준별 IAF 수행범위."""
    masters = (
        db.query(StandardMaster)
        .filter(StandardMaster.is_active.is_(True))
        .order_by(StandardMaster.id.asc())
        .all()
    )
    name_map = {r.standard_code: r.standard_name for r in masters}
    codes = [r.standard_code for r in masters] or list(DEFAULT_STANDARDS)

    saved = {
        r.standard_code: r
        for r in db.query(CbStandardAccreditation)
        .filter(CbStandardAccreditation.cb_id == cb_id)
        .all()
    }
    ab_name = {
        (r.code or "").strip(): r.name_en
        for r in db.query(AccreditationBodies).all()
        if r.code
    }
    iaf_map = _iaf_by_standard(db, cb_id)

    items: List[StandardAccreditationItem] = []
    for code in codes:
        row = saved.get(code)
        ab = (row.ab_code if row else None) or None
        reg = (row.registration_no if row else None) or None
        active = bool(row.is_active) if row else False
        if not active and (ab or reg or iaf_map.get(code)):
            active = True
        scopes = iaf_map.get(code, [])
        tax = taxonomy_for_standard(code)
        items.append(
            StandardAccreditationItem(
                standard_code=code,
                standard_name=name_map.get(code),
                ab_code=ab,
                ab_name_en=ab_name.get(ab or ""),
                registration_no=reg,
                scope_taxonomy=tax,
                scope_taxonomy_label=TAXONOMY_LABELS.get(tax, tax),
                has_scope_codes=tax != "none",
                scope_codes=scopes,
                iaf_codes=scopes if tax == "iaf39" else [],
                is_active=active,
            )
        )
    return items


def _held_standards_summary(db: Session, cb_ids: List[int]) -> Dict[int, Tuple[int, List[str], str]]:
    """cb_id -> (held_count, held_standard_codes, ab_codes summary)."""
    if not cb_ids:
        return {}
    rows = (
        db.query(
            CbStandardAccreditation.cb_id,
            CbStandardAccreditation.standard_code,
            CbStandardAccreditation.ab_code,
        )
        .filter(
            CbStandardAccreditation.cb_id.in_(cb_ids),
            CbStandardAccreditation.is_active.is_(True),
        )
        .all()
    )
    stds: Dict[int, List[str]] = {}
    abs_: Dict[int, Set[str]] = {}
    for cb_id, std, ab in rows:
        stds.setdefault(cb_id, [])
        if std and std not in stds[cb_id]:
            stds[cb_id].append(std)
        if ab:
            abs_.setdefault(cb_id, set()).add(ab)
    out: Dict[int, Tuple[int, List[str], str]] = {}
    for cid in cb_ids:
        held = stds.get(cid, [])
        out[cid] = (len(held), held, ", ".join(sorted(abs_.get(cid, set()))))
    return out


def _upsert_standard_accreditations(
    db: Session,
    cb_id: int,
    items: List[StandardAccreditationItem],
    *,
    replace_all: bool = True,
) -> int:
    now = datetime.utcnow()
    touched = 0
    seen: Set[str] = set()
    for item in items:
        std = (item.standard_code or "").strip()
        if not std:
            continue
        seen.add(std)
        ab = (item.ab_code or "").strip() or None
        reg = (item.registration_no or "").strip() or None
        active = bool(item.is_active) and bool(ab or reg)
        row = (
            db.query(CbStandardAccreditation)
            .filter(
                CbStandardAccreditation.cb_id == cb_id,
                CbStandardAccreditation.standard_code == std,
            )
            .first()
        )
        if row:
            row.ab_code = ab
            row.registration_no = reg
            row.is_active = active
            row.updated_at = now
        else:
            if not active:
                continue
            db.add(
                CbStandardAccreditation(
                    cb_id=cb_id,
                    standard_code=std,
                    ab_code=ab,
                    registration_no=reg,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        # 표준별 scope_codes가 오면 해당 표준 행만 머지 (전체 replace는 /scopes)
        codes = list(item.scope_codes or item.iaf_codes or [])
        if codes:
            scope_items = [
                ScopeItem(standard_code=std, scope_code=c, iaf_code=c, is_active=True)
                for c in codes
            ]
            _upsert_scopes(db, cb_id, scope_items, replace_all=False)
        touched += 1

    if replace_all:
        for row in (
            db.query(CbStandardAccreditation)
            .filter(CbStandardAccreditation.cb_id == cb_id)
            .all()
        ):
            if row.standard_code not in seen:
                row.is_active = False
                row.updated_at = now
    return touched


def _sanitize_cb_contact(payload: CbUpsertBody) -> dict:
    """사업자번호/전화/이메일/웹 정규화 — 잘못된 값이면 400."""
    cleaned = sanitize_contact_fields(
        biz_reg_no=payload.biz_reg_no,
        tel=payload.tel,
        email=payload.email,
        website=payload.website,
    )
    data = payload.model_dump(exclude={"scopes", "contract", "standard_accreditations"})
    if "biz_reg_no" in cleaned:
        data["biz_reg_no"] = cleaned["biz_reg_no"]
    if "tel" in cleaned:
        data["tel"] = cleaned["tel"]
    if "email" in cleaned:
        data["email"] = cleaned["email"]
    if "website" in cleaned:
        data["website"] = cleaned["website"]
    return data


def _detail(db: Session, cb: CertificationBodies) -> CbDetailResponse:
    scopes = _list_scopes(db, cb.id)
    active = [s for s in scopes if s.is_active]
    standards = {s.standard_code for s in active}
    base = cb_to_spec_dict(cb)
    return CbDetailResponse(
        **base,
        scopes=scopes,
        standard_accreditations=_list_standard_accreditations(db, cb.id),
        standard_count=len(standards),
        scope_count=len(active),
    )


def _get_or_create_contract(db: Session, cb: CertificationBodies, year: Optional[int] = None) -> CBContract:
    y = year or datetime.utcnow().year
    contract = ensure_default_cb_contract(db, cb, year=y)
    return contract


def _contract_info(contract: Optional[CBContract], year: Optional[int] = None) -> ContractInfo:
    y = year or datetime.utcnow().year
    if not contract:
        return ContractInfo(contract_year=y, tier=CBTier.MEDIUM.value)
    return ContractInfo(
        id=contract.id,
        contract_year=contract.contract_year,
        tier=contract.tier or CBTier.MEDIUM.value,
        annual_base_fee=Decimal(str(contract.annual_base_fee or 0)),
        price_per_md=Decimal(str(contract.price_per_md or 0)),
        contract_start_date=contract.contract_start_date,
        contract_end_date=contract.contract_end_date,
        is_active=bool(contract.is_active),
    )


def _list_auditors(db: Session, cb_id: int) -> List[AuditorMemberItem]:
    rows = (
        db.query(AuditorCbMemberships, Auditor)
        .outerjoin(Auditor, Auditor.id == AuditorCbMemberships.auditor_id)
        .filter(AuditorCbMemberships.cb_id == cb_id)
        .order_by(AuditorCbMemberships.id.desc())
        .limit(200)
        .all()
    )
    items: List[AuditorMemberItem] = []
    for m, a in rows:
        items.append(
            AuditorMemberItem(
                membership_id=m.id,
                auditor_id=m.auditor_id,
                name=(a.name if a else f"#{m.auditor_id}"),
                email=a.email if a else None,
                phone=a.phone if a else None,
                grade=(a.grade if a else None) or m.grade_at_cb,
                approved_grade=m.approved_grade or m.apply_grade,
                status=m.status,
                employment_type=m.employment_type,
                iaf_codes=m.approved_iaf_codes or (a.iaf_codes if a else None),
                kar_no=m.kar_no,
                is_primary=bool(m.is_primary),
            )
        )
    return items


def _full_detail(db: Session, cb: CertificationBodies, *, year: Optional[int] = None) -> CbFullDetailResponse:
    base = _detail(db, cb)
    contract = _get_or_create_contract(db, cb, year=year)
    auditors = _list_auditors(db, cb.id)
    return CbFullDetailResponse(
        **base.model_dump(),
        contract=_contract_info(contract, year=year),
        auditor_count=len(auditors),
        auditors=auditors,
    )


def _apply_contract(db: Session, cb: CertificationBodies, payload: ContractPayload) -> CBContract:
    year = payload.contract_year or datetime.utcnow().year
    contract = _get_or_create_contract(db, cb, year=year)
    if payload.tier is not None:
        tier = str(payload.tier).strip().upper()
        if tier not in {t.value for t in CBTier}:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 티어입니다: {tier}")
        contract.tier = tier
    if payload.annual_base_fee is not None:
        contract.annual_base_fee = Decimal(str(payload.annual_base_fee))
    if payload.price_per_md is not None:
        price = Decimal(str(payload.price_per_md))
        contract.price_per_md = price
        cb.fee_per_md = price
    if payload.is_active is not None:
        contract.is_active = payload.is_active
    return contract


def _contracts_by_cb(db: Session, cb_ids: List[int], year: int) -> Dict[int, CBContract]:
    if not cb_ids:
        return {}
    rows = (
        db.query(CBContract)
        .filter(CBContract.cb_id.in_(cb_ids), CBContract.contract_year == year)
        .all()
    )
    return {r.cb_id: r for r in rows}


# ---------- Endpoints ----------

@router.get("/meta/matrix-options")
def matrix_options(
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    ensure_accreditation_bodies(db)
    ensure_scope_code_masters(db)
    db.commit()
    standards = _platform_standard_codes(db)
    std_options = [
        {"standard_code": code, "standard_name": name}
        for code, name in ENTERPRISE_ISO_STANDARDS
    ]
    rows = (
        db.query(StandardMaster)
        .filter(StandardMaster.is_active.is_(True))
        .order_by(StandardMaster.id.asc())
        .all()
    )
    if rows:
        std_options = [
            {"standard_code": r.standard_code, "standard_name": r.standard_name}
            for r in rows
        ]
        standards = [r.standard_code for r in rows]

    # 표준별 수행범위 택소노미 + 코드 목록
    standard_scope_options = []
    for opt in std_options:
        meta = standard_scope_meta(opt["standard_code"])
        standard_scope_options.append({**opt, **meta})

    taxonomies = {}
    for tax, label in TAXONOMY_LABELS.items():
        if tax == "none":
            taxonomies[tax] = {"label": label, "codes": []}
        else:
            taxonomies[tax] = {"label": label, "codes": codes_for_taxonomy(tax)}

    abs_rows = (
        db.query(AccreditationBodies)
        .filter(or_(AccreditationBodies.is_active.is_(True), AccreditationBodies.is_active.is_(None)))
        .order_by(AccreditationBodies.continent.asc(), AccreditationBodies.code.asc(), AccreditationBodies.name.asc())
        .all()
    )
    accreditation_bodies = [
        {
            "code": (r.code or r.name or "").strip(),
            "name": r.name,
            "name_en": r.name_en,
            "continent": r.continent,
            "country_code": r.country_code or r.country,
        }
        for r in abs_rows
        if (r.code or r.name)
    ]
    return {
        "standards": standards,
        "standard_options": std_options,
        "standard_scope_options": standard_scope_options,
        "taxonomies": taxonomies,
        "iaf_codes": DEFAULT_IAF_CODES,  # 하위호환 — 9001/14001/45001 전용
        "iaf39_standards": sorted(
            [c for c in standards if taxonomy_for_standard(c) == "iaf39"]
        ),
        "accreditation_bodies": accreditation_bodies,
    }


@router.get("", response_model=CbListResponse)
def list_certification_bodies(
    q: Optional[str] = Query(None, description="기관명/코드/등록번호 검색"),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    query = db.query(CertificationBodies)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CertificationBodies.name.ilike(like),
                CertificationBodies.code.ilike(like),
                CertificationBodies.reg_no.ilike(like),
                CertificationBodies.accreditation_no.ilike(like),
                CertificationBodies.biz_no.ilike(like),
            )
        )
    if status_filter:
        st = status_filter.strip().lower()
        if st == "active":
            query = query.filter(
                or_(CertificationBodies.status.in_(["정상", "active", "운영"]), CertificationBodies.is_active.is_(True))
            )
        elif st == "suspended":
            query = query.filter(or_(CertificationBodies.status.in_(["정지", "suspended"]), CertificationBodies.is_active.is_(False)))
        elif st == "inactive":
            query = query.filter(CertificationBodies.status.in_(["취소", "inactive", "폐업"]))

    total = query.count()
    rows = (
        query.order_by(CertificationBodies.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    year = datetime.utcnow().year
    for r in rows:
        ensure_default_cb_contract(db, r, year=year)
    db.flush()
    cb_ids = [r.id for r in rows]
    counts = _scope_counts(db, cb_ids)
    held = _held_standards_summary(db, cb_ids)
    contracts = _contracts_by_cb(db, cb_ids, year)
    data: List[CbListItem] = []
    for r in rows:
        std_cnt, sc_cnt, std_sum, iaf_sum = counts.get(r.id, (0, 0, "", ""))
        held_cnt, held_stds, ab_sum = held.get(r.id, (0, [], ""))
        # 목록 "보유 표준"은 표준별 인정(AB/인정번호) 건수 우선; 없으면 행렬 표준 수
        display_std_cnt = held_cnt or std_cnt
        display_std_sum = ", ".join(held_stds) if held_stds else std_sum
        spec = cb_to_spec_dict(r)
        contract = contracts.get(r.id)
        data.append(
            CbListItem(
                id=r.id,
                cb_code=spec["cb_code"],
                cb_name=spec["cb_name"],
                cb_name_en=spec["cb_name_en"],
                accreditation_body=spec["accreditation_body"],
                reg_no=spec["reg_no"],
                biz_reg_no=spec["biz_reg_no"],
                ceo_name=spec["ceo_name"],
                tel=spec["tel"],
                email=spec["email"],
                status=spec["status"],
                standard_count=display_std_cnt,
                held_standard_count=held_cnt,
                held_standards=held_stds,
                ab_summary=ab_sum,
                scope_count=sc_cnt,
                standards_summary=display_std_sum,
                iaf_summary=iaf_sum,
                billing_tier=(contract.tier if contract else CBTier.MEDIUM.value),
                contract_year=(contract.contract_year if contract else year),
            )
        )
    db.commit()
    return CbListResponse(total=total, page=page, limit=limit, data=data)


@router.get("/{cb_id}/detail", response_model=CbFullDetailResponse)
def get_certification_body_full_detail(
    cb_id: int,
    contract_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """CB 기본정보 + Scope + 과금 정책 + 소속 심사원 통합 상세."""
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    detail = _full_detail(db, cb, year=contract_year)
    db.commit()
    return detail


@router.get("/{cb_id}", response_model=CbFullDetailResponse)
def get_certification_body(
    cb_id: int,
    contract_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """기본 정보 + Scope(행렬/레거시) + 과금/티어 통합 상세."""
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    detail = _full_detail(db, cb, year=contract_year)
    db.commit()
    return detail


@router.post("", response_model=CbFullDetailResponse, status_code=status.HTTP_201_CREATED)
def create_certification_body(
    payload: CbUpsertBody,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    code = payload.cb_code.strip()
    if db.query(CertificationBodies).filter(CertificationBodies.code == code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 기관 코드입니다.")

    now = datetime.utcnow()
    cb = CertificationBodies(**_new_cb_defaults(now))
    cleaned = _sanitize_cb_contact(payload)
    apply_spec_fields(cb, cleaned)
    if not cb.cb_initial:
        cb.cb_initial = code[:20]
    db.add(cb)
    db.flush()
    if payload.contract:
        _apply_contract(db, cb, payload.contract)
    else:
        ensure_default_cb_contract(db, cb, year=now.year)
    if payload.scopes:
        _upsert_scopes(db, cb.id, payload.scopes, replace_all=True)
        _sync_legacy_accreditation_scopes(db, cb.id, payload.scopes)
    if payload.standard_accreditations is not None:
        _upsert_standard_accreditations(db, cb.id, payload.standard_accreditations, replace_all=True)
    db.commit()
    db.refresh(cb)
    return _full_detail(db, cb)


@router.put("/{cb_id}", response_model=CbFullDetailResponse)
def update_certification_body(
    cb_id: int,
    payload: CbUpsertBody,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """법인정보 / Scope / 표준별 인정정보 / 과금단가 통합 저장."""
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")

    new_code = payload.cb_code.strip()
    dup = (
        db.query(CertificationBodies)
        .filter(CertificationBodies.code == new_code, CertificationBodies.id != cb_id)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="이미 존재하는 기관 코드입니다.")

    cleaned = _sanitize_cb_contact(payload)
    apply_spec_fields(cb, cleaned)
    cb.updated_at = datetime.utcnow()
    if payload.scopes is not None:
        _upsert_scopes(db, cb.id, payload.scopes, replace_all=True)
        _sync_legacy_accreditation_scopes(db, cb.id, payload.scopes)
    if payload.standard_accreditations is not None:
        _upsert_standard_accreditations(db, cb.id, payload.standard_accreditations, replace_all=True)
    if payload.contract is not None:
        _apply_contract(db, cb, payload.contract)
    db.commit()
    db.refresh(cb)
    return _full_detail(db, cb)


@router.put("/{cb_id}/scopes", response_model=CbDetailResponse)
def update_cb_scopes(
    cb_id: int,
    payload: ScopeMatrixUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """표준별 인증수행범위 저장 (IAF39 / MDQMS / FSMS / NQMS / BCMS)."""
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    _upsert_scopes(db, cb.id, payload.scopes, replace_all=payload.replace_all)
    _sync_legacy_accreditation_scopes(db, cb.id, payload.scopes)
    cb.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(cb)
    return _detail(db, cb)


class StandardAccreditationUpdate(BaseModel):
    items: List[StandardAccreditationItem]
    replace_all: bool = True


@router.get("/{cb_id}/standard-accreditations", response_model=List[StandardAccreditationItem])
def get_cb_standard_accreditations(
    cb_id: int,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    return _list_standard_accreditations(db, cb_id)


@router.put("/{cb_id}/standard-accreditations", response_model=List[StandardAccreditationItem])
def put_cb_standard_accreditations(
    cb_id: int,
    payload: StandardAccreditationUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    _upsert_standard_accreditations(db, cb.id, payload.items, replace_all=payload.replace_all)
    cb.updated_at = datetime.utcnow()
    db.commit()
    return _list_standard_accreditations(db, cb_id)


def _cell(row: Any, *keys: str, default: Any = None) -> Any:
    """엑셀 행에서 한글/영문 컬럼명 후보를 순차 조회 (부분 일치 포함)."""
    import pandas as pd

    index_map = {str(c).strip(): c for c in row.index}
    lower_map = {str(c).strip().lower().replace(" ", ""): c for c in row.index}

    def _read(col_key: Any) -> Any:
        val = row.get(col_key)
        if pd.isna(val):
            return None
        text = str(val).strip()
        if not text or text.lower() == "nan":
            return None
        # 사업자번호 등 float 변환 잔여 `.0` 제거
        if text.endswith(".0") and text.replace(".", "", 1).isdigit():
            text = text[:-2]
        return text

    for key in keys:
        if key in index_map:
            got = _read(index_map[key])
            if got is not None:
                return got
        norm = key.strip().lower().replace(" ", "")
        if norm in lower_map:
            got = _read(lower_map[norm])
            if got is not None:
                return got
        # 부분 일치: '인증기관명(국문)' ← key '인증기관명' (접두 + 괄호 확장만 허용)
        for col_name, col_key in index_map.items():
            if col_name.startswith(f"{key}(") or col_name.startswith(f"{key} "):
                got = _read(col_key)
                if got is not None:
                    return got
    return default


def _compose_address(row: Any) -> Optional[str]:
    postal = _cell(row, "우편번호", "postal", "zip", "zip_code")
    addr = _cell(row, "주소", "address", "본사주소")
    detail = _cell(row, "상세주소", "address_detail", "나머지주소")
    parts: List[str] = []
    if postal:
        parts.append(f"({postal})")
    if addr:
        parts.append(addr)
    if detail:
        parts.append(detail)
    return " ".join(parts) if parts else None


def _find_existing_cb(
    db: Session,
    *,
    cb_code: Optional[str],
    cb_name: Optional[str],
    biz_reg_no: Optional[str],
) -> Optional[CertificationBodies]:
    if cb_code:
        cb = db.query(CertificationBodies).filter(CertificationBodies.code == cb_code).first()
        if cb:
            return cb
        cb = db.query(CertificationBodies).filter(CertificationBodies.cb_initial == cb_code).first()
        if cb:
            return cb
    if biz_reg_no:
        digits = "".join(ch for ch in biz_reg_no if ch.isdigit())
        candidates = db.query(CertificationBodies).filter(CertificationBodies.biz_no.isnot(None)).all()
        for c in candidates:
            if c.biz_no and "".join(ch for ch in str(c.biz_no) if ch.isdigit()) == digits:
                return c
    if cb_name:
        return db.query(CertificationBodies).filter(CertificationBodies.name == cb_name).first()
    return None


def _parse_scope_tokens(scopes_raw: str, standards_raw: str = "", iaf_raw: str = "") -> List[ScopeItem]:
    """'ISO 9001, ISO 14001' / 'IAF 01, 14' / 혼합 문자열을 ScopeItem 목록으로 변환."""
    import re

    standards: List[str] = []
    iafs: List[str] = []

    def absorb(token: str) -> None:
        t = token.strip()
        if not t:
            return
        upper = t.upper().replace("ＩＳＯ", "ISO")
        m_std = re.search(r"(?:ISO\s*)?(9001|14001|45001|27001|22000|50001|37001)", upper)
        if m_std and ("ISO" in upper or m_std.group(1) in upper):
            standards.append(f"ISO {m_std.group(1)}")
            return
        m_iaf = re.search(r"(?:IAF\s*)?(\d{1,2})\b", upper)
        if m_iaf and ("IAF" in upper or t.strip().isdigit() or re.fullmatch(r"0?\d{1,2}", t.strip())):
            iafs.append(m_iaf.group(1).zfill(2))
            return
        if re.fullmatch(r"(9001|14001|45001|27001|22000|50001|37001)", upper):
            standards.append(f"ISO {upper}")

    for blob in (scopes_raw, standards_raw, iaf_raw):
        if not blob:
            continue
        for part in re.split(r"[,;/|]+", str(blob)):
            absorb(part)

    def uniq(items: List[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for x in items:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    standards = uniq(standards)
    iafs = uniq(iafs)

    if not standards and not iafs:
        return []
    if not standards:
        standards = ["ISO 9001"]
    if not iafs:
        iafs = ["00"]

    return [
        ScopeItem(standard_code=std, iaf_code=iaf, is_active=True)
        for std in standards
        for iaf in iafs
    ]


def _read_excel_dataframe(content: bytes, filename: str):
    try:
        import pandas as pd
    except ImportError as e:
        raise HTTPException(status_code=500, detail="pandas가 설치되어 있지 않습니다.") from e

    try:
        buf = io.BytesIO(content)
        if filename.endswith(".ods"):
            df = pd.read_excel(buf, engine="odf")
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(buf, engine="openpyxl")
        else:
            df = pd.read_excel(buf)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"엑셀 데이터 파싱 실패: {e}") from e

    if df.empty:
        raise HTTPException(status_code=400, detail="시트가 비어 있습니다.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _reset_certification_body_tables(db: Session) -> None:
    """mock/중복 CB 마스터를 비우고 AUTO_INCREMENT를 1로 리셋.

    MySQL FK를 잠시 해제 후 CB 전용 테이블을 정리한다.
    users.cb_id 는 NULL 처리하여 계정은 보존한다.
    """
    from sqlalchemy import text

    db.execute(text("UPDATE users SET cb_id = NULL WHERE cb_id IS NOT NULL"))
    db.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    try:
        for table in [
            "auditor_cb_memberships",
            "certification_applications",
            "cb_accreditation_record_scopes",
            "cb_accreditation_records",
            "cb_accredited_scopes",
            "cb_accreditation_scopes",
            "cb_scope_matrix",
            "cb_standard_accreditations",
            "cb_contracts",
            "cb_operational_rules",
            "cb_staff_members",
            "audit_requests",
            "certification_bodies",
        ]:
            try:
                db.execute(text(f"DELETE FROM {table}"))
            except Exception:  # noqa: BLE001
                pass
        db.execute(text("ALTER TABLE certification_bodies AUTO_INCREMENT = 1"))
        db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        db.commit()
    except Exception:
        try:
            db.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        except Exception:  # noqa: BLE001
            pass
        db.rollback()
        raise


def _import_cb_dataframe(db: Session, df, *, fresh_insert: bool = False) -> ExcelUploadResponse:
    """엑셀 DataFrame → certification_bodies (+ scopes) INSERT/UPSERT."""
    created = updated = scopes_upserted = imported_count = 0
    errors: List[dict] = []
    now = datetime.utcnow()

    for idx, row in df.iterrows():
        row_no = int(idx) + 2
        try:
            cb_name = _cell(
                row,
                "인증기관명(국문)",
                "인증기관명",
                "기관명",
                "cb_name",
                "name",
            )
            if not cb_name:
                continue

            initial = _cell(row, "이니셜", "cb_initial", "initial")
            cb_code = _cell(
                row,
                "기관코드",
                "코드",
                "cb_code",
                "code",
                "이니셜",
                default=initial or f"CB-{imported_count + 1:03d}",
            )
            biz_reg_no = _cell(row, "사업자등록번호", "사업자번호", "biz_reg_no", "biz_no")
            fields = {
                "cb_code": cb_code,
                "cb_name": cb_name,
                "cb_name_en": _cell(row, "인증기관명(영문)", "영문명", "cb_name_en", "name_en"),
                "cb_initial": initial or (str(cb_code)[:20] if cb_code else None),
                "reg_no": _cell(row, "등록번호", "인정번호", "인정등록번호", "reg_no"),
                "accreditation_body": _cell(row, "인정기관", "accreditation_body", default="KAB") or "KAB",
                "biz_reg_no": biz_reg_no,
                "ceo_name": _cell(row, "대표자명", "대표자", "ceo_name"),
                "address": _compose_address(row),
                "tel": _cell(row, "대표전화번호", "전화번호", "전화", "tel", "phone"),
                "email": _cell(row, "이메일", "대표이메일", "email"),
                "website": _cell(row, "홈페이지", "웹사이트", "website"),
                "logo_path": _cell(row, "로고", "logo_path"),
                "status": _cell(row, "상태", "status", default="active") or "active",
            }

            cb = None
            if not fresh_insert:
                cb = _find_existing_cb(
                    db,
                    cb_code=str(cb_code) if cb_code else None,
                    cb_name=cb_name,
                    biz_reg_no=biz_reg_no,
                )

            if cb:
                if str(fields["cb_code"]).startswith("CB-") and cb.code and not str(cb.code).startswith("CB-"):
                    fields["cb_code"] = cb.code
                apply_spec_fields(cb, fields)
                cb.updated_at = now
                updated += 1
            else:
                cb = CertificationBodies(**_new_cb_defaults(now))
                apply_spec_fields(cb, fields)
                if not cb.cb_initial:
                    cb.cb_initial = str(cb_code)[:20]
                db.add(cb)
                db.flush()
                ensure_default_cb_contract(db, cb, year=now.year)
                created += 1

            fax = _cell(row, "FAX", "팩스", "fax")
            bank = _cell(row, "은행정보", "은행", "bank_name")
            account = _cell(row, "계좌정보", "계좌번호", "account_no")
            if fax is not None:
                cb.fax = fax
            if bank is not None:
                cb.bank_name = bank
            if account is not None:
                cb.account_no = account

            scopes_raw = _cell(row, "인정범위", "보유표준", "Scope", "scopes", default="") or ""
            standards_raw = _cell(row, "표준", "standard_code", "standards", default="") or ""
            iaf_raw = _cell(row, "IAF", "IAF코드", "iaf_codes", "iaf_code", default="") or ""
            scope_items = _parse_scope_tokens(scopes_raw, standards_raw, iaf_raw)
            if scope_items:
                scopes_upserted += _upsert_scopes(db, cb.id, scope_items, replace_all=fresh_insert)
                _sync_legacy_accreditation_scopes(db, cb.id, scope_items)

            imported_count += 1
        except Exception as e:  # noqa: BLE001
            errors.append({"row": row_no, "error": str(e)})

    db.commit()
    return ExcelUploadResponse(
        success=True,
        imported_count=imported_count,
        created=created,
        updated=updated,
        scopes_upserted=scopes_upserted,
        error_count=len(errors),
        errors=errors[:50],
        message=f"총 {imported_count}개 인증기관 정보가 성공적으로 DB에 등록되었습니다.",
    )


@router.post("/upload-excel", response_model=ExcelUploadResponse)
async def upload_certification_bodies_excel(
    file: UploadFile = File(..., description="institutionData.ods 또는 Excel (.ods/.xlsx/.xls)"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """백엔드 전용 ODS/XLSX 파싱 → certification_bodies / scopes Upsert."""
    filename = (file.filename or "").lower()
    if not filename.endswith((".ods", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="ODS 또는 Excel 파일(.xlsx, .xls, .ods)만 업로드 가능합니다.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    df = _read_excel_dataframe(content, filename)
    try:
        return _import_cb_dataframe(db, df, fresh_insert=False)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"엑셀 일괄 등록 실패: {e}") from e


@router.post("/reset-and-upload", response_model=ExcelUploadResponse)
async def reset_and_upload_certification_bodies(
    file: UploadFile = File(..., description="institutionData.ods / .xlsx — 기존 CB 삭제 후 재시딩"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """기존 mock/중복 CB를 비운 뒤 엑셀 70여 개만 고유 INSERT (ID 1부터)."""
    filename = (file.filename or "").lower()
    if not filename.endswith((".ods", ".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="ODS 또는 Excel 파일(.xlsx, .xls, .ods)만 업로드 가능합니다.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    # 파싱을 먼저 수행해 실패 시 DB를 비우지 않음
    df = _read_excel_dataframe(content, filename)

    try:
        _reset_certification_body_tables(db)
        result = _import_cb_dataframe(db, df, fresh_insert=True)
        result.message = (
            f"기존 CB 데이터를 초기화한 뒤 {result.imported_count}개 기관을 재등록했습니다."
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"초기화 후 재시딩 실패: {e}") from e


@router.post("/bulk-import", response_model=BulkImportResult)
async def bulk_import_certification_bodies(
    file: UploadFile = File(..., description="JSON 또는 CSV"),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """70여 개 CB + Scope 일괄 UPSERT.

    JSON 형식:
      [{ "cb_code":"...", "cb_name":"...", "scopes":[{"standard_code":"ISO 9001","iaf_code":"14"}, ...] }, ...]
    CSV 컬럼:
      cb_code,cb_name,cb_name_en,cb_initial,reg_no,accreditation_body,biz_reg_no,ceo_name,address,tel,email,website,status,standard_code,iaf_codes
      (iaf_codes 콤마 구분 → 개별 행으로 분리)
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")

    filename = (file.filename or "").lower()
    records: List[dict] = []

    if filename.endswith(".json") or text.strip().startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON 파싱 실패: {e}") from e
        if not isinstance(payload, list):
            raise HTTPException(status_code=400, detail="JSON 루트는 배열이어야 합니다.")
        records = payload
    else:
        reader = csv.DictReader(io.StringIO(text))
        grouped: Dict[str, dict] = {}
        for row in reader:
            code = (row.get("cb_code") or row.get("code") or "").strip()
            if not code:
                continue
            if code not in grouped:
                grouped[code] = {
                    "cb_code": code,
                    "cb_name": (row.get("cb_name") or row.get("name") or code).strip(),
                    "cb_name_en": row.get("cb_name_en") or row.get("name_en"),
                    "cb_initial": row.get("cb_initial"),
                    "reg_no": row.get("reg_no"),
                    "accreditation_body": row.get("accreditation_body") or "KAB",
                    "biz_reg_no": row.get("biz_reg_no") or row.get("biz_no"),
                    "ceo_name": row.get("ceo_name"),
                    "address": row.get("address"),
                    "tel": row.get("tel") or row.get("phone"),
                    "email": row.get("email"),
                    "website": row.get("website"),
                    "status": row.get("status") or "active",
                    "scopes": [],
                }
            std = (row.get("standard_code") or "").strip()
            iaf_raw = (row.get("iaf_codes") or row.get("iaf_code") or "").strip()
            if std and iaf_raw:
                for token in iaf_raw.replace(";", ",").split(","):
                    t = token.strip()
                    if not t:
                        continue
                    iaf = t.zfill(2) if t.isdigit() else t
                    grouped[code]["scopes"].append(
                        {"standard_code": std, "iaf_code": iaf, "is_active": True}
                    )
        records = list(grouped.values())

    created = updated = scopes_upserted = 0
    errors: List[dict] = []
    now = datetime.utcnow()

    try:
        for idx, item in enumerate(records, start=1):
            try:
                code = str(item.get("cb_code") or item.get("code") or "").strip()
                name = str(item.get("cb_name") or item.get("name") or "").strip()
                if not code or not name:
                    errors.append({"row": idx, "error": "cb_code/cb_name 필수"})
                    continue

                cb = db.query(CertificationBodies).filter(CertificationBodies.code == code).first()
                fields = {
                    "cb_code": code,
                    "cb_name": name,
                    "cb_name_en": item.get("cb_name_en") or item.get("name_en"),
                    "cb_initial": item.get("cb_initial") or code[:20],
                    "reg_no": item.get("reg_no"),
                    "accreditation_body": item.get("accreditation_body") or "KAB",
                    "biz_reg_no": item.get("biz_reg_no") or item.get("biz_no"),
                    "ceo_name": item.get("ceo_name"),
                    "address": item.get("address"),
                    "tel": item.get("tel") or item.get("phone"),
                    "email": item.get("email"),
                    "website": item.get("website"),
                    "logo_path": item.get("logo_path"),
                    "status": item.get("status") or "active",
                }

                if cb:
                    apply_spec_fields(cb, fields)
                    cb.updated_at = now
                    updated += 1
                else:
                    cb = CertificationBodies(**_new_cb_defaults(now))
                    apply_spec_fields(cb, fields)
                    if not cb.cb_initial:
                        cb.cb_initial = code[:20]
                    db.add(cb)
                    db.flush()
                    ensure_default_cb_contract(db, cb, year=now.year)
                    created += 1

                scope_items: List[ScopeItem] = []
                for s in item.get("scopes") or []:
                    if isinstance(s, dict):
                        scope_items.append(
                            ScopeItem(
                                standard_code=str(s.get("standard_code") or "").strip(),
                                iaf_code=str(s.get("iaf_code") or "").strip(),
                                is_active=bool(s.get("is_active", True)),
                                granted_date=_parse_date(s.get("granted_date")),
                                expiry_date=_parse_date(s.get("expiry_date")),
                            )
                        )
                if scope_items:
                    scopes_upserted += _upsert_scopes(db, cb.id, scope_items, replace_all=False)
                    _sync_legacy_accreditation_scopes(db, cb.id, scope_items)
            except Exception as e:  # noqa: BLE001
                errors.append({"row": idx, "error": str(e)})

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"일괄 업로드 실패: {e}") from e

    return BulkImportResult(
        message="인증기관 일괄 업로드가 완료되었습니다.",
        created=created,
        updated=updated,
        scopes_upserted=scopes_upserted,
        error_count=len(errors),
        errors=errors[:50],
    )
