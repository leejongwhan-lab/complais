"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



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


class AuditorConsultingExperiences(Base):
    __tablename__ = "auditor_consulting_experiences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ksic_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    iaf_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="KSIC→IAF 자동변환")
    standard_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="컨설팅 표준")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    consulting_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="자문 일수")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorEducations(Base):
    __tablename__ = "auditor_educations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    degree: Mapped[str] = mapped_column(String(50), nullable=False)
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False, comment="전공학과")
    entered_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="입학·시작일")
    graduated_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mapped_iaf_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON 배열 — 자동 매핑 결과")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="CB 확인 여부")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


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


class AuditorExternalCerts(Base):
    __tablename__ = "auditor_external_certs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    qual_org: Mapped[str] = mapped_column(String(50), nullable=False, comment="자격기관 이니셜 (KAR/KFQ/ITS 등)")
    qual_no: Mapped[str] = mapped_column(String(100), nullable=False, comment="자격증 번호 (원본 그대로)")
    standard_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="QMS/EMS/OHSMS 등")
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    granted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


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


class AuditorQualifications(Base):
    __tablename__ = "auditor_qualifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="자격 관리 CB")
    standard_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="QMS/EMS/OHSMS/EnMS/BCMS/ISMS/IATF")
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    pcaa_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="플랫폼 일련번호 (전체 통합)")
    pcaa_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="SMI-Q-10001 형식 (cb_initial+standard+seq)")
    granted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AuditorScopeGrants(Base):
    __tablename__ = "auditor_scope_grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
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
    __tablename__ = "auditor_scope_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
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


class AuditorWorkExperiences(Base):
    __tablename__ = "auditor_work_experiences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auditor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="complais 등록 기업이면 연결")
    ksic_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="KSIC 코드")
    iaf_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="KSIC→IAF 자동변환 결과")
    nace_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="직위/직책")
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="부서")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="NULL이면 현재 재직 중")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
    work_years: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True, comment="근무 연수 (자동계산)")
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    biz_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="사업자등록번호 (IAF 자동 조회용)")


class Auditors(Base):
    __tablename__ = "auditors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complais_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="ComplAIs 개인번호 (YYYYMMDD-NNN)")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_freelance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    primary_cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="주 소속 CB")
    registration_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    iaf_codes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(20), nullable=False)
    daily_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    fee_ratio: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_holder: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detail_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
