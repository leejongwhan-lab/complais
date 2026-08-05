"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base



class AuditorAnnualEvaluations(Base):
    __tablename__ = "auditor_annual_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    eval_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    score_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="종합 점수")
    score_knowledge: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="지식/기술 점수")
    score_conduct: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="행동강령 점수")
    score_report: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="보고서 작성 점수")
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evaluated_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="CB 담당자")
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorApprovalHistory(Base):
    __tablename__ = "auditor_approval_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    standard_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    from_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    iaf_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="관련 IAF 코드")
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_doc: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="증빙 참조")
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    witness_auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    witness_contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    witness_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorAuditActivities(Base):
    __tablename__ = "auditor_audit_activities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    standard_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    organization: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditorCbMemberships(Base):
    __tablename__ = "auditor_cb_memberships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_freelance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cb_auditor_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="플랫폼 일련번호 (전체 통합)")
    fee_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fee_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="적용비율 %")
    auditor_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True, comment="심사수당 %")
    marketing_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True, comment="마케팅 %")
    monthly_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True, comment="상근 월급")
    contract_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    grade_at_cb: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    apply_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    apply_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cb_review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    approved_iaf_codes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    daily_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cert_standards: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kar_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # CB별 전속 자격/평가 관리
    qualification_granted_at: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="자격 부여일"
    )
    qualification_expires_at: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="자격 갱신/만료일"
    )
    knowledge_eval_score: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="지식/규격 평가 점수"
    )
    cpd_hours_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="당해년도 CPD 이수 시간"
    )
    conflict_of_interest_cleared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="이해상충 선언 완료 여부"
    )
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="가변 JSON 메타데이터"
    )


class AuditorClientConfirmations(Base):
    __tablename__ = "auditor_client_confirmations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    auditor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    confirmation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    has_consulting_fact: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmed_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditorCompetencyScores(Base):
    __tablename__ = "auditor_competency_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard_code: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="0~100")
    evaluated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    evaluator_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditorConductSigns(Base):
    __tablename__ = "auditor_conduct_signs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)


class AuditorConflictChecks(Base):
    __tablename__ = "auditor_conflict_checks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    auditor_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    has_consulting_history: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_special_relationship: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_other_support: Mapped[bool] = mapped_column(Boolean, nullable=False)
    result_status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditorConflictDeclarations(Base):
    __tablename__ = "auditor_conflict_declarations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    declare_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    has_conflict: Mapped[bool] = mapped_column(Boolean, nullable=False)
    conflict_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="이해상충 내용 상세")
    declared_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    confirmed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="CB 담당자 user_id")
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditorConflictHistory(Base):
    __tablename__ = "auditor_conflict_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="companies.id")
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="신고 받은 CB")
    company_biz_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    consult_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    consult_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consult_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    restriction_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorConsultingExperience(Base):
    """Maps to live auditor_consulting_experiences table."""
    __tablename__ = "auditor_consulting_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(Integer, ForeignKey("auditors.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    company_id = Column(Integer, nullable=True)
    biz_no = Column(String(20), nullable=True, comment="자문 기업 사업자등록번호 (이해상충 검증용)")
    consulting_type = Column(String(50), nullable=True, comment="자문 유형")
    ksic_code = Column(String(10), nullable=True)
    iaf_code = Column(String(10), nullable=True)
    standard_code = Column(String(20), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    consulting_days = Column(Integer, nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    auditor = relationship("Auditor", back_populates="consultings")


class AuditorEducation(Base):
    """Maps to live auditor_educations table."""
    __tablename__ = "auditor_educations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(Integer, ForeignKey("auditors.id"), nullable=False)
    degree = Column(String(50), nullable=False)
    school_name = Column(String(200), nullable=False)
    major = Column(String(200), nullable=False)
    entered_at = Column(Date, nullable=True)
    graduated_at = Column(Date, nullable=True)
    mapped_iaf_codes = Column(Text, nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)

    auditor = relationship("Auditor", back_populates="educations")


class AuditorEnvCompetency(Base):
    __tablename__ = "auditor_env_competency"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    env_grade: Mapped[str] = mapped_column(String(50), nullable=False, comment="E1=매우높음~E4=낮음")
    score_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="총 점수")
    score_education: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="전공 점수")
    score_work_exp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="실무경력 점수")
    score_training: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="교육이수 점수")
    score_audit_exp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="심사경력 점수")
    granted_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    granted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorExternalCert(Base):
    """Maps to live auditor_external_certs (column names aliased for API schema)."""
    __tablename__ = "auditor_external_certs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(Integer, ForeignKey("auditors.id"), nullable=False)
    # API schema: cert_name / issuer / cert_no / issued_date / expiry_date
    cert_name = Column("standard_code", String(20), nullable=False)
    issuer = Column("qual_org", String(50), nullable=False)
    cert_no = Column("qual_no", String(100), nullable=False)
    issued_date = Column("granted_at", Date, nullable=True)
    expiry_date = Column("expires_at", Date, nullable=True)
    grade = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    auditor = relationship("Auditor", back_populates="external_certs")


