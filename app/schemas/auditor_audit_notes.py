"""Auditor 심사노트 (조항 단위) DTOs — master DB terminology."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AuditNoteStandardItem(BaseModel):
    standard_key: str  # platform catalog key (QMS_2015)
    standard_code: Optional[str] = None  # standard_master.standard_code (ISO9001)
    family_code: str
    display_code: str
    name_ko: str
    clauses_status: str = "READY"
    clause_count: int = 0


class AuditNoteCheckpoint(BaseModel):
    title: str = ""
    hint: str = ""


class AuditNoteKpiHint(BaseModel):
    """KPI hint for 심사노트 panels (ISO audit / ESG).

    Sources: audit_kpi_master | iso_audit_kpi_master | esg_master_kpis | kpi_master.
    key/label kept as compat aliases of kpi_id/kpi_name.
    """

    kpi_id: str = ""
    kpi_name: str = ""
    key: str = ""  # = kpi_id
    label: str = ""  # = kpi_name
    source: Optional[str] = None  # audit_kpi | iso_audit | esg_master | kpi_master
    kpi_kind: Optional[str] = None  # iso | esg

    @model_validator(mode="after")
    def _sync_aliases(self) -> "AuditNoteKpiHint":
        kid = (self.kpi_id or self.key or "").strip()
        kn = (self.kpi_name or self.label or kid).strip()
        self.kpi_id = kid
        self.key = kid
        self.kpi_name = kn
        self.label = kn
        return self


class AuditNoteClauseItem(BaseModel):
    id: int
    standard_key: str
    standard_code: Optional[str] = None  # standard_master.standard_code
    family_code: Optional[str] = None
    clause_no: str  # actual_clause_no / hls display key
    clause_topic: str = ""  # master title
    clause_title: str = ""  # compat alias of clause_topic
    question: str = ""
    default_kpis: List[AuditNoteKpiHint] = Field(default_factory=list)
    # Dual center panels
    iso_audit_kpis: List[AuditNoteKpiHint] = Field(
        default_factory=list,
        description="ISO 심사 KPI (iso_audit_kpi_master + audit_kpi_master)",
    )
    esg_kpis: List[AuditNoteKpiHint] = Field(
        default_factory=list,
        description="ESG KPI (esg_master_kpis / kpi_master)",
    )
    checkpoints: List[AuditNoteCheckpoint] = Field(default_factory=list)
    process_group_id: Optional[str] = None
    process_group_name: Optional[str] = None
    group_name: Optional[str] = None  # compat = process_group_name
    hls_code: Optional[str] = None
    source: Optional[str] = None  # process_group | iso_clauses
    sort_order: int = 0
    # Multi-note per clause (process mode extras); 1 = primary plan/master row
    note_seq: int = 1
    clause_row_id: Optional[int] = None  # audit_note_clauses.id when persisted
    is_extra: bool = False  # True when note_seq > 1 (추가 심사노트)
    # plan autofill hints (audit_plan_items)
    plan_dept: Optional[str] = None
    plan_process: Optional[str] = None
    # saved state (optional)
    verdict: Optional[str] = None
    note_text: Optional[str] = None  # maps to audit_note_clauses.finding
    kpi_values: Dict[str, str] = Field(default_factory=dict)
    ncr_grade: Optional[str] = None
    ncr_fact: Optional[str] = None
    ncr_requirement: Optional[str] = None
    ncr_root_cause: Optional[str] = None
    ncr_audit_date: Optional[str] = None
    ncr_auditor_name: Optional[str] = None
    ncr_dept: Optional[str] = None
    ncr_request_date: Optional[str] = None
    ncr_due_date: Optional[str] = None
    ncr_esg_tags: List[str] = Field(default_factory=list)
    saved_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _sync_topic_group(self) -> "AuditNoteClauseItem":
        topic = (self.clause_topic or self.clause_title or "").strip()
        self.clause_topic = topic
        self.clause_title = topic
        pg_name = (self.process_group_name or self.group_name or "").strip() or None
        self.process_group_name = pg_name
        self.group_name = pg_name
        return self


class AuditInterviewTemplateItem(BaseModel):
    role_key: str
    role: str
    icon: str = ""  # unused — text-only UI
    mandatory: bool = False
    family_code: str = "COMMON"
    questions: List[str] = Field(default_factory=list)


class AuditInterviewEntry(BaseModel):
    """v15 면담 entry — structural fields + single Q/A box + 종합의견."""

    role_key: str
    role: Optional[str] = None
    name: Optional[str] = None
    dept: Optional[str] = None
    position: Optional[str] = None
    date: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    place: Optional[str] = None
    overall: Optional[str] = None
    qa_content: Optional[str] = None  # unified questions/answers textarea
    answers: Dict[str, str] = Field(
        default_factory=dict, description="legacy q0,q1,… — merged into qa_content on load"
    )


class AuditInterviewSaveIn(BaseModel):
    """면담 저장 — entries[] → audit_notes.interview_json."""

    contract_id: int
    entries: List[AuditInterviewEntry] = Field(default_factory=list)
    content: Optional[str] = None  # legacy single-text (ignored if entries present)


class AuditInterviewSaveOut(BaseModel):
    ok: bool = True
    note_id: int
    message: str = "면담이 저장되었습니다."


class AuditNoteSessionOut(BaseModel):
    note_id: Optional[int] = None
    contract_id: Optional[int] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    cb_id: Optional[int] = None
    cb_name: Optional[str] = None  # 해당인증원명
    standard_key: str
    process_standard_code: Optional[str] = None  # = standard_code (ISO9001)
    standards: List[AuditNoteStandardItem] = Field(default_factory=list)
    standards_label: Optional[str] = None  # 표준정보 display join
    status: str = "draft"
    clauses: List[AuditNoteClauseItem] = Field(default_factory=list)
    preview: bool = False
    preview_message: Optional[str] = None
    clause_source: Optional[str] = None  # process_group | iso_clauses
    standards_filter: Optional[str] = None  # contract | company | intersection | preview
    note_method: str = "process"  # clause=조항심사 | process=프로세스심사
    # 단일/통합 — contracts.audit_mode (신청 시 표준 수 기준); note_method와 별개
    audit_mode: Optional[str] = None  # single | integrated
    audit_mode_label: Optional[str] = None  # 단일심사 | 통합심사
    audit_type: Optional[str] = None  # initial / surveillance… (contracts.audit_type)
    audit_type_label: Optional[str] = None  # 최초심사 / 사후심사…
    audit_stage_label: Optional[str] = None  # 1단계 준비성 검토 / 2단계 심사
    audit_date: Optional[str] = None  # YYYY-MM-DD (period start)
    audit_period_end: Optional[str] = None
    # 계획서 스코프 / 팀장 회의
    auditor_name: Optional[str] = None
    is_lead: bool = False
    team_meeting: bool = False
    plan_id: Optional[int] = None
    plan_empty: bool = False
    plan_item_count: int = 0
    scope_mode: Optional[str] = None  # preview | assigned | team_meeting | no_plan
    scope_message: Optional[str] = None
    team_size: int = 0
    requires_team_review: bool = False
    team_review_confirmed: bool = False
    team_review_confirmed_at: Optional[str] = None
    interview_content: Optional[str] = None  # legacy flatten (compat)
    interview_templates: List[AuditInterviewTemplateItem] = Field(default_factory=list)
    interview_entries: List[AuditInterviewEntry] = Field(default_factory=list)


class TeamReviewConfirmIn(BaseModel):
    contract_id: int


class TeamReviewConfirmOut(BaseModel):
    ok: bool = True
    contract_id: int
    team_size: int = 0
    team_review_confirmed: bool = True
    team_review_confirmed_at: Optional[str] = None
    closed_waiting_ncr_count: int = 0
    message: str = "팀 검토가 확인되었습니다."


class AuditNoteMethodIn(BaseModel):
    contract_id: int
    note_method: str = Field(..., description="clause | process")


class AuditNoteMethodOut(BaseModel):
    ok: bool = True
    note_id: int
    note_method: str
    message: str = "심사방식이 저장되었습니다."


class AuditMatrixCell(BaseModel):
    clause_no: str
    clause_topic: str = ""
    clause_title: str = ""  # compat
    standard_key: Optional[str] = None
    standard_code: Optional[str] = None
    process_group_name: Optional[str] = None
    group_name: Optional[str] = None
    process_group_id: Optional[str] = None
    required: bool = True
    written: bool = False
    verdict: Optional[str] = None
    audit_method: Optional[str] = None
    missing: bool = True

    @model_validator(mode="after")
    def _sync(self) -> "AuditMatrixCell":
        topic = (self.clause_topic or self.clause_title or "").strip()
        self.clause_topic = topic
        self.clause_title = topic
        pg = (self.process_group_name or self.group_name or "").strip() or None
        self.process_group_name = pg
        self.group_name = pg
        return self


class AuditMatrixOut(BaseModel):
    contract_id: Optional[int] = None
    note_id: Optional[int] = None
    standard_key: str
    process_standard_code: Optional[str] = None
    note_method: Optional[str] = None
    audit_mode: Optional[str] = None
    audit_mode_label: Optional[str] = None
    standards: List[AuditNoteStandardItem] = Field(default_factory=list)
    required_count: int = 0
    written_count: int = 0
    missing_count: int = 0
    coverage_pct: float = 0.0
    cells: List[AuditMatrixCell] = Field(default_factory=list)
    missing_clauses: List[str] = Field(default_factory=list)


class AuditNoteKpiValueIn(BaseModel):
    kpi_id: Optional[str] = None
    key: Optional[str] = None  # compat = kpi_id
    value: Optional[str] = None

    @model_validator(mode="after")
    def _sync(self) -> "AuditNoteKpiValueIn":
        kid = (self.kpi_id or self.key or "").strip()
        self.kpi_id = kid or None
        self.key = kid or None
        return self


class AuditNoteClauseSaveIn(BaseModel):
    contract_id: int
    standard_key: str
    standard_code: Optional[str] = None  # preferred master code when known
    clause_no: str
    clause_topic: Optional[str] = None
    clause_title: Optional[str] = None  # compat
    process_group_id: Optional[str] = None
    hls_code: Optional[str] = None
    note_seq: int = Field(default=1, ge=1, description="1=기본, 2+=추가 심사노트")
    clause_row_id: Optional[int] = None  # prefer update by PK when known
    note_text: Optional[str] = None
    verdict: str = "적합"
    ncr_grade: Optional[str] = None
    ncr_fact: Optional[str] = None
    ncr_requirement: Optional[str] = None
    ncr_root_cause: Optional[str] = None
    ncr_audit_date: Optional[str] = None
    ncr_auditor_name: Optional[str] = None
    ncr_dept: Optional[str] = None
    ncr_request_date: Optional[str] = None
    ncr_due_date: Optional[str] = None
    ncr_esg_tags: List[str] = Field(default_factory=list)
    kpi_values: List[AuditNoteKpiValueIn] = Field(default_factory=list)
    audit_method: Optional[str] = Field(
        default=None, description="clause | process — 작성 시 심사방식"
    )


class ProcessGroupHlsItem(BaseModel):
    hls_code: str
    checkpoints_summary: Optional[str] = None


class ProcessGroupClauseItem(BaseModel):
    actual_clause_no: str
    clause_topic: Optional[str] = None
    guide_note: Optional[str] = None


class ProcessGroupItem(BaseModel):
    process_group_id: str
    process_group_name: str
    hls_scope_desc: Optional[str] = None
    hls_codes: List[ProcessGroupHlsItem] = Field(default_factory=list)
    standard_clauses: List[ProcessGroupClauseItem] = Field(default_factory=list)


class ProcessGroupNavOut(BaseModel):
    """심사노트 프로세스그룹 네비게이션."""

    standard_code: Optional[str] = None
    process_groups: List[ProcessGroupItem] = Field(default_factory=list)
    standards: List[Dict[str, Any]] = Field(default_factory=list)


class AuditKpiMasterItem(BaseModel):
    kpi_id: str
    hls_code: str
    standard_code: str = "COMMON"
    kpi_name: str
    kpi_type: str
    formula: Optional[str] = None
    unit: Optional[str] = None


class AuditNoteClauseSaveOut(BaseModel):
    ok: bool = True
    note_id: int
    clause_row_id: Optional[int] = None
    ncr_id: Optional[int] = None
    ncr_status: Optional[str] = None
    team_review_gated: bool = False
    message: str = "저장되었습니다."


class AuditNoteFormalizeIn(BaseModel):
    standard_key: Optional[str] = None
    clause_no: Optional[str] = None
    clause_topic: Optional[str] = None
    clause_title: Optional[str] = None
    question: Optional[str] = None
    rough_text: str = Field(..., min_length=1)


class AuditNoteFormalizeOut(BaseModel):
    formalized_text: str = ""
    configured: bool = False
    message: str = ""
