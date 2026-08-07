"""Approval workflow API — 자격 승인/반려 (live auditor_qualifications)."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auditor import AuditorQualification
from app.models.enums import ApprovalStatus

router = APIRouter(prefix="/approvals", tags=["Approval Workflow"])


class QualificationApproveAction(BaseModel):
    action: str  # APPROVED | REJECTED


class QualificationResponse(BaseModel):
    id: int
    auditor_id: int
    cb_id: Optional[int] = None
    standard_code: str
    grade: str
    cert_body_name: Optional[str] = None
    cert_no: Optional[str] = None
    major_name: Optional[str] = None
    is_active: bool
    membership_id: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/pending", response_model=List[QualificationResponse])
def get_pending_qualifications(db: Session = Depends(get_db)):
    """인증기관용: 승인 대기 목록 조회 (is_active=0)."""
    return (
        db.query(AuditorQualification)
        .filter(AuditorQualification.is_active.is_(False))
        .order_by(AuditorQualification.id.desc())
        .limit(200)
        .all()
    )


@router.post("/qualifications/{qualification_id}/process", response_model=QualificationResponse)
def process_qualification_approval(
    qualification_id: int,
    action_data: QualificationApproveAction,
    db: Session = Depends(get_db),
):
    """인증기관용: 심사원 자격 승인 또는 반려 처리."""
    qual = (
        db.query(AuditorQualification)
        .filter(AuditorQualification.id == qualification_id)
        .first()
    )
    if not qual:
        raise HTTPException(status_code=404, detail="해당 자격 신청 건을 찾을 수 없습니다.")

    action = (action_data.action or "").upper()
    if action == ApprovalStatus.APPROVED.value or action == "APPROVED":
        qual.is_active = True
        qual.granted_at = qual.granted_at or datetime.utcnow().date()
        qual.updated_at = datetime.utcnow()
    elif action == ApprovalStatus.REJECTED.value or action == "REJECTED":
        qual.is_active = False
        qual.updated_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="올바르지 않은 승인 요청입니다.")

    db.commit()
    db.refresh(qual)
    return qual
