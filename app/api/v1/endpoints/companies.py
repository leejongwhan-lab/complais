"""기업(Company) 마스터 CRUD 엔드포인트."""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Companies
from app.schemas.company import CompaniesCreate, CompaniesResponse, CompaniesUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _get_company_or_404(db: Session, company_id: int) -> Companies:
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기업을 찾을 수 없습니다.")
    return company


@router.get("", response_model=List[CompaniesResponse])
def list_companies(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(None, description="기업명/사업자번호 검색"),
    status_filter: Optional[str] = Query(None, alias="status", description="정상/휴업/폐업/인증취소"),
    biz_no: Optional[str] = Query(None, description="사업자등록번호 정확 일치"),
    db: Session = Depends(get_db),
) -> List[Companies]:
    """기업 마스터 목록/검색 조회."""
    query = db.query(Companies)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Companies.name.ilike(like))
            | (Companies.name_en.ilike(like))
            | (Companies.biz_no.ilike(like))
        )
    if status_filter:
        query = query.filter(Companies.status == status_filter)
    if biz_no:
        query = query.filter(Companies.biz_no == biz_no)
    return query.order_by(Companies.id.desc()).offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompaniesResponse)
def get_company(company_id: int, db: Session = Depends(get_db)) -> Companies:
    return _get_company_or_404(db, company_id)


@router.post("", response_model=CompaniesResponse, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompaniesCreate, db: Session = Depends(get_db)) -> Companies:
    """기업 신규 등록. AUTO_INCREMENT가 100001부터 채번된다."""
    if payload.biz_no:
        existing = db.query(Companies).filter(Companies.biz_no == payload.biz_no).first()
        if existing:
            raise HTTPException(status_code=400, detail="이미 등록된 사업자등록번호입니다.")

    now = datetime.now()
    data = payload.model_dump()
    company = Companies(
        **{k: _serialize(v) for k, v in data.items()},
        created_at=now,
        updated_at=now,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.put("/{company_id}", response_model=CompaniesResponse)
def update_company(
    company_id: int,
    payload: CompaniesUpdate,
    db: Session = Depends(get_db),
) -> Companies:
    company = _get_company_or_404(db, company_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"created_at", "updated_at"}:
            continue
        setattr(company, field, _serialize(value))
    company.updated_at = datetime.now()
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompaniesResponse)
def patch_company(
    company_id: int,
    payload: CompaniesUpdate,
    db: Session = Depends(get_db),
) -> Companies:
    """하위 호환용 PATCH (PUT과 동일 동작)."""
    return update_company(company_id, payload, db)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db)) -> None:
    company = _get_company_or_404(db, company_id)
    db.delete(company)
    db.commit()
