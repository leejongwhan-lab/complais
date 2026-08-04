"""Approval workflow API — 자격 승인/반려."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auditor import AuditorQualification
from app.models.enums import ApprovalStatus
from app.schemas.auditor import QualificationApproveAction, QualificationResponse

router = APIRouter(prefix="/approvals", tags=["Approval Workflow"])


@router.get("/pending", response_model=List[QualificationResponse])
def get_pending_qualifications(db: Session = Depends(get_db)):
    """인증기관용: 승인 대기 목록 조회."""
    return (
        db.query(AuditorQualification)
        .filter(AuditorQualification.approval_status == ApprovalStatus.PENDING.value)
        .all()
    )


@router.post("/qualifications/{qualification_id}/process", response_model=QualificationResponse)
def process_qualification_approval(
    qualification_id: int,
    action_data: QualificationApproveAction,
    approved_by: str = "cb_admin",  # 실환경에서는 JWT에서 담당자 추출
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

    if qual.approval_status != ApprovalStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="이미 처리된 승인 건입니다.")

    if action_data.action == ApprovalStatus.APPROVED:
        qual.approval_status = ApprovalStatus.APPROVED.value
        qual.approved_by = approved_by
    elif action_data.action == ApprovalStatus.REJECTED:
        qual.approval_status = ApprovalStatus.REJECTED.value
        qual.approved_by = approved_by
    else:
        raise HTTPException(status_code=400, detail="올바르지 않은 승인 요청입니다.")

    db.commit()
    db.refresh(qual)
    return qual
