"""제안서 결재 플로우 저장 (ProposalApprovalFlow)."""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)

from app.core.database import Base


class ProposalFlow(Base):
    """제안서 워크플로 · 결재 스냅샷.

    proposal_id 는 문자열(외부/레거시 cb_proposals.id 또는 UUID).
    """

    __tablename__ = "proposal_flows"

    proposal_id = Column(String(64), primary_key=True)
    current_status = Column(String(40), nullable=False, index=True, default="DRAFT")

    # calculationSummary
    base_md = Column(Numeric(12, 2), nullable=False, default=0)
    net_adjustment_rate = Column(Numeric(6, 2), nullable=False, default=0)
    final_md = Column(Numeric(12, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    vat = Column(Numeric(15, 2), nullable=False, default=0)
    grand_total = Column(Numeric(15, 2), nullable=False, default=0)

    # assignedAuditors / approvalLine — JSON
    assigned_auditors_json = Column(JSON, nullable=False, default=list)
    approval_line_json = Column(JSON, nullable=False, default=dict)

    # 작성 담당자 (반려 시 알림 대상)
    owner_user_id = Column(String(64), nullable=True)
    cb_id = Column(Integer, nullable=True, index=True)
    company_id = Column(Integer, nullable=True, index=True)

    pdf_generated = Column(Boolean, nullable=False, default=False)
    pdf_path = Column(String(512), nullable=True)
    dispatched_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    note = Column(Text, nullable=True)