class AuditorGradeRequirements(Base):
    __tablename__ = "auditor_grade_requirements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    to_grade: Mapped[str] = mapped_column(String(50), nullable=False)
    standard_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="ALL=공통, QMS/EMS=표준별")
    min_audit_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="최소 심사일수")
    min_full_audit_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="최소 전체심사 횟수")
    min_initial_renewal: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="최소 최초/갱신심사 횟수")
    min_lead_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="최소 팀장 역할 횟수")
    min_lead_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="팀장으로서 최소 심사일수")
    min_years_as_grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="현 등급 최소 유지 연수")
    cross_standard_discount: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="타 표준 보유 시 요건 완화")
    cross_discount_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="완화 시 심사일수")
    requires_witness: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="입회 필요 여부")
    witness_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="필요 입회 횟수")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorQualification(Base):
    """심사원 보유 표준 및 IAF 코드 자격 (승인 워크플로우).
    Note: table may not exist on legacy DB yet — used by approval APIs.
    """
    __tablename__ = "auditor_qualifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(Integer, ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False)
    standard = Column(String(20), nullable=False)
    # master_data.IafCode 정규화 이후 sub_code(구 iaf_ksic.IafCode PK) 대신 code를 참조
    sub_code = Column(String(10), ForeignKey("iaf_codes.code"), nullable=False)
    approval_status = Column(String(20), default="PENDING")
    approved_by = Column(String(50), nullable=True)

    auditor = relationship("Auditor", back_populates="qualification_records")


class AuditorScopeGrants(Base):
    """
    심사원이 특정 인증원(CB)으로부터 승인받은 표준/IAF 자격 범위 (배정 사전 검증의 근거 데이터).
    auditor_id -> auditors.id, cb_id -> certification_bodies.id FK로 정규화됨.
    """
    __tablename__ = "auditor_scope_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False)
    cb_id: Mapped[int] = mapped_column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id", ondelete="CASCADE"), nullable=False)
    standard_code: Mapped[str] = mapped_column(String(20), nullable=False)
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="IAF 코드 (03, 04A 등)")
    nace_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    grant_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="부여 근거")
    granted_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="CB 담당자 user_id")
    granted_at: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    nace_codes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="NACE Division 코드 (콤마구분)")
    iaf_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IAF 코드 (콤마구분)")
    mdqms_areas: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="ISO 13485 기술영역")
    sub_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IAF 세분류 코드 (콤마구분)")
    witness_auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="참관 검증심사원")
    witness_contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="참관 심사 계약")
    witness_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="참관 일자")


class AuditorScopeRequests(Base):
    """
    심사원의 자격범위 확대/승급 신청 (승인되면 AuditorScopeGrants에 반영).
    auditor_id -> auditors.id, cb_id -> certification_bodies.id FK로 정규화됨.
    """
    __tablename__ = "auditor_scope_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False)
    cb_id: Mapped[int] = mapped_column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id", ondelete="CASCADE"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="qualification=자격확대, code_expand=코드확대, grade_up=등급승급")
    standard_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="자격확대 시 새 표준")
    iaf_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IAF 코드 (콤마구분)")
    target_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="승급 목표 등급")
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="신청 사유")
    evidence_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="증빙 안내 (메일 발송 내용)")
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="CB 담당자 user_id")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    nace_codes: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="NACE Division 코드 (콤마구분)")
    sub_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="IAF 세분류 코드 (콤마구분)")


