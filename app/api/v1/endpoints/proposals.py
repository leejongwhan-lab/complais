# DEPRECATED — 진짜 경로는 certification_applications + cb_cert_applications.py (enterprise_cert_applications). 삭제 예정(정리 후보). 오늘 작업에서 사용 금지.
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
from app.services.scope_expiry import enforce_scope_not_expired

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


def _standards_from_proposal_payload(payload: UpsertProposalFlowRequest) -> list[str]:
    out: list[str] = []
    for a in payload.assigned_auditors or []:
        code = getattr(a, "standard_code", None) or ""
        if code:
            out.append(str(code))
    return out


def _standards_from_proposal_row(row: ProposalFlow) -> list[str]:
    out: list[str] = []
    raw = row.assigned_auditors_json or []
    if isinstance(raw, list):
        for a in raw:
            if isinstance(a, dict):
                code = a.get("standardCode") or a.get("standard_code") or ""
                if code:
                    out.append(str(code))
    return out


@router.put("/{proposal_id}/approval-flow", response_model=ProposalApprovalFlow)
def upsert_approval_flow(
    proposal_id: str,
    payload: UpsertProposalFlowRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """결재 플로우 스냅샷 저장/갱신 (산정·배정 완료 후)."""
    _ensure_schema(db)
    cb_id = payload.cb_id
    if cb_id is None:
        cb_id = getattr(current_user, "cb_id", None)
    standards = _standards_from_proposal_payload(payload)
    if cb_id and standards:
        enforce_scope_not_expired(db, int(cb_id), standards)

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
    # Domain 3: 최종 승인(송부 전) 시 인정만료 잠금
    if payload.action == "APPROVE":
        row = db.get(ProposalFlow, proposal_id)
        if row is not None:
            cb_id = row.cb_id or getattr(current_user, "cb_id", None)
            standards = _standards_from_proposal_row(row)
            if cb_id and standards:
                enforce_scope_not_expired(db, int(cb_id), standards)
    user_id = payload.user_id or str(getattr(current_user, "id", "") or "")
    return process_proposal_approval(
        db=db,
        proposal_id=proposal_id,
        action=payload.action,
        user_id=user_id,
        user_role=payload.user_role,
        comment=payload.comment,
    )
