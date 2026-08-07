"""심사계획서 / 심사결과보고서 aggregation DTOs (contract_id keyed)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Preferred display order for plan-doc chips — ONLY codes that exist in
# standard_master are returned by the API (labels/names come from DB).
PLAN_STANDARD_CODE_ORDER: List[str] = [
    "ISO9001",
    "ISO14001",
    "ISO45001",
    "ISO50001",
    "ISO22000",
    "ISO27001",
    "ISO37001",
    "ISO37301",
    "ISO22301",
    "ISO42001",
    "ISO19443",
    "ISO27701",
]


class AuditPlanTeamMember(BaseModel):
    role: str = "auditor"  # leader | auditor | te | observer | guide
    name: str = ""
    auditor_id: Optional[int] = None
    qual: Optional[str] = None
    standards: Optional[str] = None
    desc: Optional[str] = None


class AuditPlanScheduleItem(BaseModel):
    time_slot: Optional[str] = None
    process_name: Optional[str] = None
    standard_clause: Optional[str] = None
    clause_no: Optional[str] = None
    auditee_name: Optional[str] = None
    location_name: Optional[str] = None
    auditor_name: Optional[str] = None
    auditor_id: Optional[int] = None
    dept: Optional[str] = None
    process_group_id: Optional[str] = None
    standard_code: Optional[str] = None
    standard_key: Optional[str] = None
    note: Optional[str] = None
    sort_order: Optional[int] = None


class AuditPlanContractInfo(BaseModel):
    contract_id: int
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    biz_no: Optional[str] = None
    address: Optional[str] = None
    scope_kr: Optional[str] = None
    standards: List[str] = Field(default_factory=list)
    standards_codes: List[str] = Field(default_factory=list)
    standards_keys: List[str] = Field(default_factory=list)
    audit_type: Optional[str] = None
    audit_period_start: Optional[str] = None
    audit_period_end: Optional[str] = None
    lead_auditor_id: Optional[int] = None
    lead_auditor_name: Optional[str] = None
    member_auditor_ids: List[int] = Field(default_factory=list)
    cb_name: Optional[str] = None


class AuditPlanOut(BaseModel):
    plan_id: Optional[int] = None
    contract_id: int
    status: Optional[str] = None
    plan_date: Optional[str] = None
    audit_objective: Optional[str] = None
    audit_criteria: Optional[str] = None
    scope_summary: Optional[str] = None
    confirmed_at: Optional[str] = None
    contract: AuditPlanContractInfo
    team: List[AuditPlanTeamMember] = Field(default_factory=list)
    items: List[AuditPlanScheduleItem] = Field(default_factory=list)
    doc_data: Dict[str, Any] = Field(default_factory=dict)
    official_standards: List[Dict[str, str]] = Field(
        default_factory=list,
        description="From standard_master (filtered/ordered by PLAN_STANDARD_CODE_ORDER)",
    )
    notes_deep_link: Optional[str] = None
    reports_deep_link: Optional[str] = None


class AuditPlanSaveIn(BaseModel):
    """Persist confirmed plan → audit_plans + audit_plan_items + contract roster."""

    status: str = "confirmed"  # draft | confirmed | sent
    plan_date: Optional[str] = None
    audit_objective: Optional[str] = None
    audit_criteria: Optional[str] = None
    scope_summary: Optional[str] = None
    standards: List[str] = Field(
        default_factory=list,
        description="Selected standards (ISO9001 / QMS_2015 / 9001 labels OK)",
    )
    lead_auditor_id: Optional[int] = None
    member_auditor_ids: List[int] = Field(default_factory=list)
    team: List[AuditPlanTeamMember] = Field(default_factory=list)
    items: List[AuditPlanScheduleItem] = Field(default_factory=list)
    doc_data: Dict[str, Any] = Field(
        default_factory=dict, description="Full plan UI blob (optional mirror)"
    )
    update_contract_roster: bool = True


class AuditPlanSaveOut(BaseModel):
    ok: bool = True
    plan_id: int
    contract_id: int
    item_count: int = 0
    status: str = "confirmed"
    message: str = "심사계획서가 저장되었습니다."
    notes_deep_link: Optional[str] = None
    reports_deep_link: Optional[str] = None


class AuditReportClauseRow(BaseModel):
    clause_no: str
    standard: str = ""
    standard_code: Optional[str] = None
    clause_label: Optional[str] = None
    verdict: Optional[str] = None
    note: Optional[str] = None
    note_seq: int = 1


class AuditReportNcrRow(BaseModel):
    id: Optional[int] = None
    grade: Optional[str] = None
    clause: Optional[str] = None
    standard: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    requirement: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    auditor_name: Optional[str] = None
    dept: Optional[str] = None


class AuditReportMatrixCell(BaseModel):
    clause_no: str
    clause_topic: str = ""
    standard_key: Optional[str] = None
    standard_code: Optional[str] = None
    written: bool = False
    missing: bool = True
    verdict: Optional[str] = None


class AuditReportAggregateOut(BaseModel):
    """Live aggregation for 심사결과보고서 tabs ② ③ ⑤."""

    contract_id: int
    company_name: Optional[str] = None
    biz_no: Optional[str] = None
    address: Optional[str] = None
    standards: List[str] = Field(default_factory=list)
    standards_label: Optional[str] = None
    audit_type: Optional[str] = None
    audit_period_start: Optional[str] = None
    audit_period_end: Optional[str] = None
    lead_auditor_name: Optional[str] = None
    member_auditor_names: List[str] = Field(default_factory=list)
    team_label: Optional[str] = None
    plan_id: Optional[int] = None
    plan_status: Optional[str] = None
    note_id: Optional[int] = None
    # ② 조항 확인
    clauses: List[AuditReportClauseRow] = Field(default_factory=list)
    # ③ NCR
    ncrs: List[AuditReportNcrRow] = Field(default_factory=list)
    ncr_major: int = 0
    ncr_minor: int = 0
    ncr_obs: int = 0
    # ⑤ 매트릭스
    matrix_required: int = 0
    matrix_written: int = 0
    matrix_missing: int = 0
    matrix_coverage_pct: float = 0.0
    matrix_cells: List[AuditReportMatrixCell] = Field(default_factory=list)
    notes_deep_link: Optional[str] = None
