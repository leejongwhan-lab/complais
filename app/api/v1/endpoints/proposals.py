"""제안서 결재 플로우 API."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_cb_scope
from app.core.security import CurrentUser
from app.models.proposal_flow import ProposalFlow
from app.schemas.proposal import ProposalApprovalFlow
from app.services.proposal_approval import (
    flow_to_dto,
    get_proposal_by_id,
    process_proposal_approval,
    save_proposal,
)

router = APIRouter(prefix="/proposals", tags=["Proposals"])

DDL = """
CREATE TABLE IF NOT EXISTS proposal_flows (
  proposal_id VARCHAR(64) NOT NULL,
  current_status VARCHAR(40) NOT NULL DEFAULT 'DRAFT',
  base_md DECIMAL(12,2) NOT NULL DEFAULT 0,
  net_adjustment_rate DECIMAL(6,2) NOT NULL DEFAULT 0,
  final_md DECIMAL(12,2) NOT NULL DEFAULT 0,
  total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
  vat DECIMAL(15,2) NOT NULL DEFAULT 0,
  grand_total DECIMAL(15,2) NOT NULL DEFAULT 0,
  assigned_auditors_json JSON NOT NULL,
  approval_line_json JSON NOT NULL,
  owner_user_id VARCHAR(64) NULL,
  cb_id INT NULL,
  company_id INT NULL,
  pdf_generated TINYINT(1) NOT NULL DEFAULT 0,
  pdf_path VARCHAR(512) NULL,
  dispatched_at DATETIME NULL,
  created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NULL,
  note TEXT NULL,
  PRIMARY KEY (proposal_id),
  KEY idx_pf_status (current_status),
  KEY idx_pf_cb (cb_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def _ensure_schema(db: Session) -> None:
    db.execute(text(DDL))
    db.commit()


class ProcessApprovalRequest(BaseModel):
    action: Literal["APPROVE", "REJECT"]
    user_role: Literal["REVIEWER", "APPROVER"] = Field(..., alias="userRole")
    comment: Optional[str] = None
    user_id: Optional[str] = Field(None, alias="userId")

    class Config:
        populate_by_name = True


class UpsertProposalFlowRequest(ProposalApprovalFlow):
    owner_user_id: Optional[str] = Field(None, alias="ownerUserId")
    cb_id: Optional[int] = Field(None, alias="cbId")
    company_id: Optional[int] = Field(None, alias="companyId")

    class Config:
        populate_by_name = True


@router.get("/{proposal_id}/approval-flow", response_model=ProposalApprovalFlow)
def get_approval_flow(
    proposal_id: str,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_cb_scope),
):
    _ensure_schema(db)
    return flow_to_dto(get_proposal_by_id(db, proposal_id))


@router.put("/{proposal_id}/approval-flow", response_model=ProposalApprovalFlow)
def upsert_approval_flow(
    proposal_id: str,
    payload: UpsertProposalFlowRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """결재 플로우 스냅샷 저장/갱신 (산정·배정 완료 후)."""
    _ensure_schema(db)
    row = db.get(ProposalFlow, proposal_id)
    if row is None:
        row = ProposalFlow(
            proposal_id=proposal_id,
            current_status=payload.current_status.value
            if hasattr(payload.current_status, "value")
            else str(payload.current_status),
            assigned_auditors_json=[],
            approval_line_json={},
        )
        db.add(row)

    from app.services.proposal_approval import apply_dto_to_row

    apply_dto_to_row(row, payload)
    if payload.owner_user_id:
        row.owner_user_id = payload.owner_user_id
    if payload.cb_id is not None:
        row.cb_id = payload.cb_id
    elif getattr(current_user, "cb_id", None):
        row.cb_id = current_user.cb_id
    if payload.company_id is not None:
        row.company_id = payload.company_id
    save_proposal(db, row)
    return flow_to_dto(row)


@router.post("/{proposal_id}/approval", response_model=ProposalApprovalFlow)
def post_process_approval(
    proposal_id: str,
    payload: ProcessApprovalRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """결재 승인/반려 — processProposalApproval."""
    _ensure_schema(db)
    user_id = payload.user_id or str(getattr(current_user, "id", "") or "")
    return process_proposal_approval(
        db=db,
        proposal_id=proposal_id,
        action=payload.action,
        user_id=user_id,
        user_role=payload.user_role,
        comment=payload.comment,
    )
