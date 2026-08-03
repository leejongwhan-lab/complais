"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class AuditAssignments(Base):
    __tablename__ = "audit_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auditor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    iaf_match_status: Mapped[str] = mapped_column(String(30), nullable=False)
    conflict_check_status: Mapped[str] = mapped_column(String(30), nullable=False)
    client_confirmation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    assignment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    standards_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iaf_codes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditClauseMatrix(Base):
    __tablename__ = "audit_clause_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard: Mapped[str] = mapped_column(String(20), nullable=False)
    clause_id: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="계획 작성한 계약")
    target_audit_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="다음에 볼 심사")
    target_sequence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, comment="SA1=1, SA2=2")
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="팀장")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditDayPlans(Base):
    __tablename__ = "audit_day_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    audit_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    standards_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    site_count: Mapped[int] = mapped_column(Integer, nullable=False)
    shift_type: Mapped[str] = mapped_column(String(20), nullable=False)
    shift_count: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    stage1_days: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    stage2_days: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    total_days: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    auditor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    assignment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditDocData(Base):
    __tablename__ = "audit_doc_data"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_data: Mapped[str] = mapped_column(Text, nullable=False)
    saved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditDocumentRules(Base):
    __tablename__ = "audit_document_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="0=공통, 1=1단계, 2=2단계")
    doc_subtype: Mapped[str] = mapped_column(String(50), nullable=False, comment="proc_step key와 일치")
    doc_name_kr: Mapped[str] = mapped_column(String(100), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    standard_specific: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="1=표준별 1건씩 생성")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditDocuments(Base):
    __tablename__ = "audit_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    doc_subtype: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    standard: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    stage: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    doc_status: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    doc_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_visible_to_client: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditNcrs(Base):
    __tablename__ = "audit_ncrs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_id: Mapped[str] = mapped_column(String(20), nullable=False, comment="조항 번호 (4.1 등)")
    std_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="표준 코드 (c,e,s 등)")
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="심사소견 (부적합 내용)")
    requirement: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="해당 요구사항 조항")
    cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="원인 분석")
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="조치 기한")
    correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="즉각시정 (Correction)")
    corrective_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="시정조치 (Corrective Action)")
    ca_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="시정조치 증거/첨부 설명")
    ca_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="기업 제출일시")
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="NCR 발행일시")
    issued_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="발행자 (심사팀장) user_id")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="심사팀장 검토일시")
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="검토자 user_id")
    review_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="검토 의견 (승인/반려 사유)")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    obs_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class AuditNoteClauses(Base):
    __tablename__ = "audit_note_clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard: Mapped[str] = mapped_column(String(20), nullable=False)
    clause_id: Mapped[str] = mapped_column(String(20), nullable=False)
    clause_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditNoteEntries(Base):
    __tablename__ = "audit_note_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    clause_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    standard_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditNoteKpi(Base):
    __tablename__ = "audit_note_kpi"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kpi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    measured_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    measured_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    data_source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditNoteNcr(Base):
    __tablename__ = "audit_note_ncr"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_id_ref: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ncr_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    standard: Mapped[str] = mapped_column(String(20), nullable=False)
    clause: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    client_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    client_response_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    corrective_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditNotes(Base):
    __tablename__ = "audit_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    audit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_verdict: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    assignment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    standard_code: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_no: Mapped[str] = mapped_column(String(20), nullable=False)
    dept: Mapped[str] = mapped_column(String(100), nullable=False)
    process: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finding_type: Mapped[str] = mapped_column(String(50), nullable=False)


class AuditPlanItems(Base):
    __tablename__ = "audit_plan_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    audit_plan_id: Mapped[int] = mapped_column(Integer, nullable=False)
    time_slot: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    process_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    standard_clause: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    auditee_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    location_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    auditor_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AuditPlans(Base):
    __tablename__ = "audit_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    plan_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    audit_objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audit_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    communication_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditProposalNegotiations(Base):
    __tablename__ = "audit_proposal_negotiations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditProposals(Base):
    __tablename__ = "audit_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="contracts.id")
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditReports(Base):
    __tablename__ = "audit_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False)
    report_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    verdict: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issued_by: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
