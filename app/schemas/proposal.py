"""제안서 결재 플로우 DTO (FE types/proposal.ts 와 동일)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import ProposalStatus


class ProposalCalculationSummary(BaseModel):
    base_md: float = Field(..., alias="baseMD")
    net_adjustment_rate: float = Field(
        ..., alias="netAdjustmentRate", description="순 가/감률 % (최대 ±30)"
    )
    final_md: float = Field(..., alias="finalMD")
    total_amount: float = Field(..., alias="totalAmount", description="공급가액")
    vat: float = Field(..., description="부가세")
    grand_total: float = Field(..., alias="grandTotal", description="최종 제안 금액")

    class Config:
        populate_by_name = True


class ProposalAssignedAuditor(BaseModel):
    standard_code: str = Field(..., alias="standardCode", description="familyCode")
    lead_auditor_id: str = Field(..., alias="leadAuditorId", description="선임심사원")
    auditor_ids: List[str] = Field(
        default_factory=list, alias="auditorIds", description="동반 심사원"
    )
    ea_code_matched: bool = Field(..., alias="eaCodeMatched")
    coi_checked: bool = Field(..., alias="coiChecked", description="이해상충 검증")

    class Config:
        populate_by_name = True


class ProposalApprovalLine(BaseModel):
    reviewer_id: str = Field(..., alias="reviewerId", description="검토자(심사팀장)")
    reviewer_comment: Optional[str] = Field(None, alias="reviewerComment")
    reviewed_at: Optional[datetime] = Field(None, alias="reviewedAt")
    approver_id: str = Field(
        ..., alias="approverId", description="최종 승인자(인증원장/본부장)"
    )
    approver_comment: Optional[str] = Field(None, alias="approverComment")
    approved_at: Optional[datetime] = Field(None, alias="approvedAt")

    class Config:
        populate_by_name = True


class ProposalApprovalFlow(BaseModel):
    proposal_id: str = Field(..., alias="proposalId")
    current_status: ProposalStatus = Field(..., alias="currentStatus")
    calculation_summary: ProposalCalculationSummary = Field(
        ..., alias="calculationSummary"
    )
    assigned_auditors: List[ProposalAssignedAuditor] = Field(
        default_factory=list, alias="assignedAuditors"
    )
    approval_line: ProposalApprovalLine = Field(..., alias="approvalLine")

    class Config:
        populate_by_name = True
        use_enum_values = True
