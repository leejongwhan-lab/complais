"""Certification application CRUD endpoints."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.certification import CertificationApplications
from app.schemas.certification import (
    CertificationApplicationsCreate,
    CertificationApplicationsResponse,
    CertificationApplicationsUpdate,
)

router = APIRouter(prefix="/certification-applications", tags=["certification-applications"])


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


@router.get("", response_model=list[CertificationApplicationsResponse])
def list_applications(
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> list[CertificationApplications]:
    query = db.query(CertificationApplications)
    if company_id is not None:
        query = query.filter(CertificationApplications.company_id == company_id)
    return query.offset(skip).limit(limit).all()


@router.get("/{application_id}", response_model=CertificationApplicationsResponse)
def get_application(application_id: int, db: Session = Depends(get_db)) -> CertificationApplications:
    application = db.get(CertificationApplications, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.post("", response_model=CertificationApplicationsResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: CertificationApplicationsCreate,
    db: Session = Depends(get_db),
) -> CertificationApplications:
    now = datetime.now()
    data = payload.model_dump(exclude={"created_at", "updated_at"})
    application = CertificationApplications(
        **{k: _serialize(v) for k, v in data.items()},
        created_at=now,
        updated_at=now,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}", response_model=CertificationApplicationsResponse)
def update_application(
    application_id: int,
    payload: CertificationApplicationsUpdate,
    db: Session = Depends(get_db),
) -> CertificationApplications:
    application = db.get(CertificationApplications, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"created_at", "updated_at"}:
            continue
        setattr(application, field, _serialize(value))
    application.updated_at = datetime.now()

    db.commit()
    db.refresh(application)
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(application_id: int, db: Session = Depends(get_db)) -> None:
    application = db.get(CertificationApplications, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    db.delete(application)
    db.commit()
