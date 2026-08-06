"""IAF / ISO 표준 마스터 + CB 인정 Scope API.

1행 = 1개 표준 + 1개 IAF 코드 (콤마 구분 폐지).
"""
import csv
import io
from datetime import date, datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.core.security import CurrentUser, require_cb_scope, require_platform_admin
from app.models.cb import CertificationBodies
from app.models.enums import UsersRole
from app.models.master_data import CbAccreditedScope, IafCode, IsoStandard
from app.services.iaf_recommendation import recommend_iaf

router = APIRouter(tags=["Accreditation Masters"])


# ---------- Schemas ----------

class IafCodeOut(BaseModel):
    iaf_code_id: int
    iaf_code: str
    industry_name_ko: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    updated_at: Optional[datetime] = None


class RecommendIafItem(BaseModel):
    iaf_code_id: int
    iaf_code: str
    industry_name_ko: str
    name_en: Optional[str] = None
    source: str = Field(..., description="major | company_ksic | company_iaf")
    extra_exp_years: int = 0
    requires_committee: bool = False
    notes: Optional[str] = None
    preselected: bool = True


class RecommendIafResponse(BaseModel):
    major: Optional[str] = None
    company_id: Optional[int] = None
    recommendations: List[RecommendIafItem]


class IafCodeCreate(BaseModel):
    iaf_code: str
    industry_name_ko: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class IafCodeUpdate(BaseModel):
    industry_name_ko: Optional[str] = None
    name_en: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class IsoStandardOut(BaseModel):
    standard_id: int
    standard_key: Optional[str] = None
    standard_code: str
    standard_name_ko: str
    is_active: bool = True


class IsoStandardCreate(BaseModel):
    standard_key: Optional[str] = None
    standard_code: str
    standard_name_ko: str
    is_active: bool = True


class IsoStandardUpdate(BaseModel):
    standard_key: Optional[str] = None
    standard_name_ko: Optional[str] = None
    is_active: Optional[bool] = None


class CbScopeOut(BaseModel):
    scope_id: int
    cb_id: int
    standard_id: int
    iaf_code_id: int
    accreditation_body: str
    approval_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str
    status_label: str
    standard_code: Optional[str] = None
    standard_name_ko: Optional[str] = None
    iaf_code: Optional[str] = None
    industry_name_ko: Optional[str] = None


class CbScopeCreate(BaseModel):
    standard_id: int
    iaf_code_id: int
    accreditation_body: str = "KAB"
    approval_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str = "active"
    cb_id: Optional[int] = Field(
        default=None,
        description="platform_admin 전용. CB 계정은 세션 cb_id 강제",
    )


class CbScopeUpdate(BaseModel):
    accreditation_body: Optional[str] = None
    approval_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: Optional[str] = None


_STATUS_LABEL = {
    "active": "정상",
    "suspended": "정지",
    "withdrawn": "철회",
}

from app.data.standards_catalog import OPERATING_STANDARDS

# 운영 14규격 (비어 있을 때만 시드)
_DEFAULT_ISO = [(s.display_code, s.name_ko) for s in OPERATING_STANDARDS]

_DEFAULT_IAF = [
    ("01", "Agriculture, fishing"),
    ("14", "Rubber and plastic products"),
    ("17", "Basic metals and fabricated metal products"),
    ("18", "Machinery and equipment"),
    ("19", "Electrical and optical equipment"),
    ("28", "Construction"),
    ("29", "Wholesale and retail trade; Repair of motor vehicles, motorcycles and personal and household goods"),
    ("33", "Information technology"),
    ("34", "Engineering services"),
    ("35", "Other services"),
]


def _status_label(status_val: str) -> str:
    return _STATUS_LABEL.get(status_val, status_val)


