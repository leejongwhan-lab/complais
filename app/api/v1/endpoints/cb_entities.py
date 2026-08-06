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
from app.models.cb import CertificationBodies, CbOperationalRules
from app.schemas.cb import (
    CertificationBodiesResponse,
    CertificationBodiesUpdate,
    CbOperationalRulesResponse,
    CbOperationalRulesUpdate,
)

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
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_path: Optional[str] = None
    intro: Optional[str] = None
    owner_user_id: Optional[int] = None
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
    max_consecutive: int = 3
    impartiality_cycle_months: int = 12
    doc_rule_contract: Optional[str] = "CB-QE-{YYMMDD}-{SEQ3}"
    doc_rule_report: Optional[str] = None
    doc_rule_ncr: Optional[str] = None
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


def _sync_legacy_fee_columns(cb: CertificationBodies, rules: CbOperationalRules) -> None:
    """하위 호환: certification_bodies 레거시 수수료/문서 컬럼 동기화."""
    cb.doc_rule_contract = rules.doc_rule_contract
    cb.doc_rule_report = rules.doc_rule_report
    cb.doc_rule_ncr = rules.doc_rule_ncr
    cb.fee_per_md = Decimal(rules.fee_per_md or 0)
    cb.fee_travel = Decimal(rules.fee_travel or 0)
    cb.fee_cert = Decimal(rules.fee_cert or 0)
    cb.max_consecutive = rules.max_consecutive_audits or 3
    cb.impartiality_cycle_months = rules.impartiality_cycle_months or 12


def _ensure_operational_rules(db: Session, cb: CertificationBodies) -> CbOperationalRules:
    rules = db.query(CbOperationalRules).filter(CbOperationalRules.cb_id == cb.id).first()
    if rules:
        return rules
    now = datetime.now()
    rules = CbOperationalRules(
        cb_id=cb.id,
        doc_rule_contract=cb.doc_rule_contract or "CB-QE-{YYMMDD}-{SEQ3}",
        doc_rule_report=cb.doc_rule_report,
        doc_rule_ncr=cb.doc_rule_ncr,
        fee_per_md=int(cb.fee_per_md or 0),
        fee_travel=int(cb.fee_travel or 0),
        fee_cert=int(cb.fee_cert or 0),
        max_consecutive_audits=cb.max_consecutive or 3,
        impartiality_cycle_months=cb.impartiality_cycle_months or 12,
        created_at=now,
        updated_at=now,
    )
    db.add(rules)
    db.flush()
    return rules


