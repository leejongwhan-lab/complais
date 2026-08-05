"""인증기관(CB) 마스터 CRUD 엔드포인트.

요청의 CBEntity 개념을 기존 CertificationBodies(`certification_bodies`)에 매핑한다.
식별자는 요청대로 `code`(기관 이니셜 코드, 예: KAB_CB_01)를 경로 파라미터로 사용한다.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.cb import CertificationBodies
from app.schemas.cb import CertificationBodiesResponse, CertificationBodiesUpdate

router = APIRouter(prefix="/cb-entities", tags=["CB Entities"])


class CBEntityCreate(BaseModel):
    """인증기관 신규 등록 — 필수 최소 필드 + 확장 필드."""
    code: str = Field(..., description="기관 이니셜 코드 (예: KAB_CB_01)")
    name: str
    name_en: Optional[str] = None
    cb_type: str = Field(default="certification", description="기관유형")
    cb_initial: Optional[str] = None
    accreditation: Optional[str] = None
    address: Optional[str] = None
    tel: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    ceo_name: Optional[str] = None
    biz_no: Optional[str] = None
    corp_no: Optional[str] = None
    fax: Optional[str] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    fee_per_md: Decimal = Decimal("0")
    fee_travel: Decimal = Decimal("0")
    fee_cert: Decimal = Decimal("0")
    max_consecutive: int = 0
    impartiality_cycle_months: int = 0
    reg_no: Optional[str] = None
    is_active: bool = True
    accreditation_region: Optional[str] = None
    accreditation_country: Optional[str] = None
    accreditation_body: Optional[str] = None
    stamp_url: Optional[str] = None
    accreditation_no: Optional[str] = None
    accredited_standards: Optional[str] = None
    iaf_scopes: Optional[str] = None
    expire_date: Optional[str] = None
    status: Optional[str] = "정상"
    evaluation_score: Optional[Decimal] = None
    tax_email: Optional[str] = None


class CBEntityResponse(CertificationBodiesResponse):
    """목록/상세 응답 — CertificationBodiesResponse 재사용."""
    model_config = ConfigDict(from_attributes=True)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _get_cb_by_code_or_404(db: Session, code: str) -> CertificationBodies:
    cb = db.query(CertificationBodies).filter(CertificationBodies.code == code).first()
    if cb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="인증기관을 찾을 수 없습니다.")
    return cb


@router.get("", response_model=List[CBEntityResponse])
def list_cb_entities(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(None, description="기관명/코드 검색"),
    status_filter: Optional[str] = Query(None, alias="status", description="정상/정지/취소"),
    db: Session = Depends(get_db),
) -> List[CertificationBodies]:
    """인증기관 마스터 목록/검색 조회."""
    query = db.query(CertificationBodies)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (CertificationBodies.name.ilike(like))
            | (CertificationBodies.name_en.ilike(like))
            | (CertificationBodies.code.ilike(like))
        )
    if status_filter:
        query = query.filter(CertificationBodies.status == status_filter)
    return query.order_by(CertificationBodies.id.desc()).offset(skip).limit(limit).all()


@router.get("/{code}", response_model=CBEntityResponse)
def get_cb_entity(code: str, db: Session = Depends(get_db)) -> CertificationBodies:
    return _get_cb_by_code_or_404(db, code)


@router.post("", response_model=CBEntityResponse, status_code=status.HTTP_201_CREATED)
def create_cb_entity(payload: CBEntityCreate, db: Session = Depends(get_db)) -> CertificationBodies:
    """인증기관 신규 등록."""
    existing = db.query(CertificationBodies).filter(CertificationBodies.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 기관 코드입니다.")

    now = datetime.now()
    data = payload.model_dump()
    cb = CertificationBodies(
        **{k: _serialize(v) for k, v in data.items()},
        created_at=now,
        updated_at=now,
    )
    db.add(cb)
    db.commit()
    db.refresh(cb)
    return cb


@router.put("/{code}", response_model=CBEntityResponse)
def update_cb_entity(
    code: str,
    payload: CertificationBodiesUpdate,
    db: Session = Depends(get_db),
) -> CertificationBodies:
    cb = _get_cb_by_code_or_404(db, code)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"created_at", "updated_at", "code"}:
            continue
        setattr(cb, field, _serialize(value))
    cb.updated_at = datetime.now()
    db.commit()
    db.refresh(cb)
    return cb


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cb_entity(code: str, db: Session = Depends(get_db)) -> None:
    cb = _get_cb_by_code_or_404(db, code)
    db.delete(cb)
    db.commit()
