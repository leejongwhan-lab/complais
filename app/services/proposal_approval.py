# DEPRECATED — 진짜 경로는 certification_applications + cb_cert_applications.py (enterprise_cert_applications). 삭제 예정(정리 후보). 오늘 작업에서 사용 금지.
"""제안서 결재 승인/반려 처리 (FE processProposalApproval 와 동일)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import ProposalStatus, can_transition_proposal_status
from app.models.proposal_flow import ProposalFlow
from app.schemas.proposal import ProposalApprovalFlow


logger = logging.getLogger(__name__)

ApprovalAction = Literal["APPROVE", "REJECT"]
ApprovalRole = Literal["REVIEWER", "APPROVER"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _default_approval_line() -> Dict[str, Any]:
    return {
        "reviewerId": "",
        "approverId": "",
        "reviewerComment": None,
        "reviewedAt": None,
        "approverComment": None,
        "approvedAt": None,
    }


def flow_to_dto(row: ProposalFlow) -> ProposalApprovalFlow:
    line_raw = row.approval_line_json or _default_approval_line()
    auditors_raw = row.assigned_auditors_json or []
    return ProposalApprovalFlow.model_validate(
        {
            "proposalId": row.proposal_id,
            "currentStatus": row.current_status,
            "calculationSummary": {
                "baseMD": float(row.base_md or 0),
                "netAdjustmentRate": float(row.net_adjustment_rate or 0),
                "finalMD": float(row.final_md or 0),
                "totalAmount": float(row.total_amount or 0),
                "vat": float(row.vat or 0),
                "grandTotal": float(row.grand_total or 0),
            },
            "assignedAuditors": auditors_raw,
            "approvalLine": line_raw,
        }
    )


def apply_dto_to_row(row: ProposalFlow, dto: ProposalApprovalFlow) -> None:
    row.current_status = (
        dto.current_status.value
        if isinstance(dto.current_status, ProposalStatus)
        else str(dto.current_status)
    )
    s = dto.calculation_summary
    row.base_md = s.base_md
    row.net_adjustment_rate = s.net_adjustment_rate
    row.final_md = s.final_md
    row.total_amount = s.total_amount
    row.vat = s.vat
    row.grand_total = s.grand_total
    row.assigned_auditors_json = [
        a.model_dump(by_alias=True) for a in dto.assigned_auditors
    ]
    row.approval_line_json = dto.approval_line.model_dump(by_alias=True, mode="json")
    row.updated_at = _utcnow()


def get_proposal_by_id(db: Session, proposal_id: str) -> ProposalFlow:
    row = db.get(ProposalFlow, proposal_id)
    if not row:
        raise HTTPException(status_code=404, detail="제안서를 찾을 수 없습니다.")
    return row


def save_proposal(db: Session, row: ProposalFlow) -> ProposalFlow:
    row.updated_at = _utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def generate_proposal_pdf(db: Session, proposal_id: str) -> None:
    """PDF 자동 생성 및 발송 트리거 (스텁 — 실제 렌더러 연동 전)."""
    row = get_proposal_by_id(db, proposal_id)
    row.pdf_generated = True
    row.pdf_path = f"/generated/proposals/{proposal_id}.pdf"
    row.note = (row.note or "") + f"\n[PDF] generated at {_utcnow().isoformat()}"
    db.add(row)
    db.commit()
    logger.info("proposal PDF stub generated: %s", proposal_id)


def notify_owner_revision_required(row: ProposalFlow, comment: Optional[str]) -> None:
    """작성자(담당자) 보완 요청 알림 (스텁)."""
    logger.info(
        "revision notice proposal=%s owner=%s comment=%s",
        row.proposal_id,
        row.owner_user_id,
        comment,
    )


def process_proposal_approval(
    db: Session,
    proposal_id: str,
    action: ApprovalAction,
    user_id: str,
    user_role: ApprovalRole,
    comment: Optional[str] = None,
) -> ProposalApprovalFlow:
    """결재 승인/반려 처리.

    REJECT → REJECTED + 보완 알림
    REVIEWER APPROVE → reviewedAt 기록, PENDING_APPROVAL 유지(최종 승인자 대기)
    APPROVER APPROVE → APPROVED + PDF 생성 트리거
    """
    row = get_proposal_by_id(db, proposal_id)
    line = dict(row.approval_line_json or _default_approval_line())
    current = row.current_status

    if action == "REJECT":
        target = ProposalStatus.REJECTED.value
        if current != target and not can_transition_proposal_status(current, target):
            # PENDING_APPROVAL → REJECTED 허용; AUDITOR_ASSIGNED 이후도 반려 가능하도록 완화
            if current not in {
                ProposalStatus.PENDING_APPROVAL.value,
                ProposalStatus.AUDITOR_ASSIGNED.value,
                ProposalStatus.COST_APPLIED.value,
                ProposalStatus.MD_CALCULATED.value,
            }:
                raise HTTPException(
                    status_code=400,
                    detail=f"현재 상태({current})에서 반려할 수 없습니다.",
                )
        row.current_status = target
        if user_role == "REVIEWER":
            line["reviewerComment"] = comment
            line["reviewerId"] = line.get("reviewerId") or user_id
        else:
            line["approverComment"] = comment
            line["approverId"] = line.get("approverId") or user_id
            # 스펙 예시와 호환: reviewerComment 에도 남김
            if not line.get("reviewerComment"):
                line["reviewerComment"] = comment
        row.approval_line_json = line
        save_proposal(db, row)
        notify_owner_revision_required(row, comment)
        return flow_to_dto(row)

    # APPROVE
    if user_role == "REVIEWER":
        line["reviewedAt"] = _utcnow().isoformat()
        line["reviewerComment"] = comment
        line["reviewerId"] = line.get("reviewerId") or user_id
        # 최종 승인자 대기
        row.current_status = ProposalStatus.PENDING_APPROVAL.value
        row.approval_line_json = line
        save_proposal(db, row)
        return flow_to_dto(row)

    if user_role == "APPROVER":
        line["approvedAt"] = _utcnow().isoformat()
        line["approverComment"] = comment
        line["approverId"] = line.get("approverId") or user_id
        row.current_status = ProposalStatus.APPROVED.value
        row.approval_line_json = line
        save_proposal(db, row)
        generate_proposal_pdf(db, proposal_id)
        row = get_proposal_by_id(db, proposal_id)
        return flow_to_dto(row)

    raise HTTPException(status_code=400, detail="userRole 이 올바르지 않습니다.")