class AuditorSeq(Base):
    __tablename__ = "auditor_seq"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, comment="마지막 채번 번호")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorSettlements(Base):
    __tablename__ = "auditor_settlements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="contracts.id (also used as project_id)")
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    settlement_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, comment="YYYY-MM")
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorWitnessRecords(Base):
    __tablename__ = "auditor_witness_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="심사 계약")
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    witness_auditor_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="입회한 검증심사원")
    observed_auditor_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="관찰받은 심사원")
    witness_date: Mapped[date] = mapped_column(Date, nullable=False)
    audit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    observation_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True, comment="입회 일수")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checklist_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="나중에 체크리스트 연결")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorWorkExperience(Base):
    """Maps to live auditor_work_experiences table (API 'careers' collection).

    주의: 과거 __tablename__이 실제와 다른 `auditor_careers`로 잘못 지정되어 있었고
    (`alembic revision --autogenerate` 검토 중 발견: 실제 테이블은 6건의 실데이터를 가진
    `auditor_work_experiences`이며 `auditor_careers`는 아예 존재하지 않음), 컬럼 별칭 또한
    실제 컬럼명(company_name/position/ksic_code/iaf_code/note)과 다른 레거시 별칭
    (company/role/industry_code/iaf_codes/description)을 가리키고 있어 함께 수정함.
    """
    __tablename__ = "auditor_work_experiences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(Integer, ForeignKey("auditors.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    position = Column(String(100), nullable=True)
    ksic_code = Column(String(10), nullable=True)
    iaf_code = Column(String(10), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, nullable=False, default=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)

    auditor = relationship("Auditor", back_populates="careers")


class AuditorCareer(Base):
    """
    심사원 산업분야별 실무경력 (KSIC/IAF 정규화 매핑).
    부속서 1(KSIC↔IAF)·부속서 2(전공↔IAF 단서조항의 추가 실무경력 요건) 심사 근거 자료로 사용.
    기존 `AuditorWorkExperience`(auditor_careers 테이블, 문자열 코드 기반)와 별도로,
    master_data의 정규화 마스터를 FK로 참조하는 신규 경력 레코드.
    """
    __tablename__ = "auditor_career_records"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False, index=True)

    company_name = Column(String(200), nullable=False, comment="근무/컨설팅 기업명")
    position = Column(String(100), nullable=True, comment="직위/역할")

    ksic_id = Column(BigInteger, ForeignKey("ksic_codes.id", ondelete="SET NULL"), nullable=True, comment="해당 업종 KSIC 마스터 FK")
    iaf_id = Column(BigInteger, ForeignKey("iaf_codes.id", ondelete="SET NULL"), nullable=True, comment="환산된 IAF 코드 마스터 FK")

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False, comment="현재 재직/진행 여부")
    career_months = Column(Integer, nullable=True, comment="경력 개월 수 (자동 계산 캐시)")

    is_verified = Column(Boolean, default=False, comment="증빙 확인 여부")
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    auditor = relationship("Auditor", back_populates="career_records")
    ksic = relationship("KsicCode")
    iaf = relationship("IafCode")


class AuditorIafQualification(Base):
    """
    심사원이 보유/부여받은 IAF 코드별 자격 (부속서 1·2 기준 정규화 자격 마스터).
    부속서 2 단서조항(전공만으로 부족 시 경력 추가, 위원회 심의 등)의 최종 승인 결과를 저장.
    """
    __tablename__ = "auditor_iaf_qualifications"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False, index=True)
    iaf_id = Column(BigInteger, ForeignKey("iaf_codes.id", ondelete="CASCADE"), nullable=False, index=True)

    source_type = Column(String(20), nullable=False, comment="자격 취득 근거 (MAJOR/CAREER/COMMITTEE/TRAINING 등)")
    source_major_id = Column(BigInteger, ForeignKey("majors.id", ondelete="SET NULL"), nullable=True, comment="전공 기반 취득 시 근거 전공 FK")
    source_career_id = Column(BigInteger, ForeignKey("auditor_career_records.id", ondelete="SET NULL"), nullable=True, comment="경력 기반 취득 시 근거 경력 FK")

    grade = Column(String(50), nullable=True, comment="심사원 등급 (Trainee/Auditor/Lead 등)")
    granted_at = Column(Date, nullable=True)
    expires_at = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    auditor = relationship("Auditor", back_populates="iaf_qualifications")
    iaf = relationship("IafCode")
    source_major = relationship("Major")
    source_career = relationship("AuditorCareer")