@router.post("", response_model=CBEntityResponse, status_code=status.HTTP_201_CREATED)
def create_cb_entity(payload: CBEntityCreate, db: Session = Depends(get_db)) -> CertificationBodies:
    """인증기관 신규 등록 + 기본 운용규칙 생성."""
    existing = db.query(CertificationBodies).filter(CertificationBodies.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 존재하는 기관 코드입니다.")

    now = datetime.now()
    data = payload.model_dump()
    # phone 미입력 시 tel 사용
    if not data.get("phone") and data.get("tel"):
        data["phone"] = data["tel"]
    if not data.get("tel") and data.get("phone"):
        data["tel"] = data["phone"]

    cb = CertificationBodies(
        **{k: _serialize(v) for k, v in data.items()},
        created_at=now,
        updated_at=now,
    )
    db.add(cb)
    db.flush()

    rules = CbOperationalRules(
        cb_id=cb.id,
        doc_rule_contract=payload.doc_rule_contract or "CB-QE-{YYMMDD}-{SEQ3}",
        doc_rule_report=payload.doc_rule_report,
        doc_rule_ncr=payload.doc_rule_ncr,
        fee_per_md=int(payload.fee_per_md or 0),
        fee_travel=int(payload.fee_travel or 0),
        fee_cert=int(payload.fee_cert or 0),
        max_consecutive_audits=payload.max_consecutive or 3,
        impartiality_cycle_months=payload.impartiality_cycle_months or 12,
        created_at=now,
        updated_at=now,
    )
    db.add(rules)
    _sync_legacy_fee_columns(cb, rules)
    from app.services.cb_billing import ensure_default_cb_contract

    ensure_default_cb_contract(db, cb, year=now.year)
    db.commit()
    db.refresh(cb)
    return cb


@router.put("/{code}", response_model=CBEntityResponse)
def update_cb_entity(
    code: str,
    payload: CertificationBodiesUpdate,
    db: Session = Depends(get_db),
) -> CertificationBodies:
    from app.core.validators import sanitize_contact_fields

    cb = _get_cb_by_code_or_404(db, code)
    data = payload.model_dump(exclude_unset=True)
    cleaned = sanitize_contact_fields(
        biz_no=data.get("biz_no") if "biz_no" in data else None,
        tel=data.get("tel") if "tel" in data else None,
        phone=data.get("phone") if "phone" in data else None,
        email=data.get("email") if "email" in data else None,
        website=data.get("website") if "website" in data else None,
    )
    data.update(cleaned)
    for field, value in data.items():
        if field in {"created_at", "updated_at", "code"}:
            continue
        setattr(cb, field, _serialize(value))

    # phone/tel 상호 보정
    if "phone" in data and data["phone"] and not data.get("tel"):
        cb.tel = data["phone"]
    if "tel" in data and data["tel"] and not data.get("phone"):
        cb.phone = data["tel"]

    # 레거시 수수료 필드가 직접 수정되면 operational_rules에도 반영
    fee_fields = {
        "doc_rule_contract",
        "doc_rule_report",
        "doc_rule_ncr",
        "fee_per_md",
        "fee_travel",
        "fee_cert",
        "max_consecutive",
        "impartiality_cycle_months",
    }
    if fee_fields.intersection(data.keys()):
        rules = _ensure_operational_rules(db, cb)
        if "doc_rule_contract" in data:
            rules.doc_rule_contract = data["doc_rule_contract"]
        if "doc_rule_report" in data:
            rules.doc_rule_report = data["doc_rule_report"]
        if "doc_rule_ncr" in data:
            rules.doc_rule_ncr = data["doc_rule_ncr"]
        if "fee_per_md" in data:
            rules.fee_per_md = int(data["fee_per_md"] or 0)
        if "fee_travel" in data:
            rules.fee_travel = int(data["fee_travel"] or 0)
        if "fee_cert" in data:
            rules.fee_cert = int(data["fee_cert"] or 0)
        if "max_consecutive" in data:
            rules.max_consecutive_audits = int(data["max_consecutive"] or 3)
        if "impartiality_cycle_months" in data:
            rules.impartiality_cycle_months = int(data["impartiality_cycle_months"] or 12)
        rules.updated_at = datetime.now()

    cb.updated_at = datetime.now()
    db.commit()
    db.refresh(cb)
    return cb


@router.get("/{code}/operational-rules", response_model=CbOperationalRulesResponse)
def get_cb_operational_rules(code: str, db: Session = Depends(get_db)) -> CbOperationalRules:
    """CB 운용/수수료 규칙 조회 (없으면 레거시 값으로 생성)."""
    cb = _get_cb_by_code_or_404(db, code)
    rules = _ensure_operational_rules(db, cb)
    db.commit()
    db.refresh(rules)
    return rules


@router.put("/{code}/operational-rules", response_model=CbOperationalRulesResponse)
def update_cb_operational_rules(
    code: str,
    payload: CbOperationalRulesUpdate,
    db: Session = Depends(get_db),
) -> CbOperationalRules:
    """CB 운용/수수료 규칙 갱신 + 레거시 컬럼 동기화."""
    cb = _get_cb_by_code_or_404(db, code)
    rules = _ensure_operational_rules(db, cb)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rules, field, value)
    rules.updated_at = datetime.now()
    _sync_legacy_fee_columns(cb, rules)
    cb.updated_at = datetime.now()
    db.commit()
    db.refresh(rules)
    return rules


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cb_entity(code: str, db: Session = Depends(get_db)) -> None:
    cb = _get_cb_by_code_or_404(db, code)
    db.delete(cb)
    db.commit()
