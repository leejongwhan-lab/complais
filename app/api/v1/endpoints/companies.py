"""기업(Company) 마스터 CRUD 엔드포인트."""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Companies
from app.schemas.company import CompaniesCreate, CompaniesResponse, CompaniesUpdate
from app.services.iaf_recommendation import resolve_iaf_for_company

router = APIRouter(prefix="/companies", tags=["companies"])


class MappedIafItem(BaseModel):
    iaf_code_id: int
    iaf_code: str
    industry_name_ko: str
    name_en: Optional[str] = None
    source: str


class CompanySearchResponse(BaseModel):
    id: int
    name: str
    biz_no: Optional[str] = None
    ceo_name: Optional[str] = None
    address_kr: Optional[str] = Field(default=None, validation_alias="address")
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    mapped_iaf_codes: List[MappedIafItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


def _get_company_or_404(db: Session, company_id: int) -> Companies:
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="기업을 찾을 수 없습니다.")
    return company


def _to_search_item(db: Session, row: Companies) -> CompanySearchResponse:
    hints = resolve_iaf_for_company(db, row)
    return CompanySearchResponse(
        id=row.id,
        name=row.name,
        biz_no=row.biz_no,
        ceo_name=row.ceo_name,
        address_kr=row.address,
        ksic_code=row.ksic_code,
        iaf_code=row.iaf_code,
        mapped_iaf_codes=[
            MappedIafItem(
                iaf_code_id=h.iaf_code_id,
                iaf_code=h.iaf_code,
                industry_name_ko=h.industry_name_ko,
                name_en=h.name_en,
                source=h.source,
            )
            for h in hints
        ],
    )


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


@router.get("/search", response_model=List[CompanySearchResponse])
def search_companies(
    q: Optional[str] = Query(None, min_length=2, description="기업명 또는 사업자등록번호"),
    keyword: Optional[str] = Query(None, min_length=2, description="하위 호환용 (q와 동일)"),
    db: Session = Depends(get_db),
) -> List[CompanySearchResponse]:
    """기업명/사업자번호 부분 검색 (최대 10건). KSIC→IAF 매핑 포함."""
    term = (q or keyword or "").strip()
    if len(term) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="검색어(q)를 2자 이상 입력하세요.",
        )

    results = (
        db.query(Companies)
        .filter(
            (Companies.name.ilike(f"%{term}%"))
            | (Companies.biz_no.ilike(f"%{term}%"))
        )
        .order_by(Companies.id.desc())
        .limit(10)
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="검색된 기업 정보가 없습니다. 마스터 DB를 확인해주세요.",
        )

    return [_to_search_item(db, row) for row in results]


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
    data = payload.model_dump(exclude={"ksic_codes", "iaf_codes"})
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