def _scope_to_out(row: CbAccreditedScope) -> CbScopeOut:
    return CbScopeOut(
        scope_id=row.id,
        cb_id=row.cb_id,
        standard_id=row.standard_id,
        iaf_code_id=row.iaf_code_id,
        accreditation_body=row.accreditation_body,
        approval_date=row.approval_date,
        expiry_date=row.expiry_date,
        status=row.status,
        status_label=_status_label(row.status),
        standard_code=row.standard.standard_code if row.standard else None,
        standard_name_ko=row.standard.standard_name_ko if row.standard else None,
        iaf_code=row.iaf_code.code if row.iaf_code else None,
        industry_name_ko=row.iaf_code.name_ko if row.iaf_code else None,
    )


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
        raise HTTPException(status_code=403, detail="다른 인증기관의 Scope는 접근할 수 없습니다.")
    return current_user.cb_id


def _ensure_seed_masters(db: Session) -> None:
    """UI 드롭다운용 최소 시드 (비어 있을 때만)."""
    now = datetime.utcnow()
    if db.query(IsoStandard.id).first() is None:
        for code, name in _DEFAULT_ISO:
            db.add(
                IsoStandard(
                    standard_code=code,
                    standard_name_ko=name,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.flush()
    if db.query(IafCode.id).first() is None:
        for code, name in _DEFAULT_IAF:
            db.add(
                IafCode(
                    code=code,
                    name_ko=name,
                    name_en=name,
                    is_active=True,
                    updated_at=now,
                )
            )
        db.flush()
    db.commit()


def _iaf_out(r: IafCode) -> IafCodeOut:
    return IafCodeOut(
        iaf_code_id=r.id,
        iaf_code=r.code,
        industry_name_ko=r.name_ko,
        name_en=r.name_en,
        description=r.description,
        is_active=bool(r.is_active) if r.is_active is not None else True,
        updated_at=r.updated_at,
    )


def _iso_out(r: IsoStandard) -> IsoStandardOut:
    return IsoStandardOut(
        standard_id=r.id,
        standard_key=getattr(r, "standard_key", None),
        standard_code=r.standard_code,
        standard_name_ko=r.standard_name_ko,
        is_active=bool(r.is_active) if r.is_active is not None else True,
    )


def _create_scope_row(
    db: Session,
    *,
    cb_id: int,
    standard_id: int,
    iaf_code_id: int,
    accreditation_body: str = "KAB",
    approval_date: Optional[date] = None,
    expiry_date: Optional[date] = None,
    status_val: str = "active",
    allow_duplicate: bool = False,
) -> Tuple[CbAccreditedScope, str]:
    """반환: (row, action) action=created|exists|updated."""
    if status_val not in {"active", "suspended", "withdrawn"}:
        raise HTTPException(status_code=400, detail="status는 active|suspended|withdrawn 만 가능합니다.")

    if not db.query(CertificationBodies.id).filter(CertificationBodies.id == cb_id).first():
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")
    if not db.query(IsoStandard.id).filter(IsoStandard.id == standard_id).first():
        raise HTTPException(status_code=404, detail="표준을 찾을 수 없습니다.")
    if not db.query(IafCode.id).filter(IafCode.id == iaf_code_id).first():
        raise HTTPException(status_code=404, detail="IAF 코드를 찾을 수 없습니다.")

    existing = (
        db.query(CbAccreditedScope)
        .filter(
            CbAccreditedScope.cb_id == cb_id,
            CbAccreditedScope.standard_id == standard_id,
            CbAccreditedScope.iaf_code_id == iaf_code_id,
        )
        .first()
    )
    now = datetime.utcnow()
    if existing:
        if not allow_duplicate:
            raise HTTPException(
                status_code=400,
                detail="동일한 CB-표준-IAF Scope가 이미 등록되어 있습니다.",
            )
        existing.accreditation_body = accreditation_body or existing.accreditation_body
        if approval_date is not None:
            existing.approval_date = approval_date
        if expiry_date is not None:
            existing.expiry_date = expiry_date
        existing.status = status_val
        existing.updated_at = now
        db.flush()
        return existing, "updated"

    row = CbAccreditedScope(
        cb_id=cb_id,
        standard_id=standard_id,
        iaf_code_id=iaf_code_id,
        accreditation_body=accreditation_body or "KAB",
        approval_date=approval_date,
        expiry_date=expiry_date,
        status=status_val,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row, "created"


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"날짜 형식 오류: {value}")


def _resolve_standard(db: Session, raw: str) -> Optional[IsoStandard]:
    text = (raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        return db.query(IsoStandard).filter(IsoStandard.id == int(text)).first()
    return (
        db.query(IsoStandard)
        .filter(
            (IsoStandard.standard_code == text)
            | (IsoStandard.standard_code.ilike(f"%{text}%"))
            | (IsoStandard.standard_name_ko == text)
        )
        .first()
    )


def _resolve_iaf(db: Session, raw: str) -> Optional[IafCode]:
    text = (raw or "").strip()
    if not text:
        return None
    text = text.replace("IAF", "").replace("iaf", "").strip()
    if text.isdigit() and len(text) > 2:
        # numeric id
        by_id = db.query(IafCode).filter(IafCode.id == int(text)).first()
        if by_id:
            return by_id
    return db.query(IafCode).filter(IafCode.code == text).first() or db.query(IafCode).filter(
        IafCode.code == text.zfill(2)
    ).first()


# ---------- Meta (UI 선택용) ----------

@router.get("/meta/iaf-codes", response_model=List[IafCodeOut])
def meta_list_iaf_codes(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """등록된 활성 IAF 코드 목록."""
    _ensure_seed_masters(db)
    query = db.query(IafCode).filter(IafCode.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((IafCode.code.ilike(like)) | (IafCode.name_ko.ilike(like)))
    return [_iaf_out(r) for r in query.order_by(IafCode.code.asc()).limit(500).all()]


@router.get("/meta/iso-standards", response_model=List[IsoStandardOut])
def meta_list_iso_standards(
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """등록된 활성 ISO 표준 목록."""
    _ensure_seed_masters(db)
    query = db.query(IsoStandard).filter(IsoStandard.is_active.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (IsoStandard.standard_code.ilike(like))
            | (IsoStandard.standard_name_ko.ilike(like))
        )
    return [_iso_out(r) for r in query.order_by(IsoStandard.standard_code.asc()).all()]


@router.get("/meta/recommend-iaf", response_model=RecommendIafResponse)
def meta_recommend_iaf(
    major: Optional[str] = Query(None, description="전공학과명"),
    company_id: Optional[int] = Query(None, description="경력 기업 ID"),
    db: Session = Depends(get_db),
):
    """전공·경력 기업 기반 신청 가능 IAF 추천 목록."""
    if not (major and major.strip()) and company_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="major 또는 company_id 중 하나 이상 필요합니다.",
        )
    hints = recommend_iaf(db, major=major, company_id=company_id)
    return RecommendIafResponse(
        major=major.strip() if major else None,
        company_id=company_id,
        recommendations=[
            RecommendIafItem(
                iaf_code_id=h.iaf_code_id,
                iaf_code=h.iaf_code,
                industry_name_ko=h.industry_name_ko,
                name_en=h.name_en,
                source=h.source,
                extra_exp_years=h.extra_exp_years,
                requires_committee=h.requires_committee,
                notes=h.notes,
                preselected=True,
            )
            for h in hints
        ],
    )


# 하위 호환 별칭
@router.get("/masters/iaf-codes", response_model=List[IafCodeOut], include_in_schema=False)
def list_iaf_codes_alias(
    active_only: bool = Query(True),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if active_only:
        return meta_list_iaf_codes(q=q, db=db)
    _ensure_seed_masters(db)
    query = db.query(IafCode)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((IafCode.code.ilike(like)) | (IafCode.name_ko.ilike(like)))
    return [_iaf_out(r) for r in query.order_by(IafCode.code.asc()).limit(500).all()]


@router.get("/masters/iso-standards", response_model=List[IsoStandardOut], include_in_schema=False)
def list_iso_standards_alias(
    active_only: bool = Query(True),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if active_only:
        return meta_list_iso_standards(q=q, db=db)
    _ensure_seed_masters(db)
    query = db.query(IsoStandard)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (IsoStandard.standard_code.ilike(like))
            | (IsoStandard.standard_name_ko.ilike(like))
        )
    return [_iso_out(r) for r in query.order_by(IsoStandard.standard_code.asc()).all()]


@router.post("/masters/iaf-codes", status_code=status.HTTP_201_CREATED)
def create_iaf_code(
    payload: IafCodeCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    code = payload.iaf_code.strip()
    if db.query(IafCode).filter(IafCode.code == code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 IAF 코드입니다.")
    now = datetime.utcnow()
    row = IafCode(
        code=code,
        name_ko=payload.industry_name_ko.strip(),
        name_en=payload.name_en,
        description=payload.description,
        is_active=payload.is_active,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _iaf_out(row)


@router.patch("/masters/iaf-codes/{iaf_code_id}")
def update_iaf_code(
    iaf_code_id: int,
    payload: IafCodeUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    row = db.query(IafCode).filter(IafCode.id == iaf_code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="IAF 코드를 찾을 수 없습니다.")
    data = payload.model_dump(exclude_unset=True)
    if "industry_name_ko" in data:
        row.name_ko = data.pop("industry_name_ko")
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    return _iaf_out(row)


@router.post("/masters/iso-standards", status_code=status.HTTP_201_CREATED)
def create_iso_standard(
    payload: IsoStandardCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    code = payload.standard_code.strip()
    if db.query(IsoStandard).filter(IsoStandard.standard_code == code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 표준 코드입니다.")
    now = datetime.utcnow()
    row = IsoStandard(
        standard_key=(payload.standard_key or "").strip() or None,
        standard_code=code,
        standard_name_ko=payload.standard_name_ko.strip(),
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _iso_out(row)


@router.patch("/masters/iso-standards/{standard_id}")
def update_iso_standard(
    standard_id: int,
    payload: IsoStandardUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_platform_admin),
):
    row = db.query(IsoStandard).filter(IsoStandard.id == standard_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="표준을 찾을 수 없습니다.")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    return _iso_out(row)


# ---------- CB Scopes (명세 경로) ----------

@router.get("/cb/scopes", response_model=List[CbScopeOut])
def list_cb_scopes(
    status_filter: Optional[str] = Query(None, alias="status"),
    standard_id: Optional[int] = None,
    cb_id: Optional[int] = Query(None, description="platform_admin 전용"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """자사 CB 승인 Scope 목록 — 1행 = 표준1 + IAF1."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, cb_id)
    # 업로드/수정 직후 동일 세션 캐시로 누락되지 않도록 강제 갱신
    db.expire_all()
    query = (
        db.query(CbAccreditedScope)
        .options(
            joinedload(CbAccreditedScope.standard),
            joinedload(CbAccreditedScope.iaf_code),
        )
        .filter(CbAccreditedScope.cb_id == scope_cb_id)
    )
    if status_filter:
        query = query.filter(CbAccreditedScope.status == status_filter.strip().lower())
    if standard_id:
        query = query.filter(CbAccreditedScope.standard_id == standard_id)
    rows = query.order_by(CbAccreditedScope.id.desc()).all()
    return [_scope_to_out(r) for r in rows]


@router.post("/cb/scopes", response_model=CbScopeOut, status_code=status.HTTP_201_CREATED)
def create_cb_scope(
    payload: CbScopeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """단일 Scope (1개 표준 + 1개 IAF) 추가."""
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, payload.cb_id)
    row, _ = _create_scope_row(
        db,
        cb_id=scope_cb_id,
        standard_id=payload.standard_id,
        iaf_code_id=payload.iaf_code_id,
        accreditation_body=payload.accreditation_body or "KAB",
        approval_date=payload.approval_date,
        expiry_date=payload.expiry_date,
        status_val=(payload.status or "active").strip().lower(),
        allow_duplicate=False,
    )
    db.commit()
    db.refresh(row)
    db.expire_all()
    row = (
        db.query(CbAccreditedScope)
        .options(
            joinedload(CbAccreditedScope.standard),
            joinedload(CbAccreditedScope.iaf_code),
        )
        .filter(CbAccreditedScope.id == row.id)
        .first()
    )
    return _scope_to_out(row)


@router.delete("/cb/scopes/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cb_scope(
    scope_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """특정 Scope 삭제/해제."""
    _require_cb_manager(current_user)
    query = db.query(CbAccreditedScope).filter(CbAccreditedScope.id == scope_id)
    if current_user.role != UsersRole.PLATFORM_ADMIN.value:
        query = query.filter(CbAccreditedScope.cb_id == current_user.cb_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Scope를 찾을 수 없습니다.")
    db.delete(row)
    db.commit()
    return None


@router.patch("/cb/scopes/{scope_id}", response_model=CbScopeOut)
def update_cb_scope(
    scope_id: int,
    payload: CbScopeUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    _require_cb_manager(current_user)
    query = db.query(CbAccreditedScope).filter(CbAccreditedScope.id == scope_id)
    if current_user.role != UsersRole.PLATFORM_ADMIN.value:
        query = query.filter(CbAccreditedScope.cb_id == current_user.cb_id)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Scope를 찾을 수 없습니다.")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"]:
        st = data["status"].strip().lower()
        if st not in {"active", "suspended", "withdrawn"}:
            raise HTTPException(status_code=400, detail="status는 active|suspended|withdrawn 만 가능합니다.")
        data["status"] = st
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    row = (
        db.query(CbAccreditedScope)
        .options(
            joinedload(CbAccreditedScope.standard),
            joinedload(CbAccreditedScope.iaf_code),
        )
        .filter(CbAccreditedScope.id == scope_id)
        .first()
    )
    return _scope_to_out(row)


@router.post("/cb/scopes/bulk-import")
async def bulk_import_cb_scopes(
    csv_file: UploadFile = File(..., description="표준,IAF코드[,인정기구,승인일,만료일,상태]"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CSV 행별로 (표준, IAF코드)를 개별 레코드로 분리 저장.

    헤더 예시: standard_code,iaf_code,accreditation_body,approval_date,expiry_date,status
    IAF 셀에 콤마가 있으면 각각 별도 행으로 분리한다.
    """
    _require_cb_manager(current_user)
    scope_cb_id = _resolve_cb_id(current_user, None)
    _ensure_seed_masters(db)

    raw = await csv_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp949")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV 내용이 없습니다.")

    # 헤더 감지
    start = 0
    header = [c.strip().lower() for c in rows[0]]
    if any(h in header for h in ("standard_code", "표준", "iso", "iaf_code", "iaf")):
        start = 1

    created = 0
    updated = 0
    skipped = 0
    errors: List[dict] = []

    try:
        for idx, cols in enumerate(rows[start:], start=start + 1):
            if not cols or all(not str(c).strip() for c in cols):
                skipped += 1
                continue
            padded = list(cols) + [""] * max(0, 6 - len(cols))
            std_raw = str(padded[0]).strip()
            iaf_raw = str(padded[1]).strip()
            body = str(padded[2]).strip() or "KAB"
            try:
                approval = _parse_date(str(padded[3])) if padded[3] else None
                expiry = _parse_date(str(padded[4])) if padded[4] else None
            except ValueError as e:
                errors.append({"row": idx, "error": str(e)})
                continue
            status_val = (str(padded[5]).strip().lower() or "active")
            if status_val in {"정상", "active"}:
                status_val = "active"
            elif status_val in {"정지", "suspended"}:
                status_val = "suspended"
            elif status_val in {"철회", "withdrawn"}:
                status_val = "withdrawn"

            standard = _resolve_standard(db, std_raw)
            if not standard:
                errors.append({"row": idx, "error": f"표준을 찾을 수 없습니다: {std_raw}"})
                continue

            # 콤마로 묶인 IAF → 개별 레코드
            iaf_tokens = [t.strip() for t in iaf_raw.replace(";", ",").split(",") if t.strip()]
            if not iaf_tokens:
                errors.append({"row": idx, "error": "IAF 코드가 비어 있습니다."})
                continue

            for token in iaf_tokens:
                iaf = _resolve_iaf(db, token)
                if not iaf:
                    errors.append({"row": idx, "error": f"IAF 코드를 찾을 수 없습니다: {token}"})
                    continue
                try:
                    _, action = _create_scope_row(
                        db,
                        cb_id=scope_cb_id,
                        standard_id=standard.id,
                        iaf_code_id=iaf.id,
                        accreditation_body=body,
                        approval_date=approval,
                        expiry_date=expiry,
                        status_val=status_val,
                        allow_duplicate=True,
                    )
                    if action == "created":
                        created += 1
                    else:
                        updated += 1
                except HTTPException as he:
                    errors.append({"row": idx, "error": str(he.detail)})

        db.commit()
        # 커밋 확정 후 세션 캐시 비우기 → 후속 GET이 최신 행을 보도록 보장
        db.expire_all()

        # 레거시 요약 컬럼 동기화 (프로필 화면/대시보드 호환)
        cb = db.query(CertificationBodies).filter(CertificationBodies.id == scope_cb_id).first()
        if cb:
            scope_rows = (
                db.query(CbAccreditedScope)
                .options(
                    joinedload(CbAccreditedScope.standard),
                    joinedload(CbAccreditedScope.iaf_code),
                )
                .filter(
                    CbAccreditedScope.cb_id == scope_cb_id,
                    CbAccreditedScope.status == "active",
                )
                .all()
            )
            standards = sorted(
                {
                    r.standard.standard_code
                    for r in scope_rows
                    if r.standard and r.standard.standard_code
                }
            )
            iafs = sorted(
                {r.iaf_code.code for r in scope_rows if r.iaf_code and r.iaf_code.code}
            )
            cb.accredited_standards = ", ".join(standards) if standards else None
            cb.iaf_scopes = ", ".join(iafs) if iafs else None
            cb.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(cb)

        total = (
            db.query(CbAccreditedScope)
            .filter(CbAccreditedScope.cb_id == scope_cb_id)
            .count()
        )
        return {
            "message": "Scope 대량 업로드가 완료되었습니다.",
            "cb_id": scope_cb_id,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors[:50],
            "total_scopes": total,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"업로드 실패: {e}") from e


# 하위 호환 별칭
@router.get("/cb/accredited-scopes", response_model=List[CbScopeOut], include_in_schema=False)
def list_cb_accredited_scopes_alias(
    status_filter: Optional[str] = Query(None, alias="status"),
    standard_id: Optional[int] = None,
    cb_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    return list_cb_scopes(
        status_filter=status_filter,
        standard_id=standard_id,
        cb_id=cb_id,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/cb/accredited-scopes",
    response_model=CbScopeOut,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_cb_accredited_scope_alias(
    payload: CbScopeCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    return create_cb_scope(payload=payload, db=db, current_user=current_user)


@router.delete(
    "/cb/accredited-scopes/{scope_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
def delete_cb_accredited_scope_alias(
    scope_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    return delete_cb_scope(scope_id=scope_id, db=db, current_user=current_user)
