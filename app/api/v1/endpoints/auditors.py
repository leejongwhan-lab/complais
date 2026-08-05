"""심사원(Auditor) 마스터 CRUD 및 CB 소속 조회 API."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cb_scope import is_platform_admin
from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.auditor import Auditor, AuditorCbMemberships
from app.schemas.auditor import AuditorCbMembershipsResponse
from app.schemas.auditor_profile import (
    AuditorProfileCreate,
    AuditorProfileResponse,
    AuditorProfileUpdate,
)

router = APIRouter(prefix="/auditors", tags=["Auditors"])

# 라이브 auditors.status ENUM('active','leave','suspended') 과의 한국어 표기 매핑
_STATUS_MAP = {
    "활성": "active",
    "휴면": "leave",
    "정지": "suspended",
    "active": "active",
    "leave": "leave",
    "suspended": "suspended",
}


def _normalize_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return _STATUS_MAP.get(value, value)


def _get_auditor_or_404(db: Session, auditor_id: int) -> Auditor:
    auditor = db.get(Auditor, auditor_id)
    if auditor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="심사원을 찾을 수 없습니다.")
    return auditor


@router.get("", response_model=List[AuditorProfileResponse])
def list_auditors(
    skip: int = 0,
    limit: int = 100,
    q: Optional[str] = Query(None, description="성명/이메일/연락처 검색"),
    status_filter: Optional[str] = Query(None, alias="status", description="활성/휴면/정지"),
    primary_cb_id: Optional[int] = None,
    db: Session = Depends(get_db),
) -> List[Auditor]:
    """심사원 마스터 목록/검색 조회."""
    query = db.query(Auditor)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Auditor.name.ilike(like))
            | (Auditor.email.ilike(like))
            | (Auditor.phone.ilike(like))
        )
    if status_filter:
        query = query.filter(Auditor.status == (_normalize_status(status_filter) or status_filter))
    if primary_cb_id is not None:
        query = query.filter(Auditor.primary_cb_id == primary_cb_id)
    return query.order_by(Auditor.id.desc()).offset(skip).limit(limit).all()


@router.get("/cb-memberships", response_model=List[AuditorCbMembershipsResponse])
def get_cb_auditors(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> List[AuditorCbMemberships]:
    """로그인한 인증원(CB) 소속 심사원 목록을 조회합니다."""
    query = db.query(AuditorCbMemberships)
    if not is_platform_admin(current_user):
        query = query.filter(AuditorCbMemberships.cb_id == current_user.cb_id)
    return query.order_by(AuditorCbMemberships.id.desc()).all()


@router.get("/{auditor_id}", response_model=AuditorProfileResponse)
def get_auditor(auditor_id: int, db: Session = Depends(get_db)) -> Auditor:
    return _get_auditor_or_404(db, auditor_id)


@router.post("", response_model=AuditorProfileResponse, status_code=status.HTTP_201_CREATED)
def create_auditor(payload: AuditorProfileCreate, db: Session = Depends(get_db)) -> Auditor:
    """심사원 신규 등록. AUTO_INCREMENT가 10001부터 채번된다."""
    now = datetime.now()
    data = payload.model_dump()
    # 라이브 DB NOT NULL / ENUM 기본값 보정
    data["status"] = _normalize_status(data.get("status")) or "active"
    data.setdefault("grade", "trainee")
    data["grade"] = data.get("grade") or "trainee"
    data["employment_type"] = data.get("employment_type") or "parttime"
    data["is_freelance"] = bool(data.get("is_freelance") or False)
    data["is_active"] = True if data.get("is_active") is None else data["is_active"]
    data["contract_type"] = data.get("contract_type") or "per_day"
    data["daily_rate"] = data.get("daily_rate") if data.get("daily_rate") is not None else 0.0
    data["fee_ratio"] = data.get("fee_ratio") if data.get("fee_ratio") is not None else 0.0
    data["monthly_fee"] = data.get("monthly_fee") if data.get("monthly_fee") is not None else 0.0
    if not data.get("email"):
        raise HTTPException(status_code=400, detail="email은 필수입니다.")

    auditor = Auditor(**data, created_at=now, updated_at=now)
    db.add(auditor)
    db.commit()
    db.refresh(auditor)
    return auditor


@router.put("/{auditor_id}", response_model=AuditorProfileResponse)
def update_auditor(
    auditor_id: int,
    payload: AuditorProfileUpdate,
    db: Session = Depends(get_db),
) -> Auditor:
    auditor = _get_auditor_or_404(db, auditor_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "status":
            value = _normalize_status(value)
        setattr(auditor, field, value)
    auditor.updated_at = datetime.now()
    db.commit()
    db.refresh(auditor)
    return auditor


@router.delete("/{auditor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_auditor(auditor_id: int, db: Session = Depends(get_db)) -> None:
    # ORM cascade로 깨진 레거시 연관 테이블(auditor_qualifications 등)을 로드하지 않도록
    # 존재 확인 후 SQL DELETE로 직접 제거한다.
    exists = db.query(Auditor.id).filter(Auditor.id == auditor_id).first()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="심사원을 찾을 수 없습니다.")
    db.query(Auditor).filter(Auditor.id == auditor_id).delete(synchronize_session=False)
    db.commit()
