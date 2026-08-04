"""Auditor management API — 심사원 조회."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auditor import Auditor
from app.schemas.auditor import AuditorDetailResponse

router = APIRouter(prefix="/auditors", tags=["Auditors"])


@router.get("/{auditor_id}", response_model=AuditorDetailResponse)
def get_auditor_detail(auditor_id: int, db: Session = Depends(get_db)):
    # joinedload를 제거하고 기본 쿼리로 안전하게 조회
    auditor = db.query(Auditor).filter(Auditor.id == auditor_id).first()

    if not auditor:
        raise HTTPException(status_code=404, detail="심사원을 찾을 수 없습니다.")

    return auditor
