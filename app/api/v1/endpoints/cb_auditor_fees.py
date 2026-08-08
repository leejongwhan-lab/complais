"""CB — 관리기업 관계 / 역할별 일당 요율 API (목표2)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_cb_portal_user
from app.db.session import get_db
from app.models.auditor import Auditor, AuditorManagedCompanies
from app.models.cb import CbAuditorRoleRates
from app.models.company import Companies

router = APIRouter(tags=["cb-auditor-fees"])


class ManagedCompanyIn(BaseModel):
    auditor_id: int
    company_id: int
    status: str = "ACTIVE"
    note: Optional[str] = None


class ManagedCompanyOut(BaseModel):
    id: int
    auditor_id: int
    company_id: int
    cb_id: int
    assigned_at: datetime
    status: str
    note: Optional[str] = None
    auditor_name: Optional[str] = None
    company_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ManagedCompanyStatusIn(BaseModel):
    status: str = Field(..., description="ACTIVE / TRANSFERRED / INACTIVE")
    note: Optional[str] = None


class RoleRateIn(BaseModel):
    role: str = Field(..., description="lead / auditor / expert / observer / witness")
    daily_rate: int = Field(..., ge=0)
    is_active: bool = True


class RoleRateOut(BaseModel):
    id: int
    cb_id: int
    role: str
    daily_rate: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


def _cb_id(user: CurrentUser) -> int:
    if not user.cb_id:
        raise HTTPException(status_code=403, detail="CB 소속이 필요합니다.")
    return int(user.cb_id)


@router.get("/cb-auditor-managed-companies", response_model=List[ManagedCompanyOut])
def list_managed_companies(
    auditor_id: Optional[int] = None,
    company_id: Optional[int] = None,
    status: Optional[str] = "ACTIVE",
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> List[ManagedCompanyOut]:
    cb_id = _cb_id(current_user)
    q = db.query(AuditorManagedCompanies).filter(AuditorManagedCompanies.cb_id == cb_id)
    if auditor_id is not None:
        q = q.filter(AuditorManagedCompanies.auditor_id == auditor_id)
    if company_id is not None:
        q = q.filter(AuditorManagedCompanies.company_id == company_id)
    if status:
        q = q.filter(AuditorManagedCompanies.status == status.upper())
    rows = q.order_by(AuditorManagedCompanies.id.desc()).all()
    out: List[ManagedCompanyOut] = []
    for r in rows:
        auditor = db.get(Auditor, r.auditor_id)
        company = db.get(Companies, r.company_id)
        out.append(
            ManagedCompanyOut(
                id=r.id,
                auditor_id=r.auditor_id,
                company_id=r.company_id,
                cb_id=r.cb_id,
                assigned_at=r.assigned_at,
                status=r.status,
                note=r.note,
                auditor_name=auditor.name if auditor else None,
                company_name=company.name if company else None,
            )
        )
    return out


@router.post("/cb-auditor-managed-companies", response_model=ManagedCompanyOut)
def upsert_managed_company(
    payload: ManagedCompanyIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> ManagedCompanyOut:
    cb_id = _cb_id(current_user)
    if db.get(Auditor, payload.auditor_id) is None:
        raise HTTPException(status_code=404, detail="심사원을 찾을 수 없습니다.")
    if db.get(Companies, payload.company_id) is None:
        raise HTTPException(status_code=404, detail="기업을 찾을 수 없습니다.")

    now = datetime.now()
    status_val = (payload.status or "ACTIVE").strip().upper()
    row = (
        db.query(AuditorManagedCompanies)
        .filter(
            AuditorManagedCompanies.auditor_id == payload.auditor_id,
            AuditorManagedCompanies.company_id == payload.company_id,
            AuditorManagedCompanies.cb_id == cb_id,
        )
        .first()
    )
    if row is None:
        row = AuditorManagedCompanies(
            auditor_id=payload.auditor_id,
            company_id=payload.company_id,
            cb_id=cb_id,
            assigned_at=now,
            status=status_val,
            note=payload.note,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.status = status_val
        row.note = payload.note
        row.updated_at = now
        if status_val == "ACTIVE":
            row.assigned_at = now
    db.commit()
    db.refresh(row)
    auditor = db.get(Auditor, row.auditor_id)
    company = db.get(Companies, row.company_id)
    return ManagedCompanyOut(
        id=row.id,
        auditor_id=row.auditor_id,
        company_id=row.company_id,
        cb_id=row.cb_id,
        assigned_at=row.assigned_at,
        status=row.status,
        note=row.note,
        auditor_name=auditor.name if auditor else None,
        company_name=company.name if company else None,
    )


@router.patch("/cb-auditor-managed-companies/{row_id}", response_model=ManagedCompanyOut)
def patch_managed_company(
    row_id: int,
    payload: ManagedCompanyStatusIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> ManagedCompanyOut:
    cb_id = _cb_id(current_user)
    row = db.get(AuditorManagedCompanies, row_id)
    if row is None or int(row.cb_id) != cb_id:
        raise HTTPException(status_code=404, detail="관리기업 관계를 찾을 수 없습니다.")
    row.status = payload.status.strip().upper()
    if payload.note is not None:
        row.note = payload.note
    row.updated_at = datetime.now()
    db.commit()
    db.refresh(row)
    auditor = db.get(Auditor, row.auditor_id)
    company = db.get(Companies, row.company_id)
    return ManagedCompanyOut(
        id=row.id,
        auditor_id=row.auditor_id,
        company_id=row.company_id,
        cb_id=row.cb_id,
        assigned_at=row.assigned_at,
        status=row.status,
        note=row.note,
        auditor_name=auditor.name if auditor else None,
        company_name=company.name if company else None,
    )


@router.get("/cb-auditor-role-rates", response_model=List[RoleRateOut])
def list_role_rates(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> List[CbAuditorRoleRates]:
    cb_id = _cb_id(current_user)
    return (
        db.query(CbAuditorRoleRates)
        .filter(CbAuditorRoleRates.cb_id == cb_id)
        .order_by(CbAuditorRoleRates.role.asc())
        .all()
    )


@router.put("/cb-auditor-role-rates/{role}", response_model=RoleRateOut)
def upsert_role_rate(
    role: str,
    payload: RoleRateIn,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> CbAuditorRoleRates:
    cb_id = _cb_id(current_user)
    role_key = (payload.role or role).strip().lower()
    if role_key not in {"lead", "auditor", "expert", "observer", "witness"}:
        raise HTTPException(status_code=400, detail="허용되지 않은 role 입니다.")
    now = datetime.now()
    row = (
        db.query(CbAuditorRoleRates)
        .filter(CbAuditorRoleRates.cb_id == cb_id, CbAuditorRoleRates.role == role_key)
        .first()
    )
    if row is None:
        row = CbAuditorRoleRates(
            cb_id=cb_id,
            role=role_key,
            daily_rate=int(payload.daily_rate),
            is_active=bool(payload.is_active),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.daily_rate = int(payload.daily_rate)
        row.is_active = bool(payload.is_active)
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
