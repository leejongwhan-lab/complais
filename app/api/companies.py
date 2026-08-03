"""Company CRUD endpoints."""
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.company import Companies
from app.schemas.company import CompaniesCreate, CompaniesResponse, CompaniesUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


@router.get("", response_model=list[CompaniesResponse])
def list_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[Companies]:
    return db.query(Companies).offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompaniesResponse)
def get_company(company_id: int, db: Session = Depends(get_db)) -> Companies:
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.post("", response_model=CompaniesResponse, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompaniesCreate, db: Session = Depends(get_db)) -> Companies:
    now = datetime.now()
    data = payload.model_dump(exclude={"created_at", "updated_at"})
    company = Companies(**{k: _serialize(v) for k, v in data.items()}, created_at=now, updated_at=now)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompaniesResponse)
def update_company(
    company_id: int,
    payload: CompaniesUpdate,
    db: Session = Depends(get_db),
) -> Companies:
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"created_at", "updated_at"}:
            continue
        setattr(company, field, _serialize(value))
    company.updated_at = datetime.now()

    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db)) -> None:
    company = db.get(Companies, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    db.delete(company)
    db.commit()