class AuditApplication(Base):
    """
    심사원의 신규/확대 IAF 자격 신청서 (부속서 1·2 기준 자격인증 심사 워크플로우).
    승인 시 AuditorIafQualification 레코드를 생성/연결한다.
    """
    __tablename__ = "audit_applications"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False, index=True)
    iaf_id = Column(BigInteger, ForeignKey("iaf_codes.id", ondelete="CASCADE"), nullable=False, index=True)

    application_type = Column(String(20), nullable=False, comment="신청 유형 (NEW=신규자격, EXPAND=자격확대, RENEWAL=갱신)")
    career_id = Column(BigInteger, ForeignKey("auditor_career_records.id", ondelete="SET NULL"), nullable=True, comment="근거 경력")
    major_id = Column(BigInteger, ForeignKey("majors.id", ondelete="SET NULL"), nullable=True, comment="근거 전공")

    status = Column(String(20), default="PENDING", comment="PENDING/APPROVED/REJECTED/COMMITTEE_REVIEW")
    requires_committee = Column(Boolean, default=False, comment="자격인증위원회 심의 필요 여부 (부속서 2 단서조항)")
    reason = Column(Text, nullable=True, comment="신청 사유/자기소개")
    review_note = Column(Text, nullable=True)
    reviewed_by = Column(String(50), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    resulting_qualification_id = Column(
        BigInteger, ForeignKey("auditor_iaf_qualifications.id", ondelete="SET NULL"), nullable=True,
        comment="승인 시 생성된 자격 레코드",
    )

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    auditor = relationship("Auditor", back_populates="iaf_applications")
    iaf = relationship("IafCode")
    career = relationship("AuditorCareer")
    major = relationship("Major")
    resulting_qualification = relationship("AuditorIafQualification")
    md_review = relationship(
        "AuditMdReview",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan",
    )
    contracts = relationship(
        "Contract",
        back_populates="application",
        cascade="all, delete-orphan",
    )
    assignments = relationship(
        "AuditAssignment",
        back_populates="application",
        cascade="all, delete-orphan",
    )


class Auditor(Base):
    """인증심사원 — columns aligned to live MySQL `auditors` table."""
    __tablename__ = "auditors"

    id = Column(MySQLInteger(unsigned=True), primary_key=True, autoincrement=True)
    complais_no = Column(String(50), nullable=True, comment="ComplAIs 개인번호")
    user_id = Column(Integer, nullable=True)
    name = Column(String(50), nullable=False)
    name_en = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True)
    grade = Column(String(30), nullable=True)
    employment_type = Column(String(50), nullable=True)
    is_freelance = Column(Boolean, nullable=True)
    primary_cb_id = Column(Integer, nullable=True, comment="주 소속 CB")
    registration_no = Column(String(50), nullable=True)
    iaf_codes = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=True)
    status = Column(String(20), nullable=True)
    contract_type = Column(String(50), nullable=True)
    daily_rate = Column(Float, nullable=True)
    fee_ratio = Column(Float, nullable=True)
    bank_name = Column(String(50), nullable=True)
    account_no = Column(String(50), nullable=True)
    account_holder = Column(String(50), nullable=True)
    intro = Column(Text, nullable=True)
    monthly_fee = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    address = Column(String(500), nullable=True)
    detail_address = Column(String(500), nullable=True)
    profile_status = Column(String(20), nullable=True)

    # --- 백오피스 마스터 확장 컬럼 ---
    rrn_hash = Column(String(255), nullable=True, comment="주민등록번호 암호화 Hash")
    income_type = Column(String(50), nullable=True, comment="3.3% 사업소득/기타소득/법인사업자")
    education_level = Column(String(50), nullable=True)
    school_name = Column(String(100), nullable=True)
    major = Column(String(100), nullable=True)
    career_summary = Column(Text, nullable=True)
    total_working_days = Column(Integer, nullable=True)
    cb_affiliation = Column(String(100), nullable=True)
    commission_type = Column(String(20), nullable=True, comment="퍼센트/건별")
    security_pledge_agreed = Column(Boolean, nullable=True, default=False)
    subcontract_agreed = Column(Boolean, nullable=True, default=False)

    educations = relationship(
        "AuditorEducation",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    careers = relationship(
        "AuditorWorkExperience",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    consultings = relationship(
        "AuditorConsultingExperience",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    external_certs = relationship(
        "AuditorExternalCert",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    qualification_records = relationship(
        "AuditorQualification",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    career_records = relationship(
        "AuditorCareer",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    iaf_qualifications = relationship(
        "AuditorIafQualification",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    iaf_applications = relationship(
        "AuditApplication",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    assignments = relationship(
        "AuditAssignment",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    audit_notes = relationship(
        "AuditNote",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )
    audit_ncrs = relationship(
        "AuditNCR",
        back_populates="auditor",
        cascade="all, delete-orphan",
    )

