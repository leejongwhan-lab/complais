"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.db.base import Base



class CbAccreditationChangeRequests(Base):
    __tablename__ = "cb_accreditation_change_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    request_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    target_scope_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accreditation: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    reg_no: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    standard_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    standard_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    iaf_codes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mdqms_areas: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="ISO 13485 기술영역")
    nace_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    use_nace: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cert_file_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cert_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    requested_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbAccreditationScopes(Base):
    __tablename__ = "cb_accreditation_scopes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard_code: Mapped[str] = mapped_column(String(20), nullable=False)
    standard_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    iaf_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mdqms_areas: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="ISO 13485 기술영역 코드 (A.1.1,A.1.2 등)")
    nace_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    use_nace: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbAccreditations(Base):
    __tablename__ = "cb_accreditations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    body_id: Mapped[int] = mapped_column(Integer, nullable=False)
    accred_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    standards: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issued_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CbApprovalLines(Base):
    __tablename__ = "cb_approval_lines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    approver_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbFeePolicy(Base):
    __tablename__ = "cb_fee_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_method: Mapped[str] = mapped_column(String(50), nullable=False)
    audit_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    standards_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    marketing_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    auditor_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbNotices(Base):
    __tablename__ = "cb_notices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


# DEPRECATED — cert-application flow 용 CbProposals / CbProposalTeam / CbProposalApprovals /
# CbProposalNegotiations. 진짜 경로는 certification_applications + cb_cert_applications.py
# (enterprise_cert_applications). 삭제 예정(정리 후보). 오늘 작업에서 사용 금지.
class CbProposalApprovals(Base):
    __tablename__ = "cb_proposal_approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    step: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    approval_type: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    acted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbProposalNegotiations(Base):
    __tablename__ = "cb_proposal_negotiations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)
    sender_id: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbProposalTeam(Base):
    __tablename__ = "cb_proposal_team"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    proposal_id: Mapped[int] = mapped_column(Integer, nullable=False)
    auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="0=전체,1=1단계,2=2단계")
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)


class CbProposals(Base):
    __tablename__ = "cb_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    application_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    audit_period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    audit_period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage1_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage1_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage1_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    stage2_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage2_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    stage2_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    audit_days: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    auditor_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_audit: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_travel: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_other: Mapped[int] = mapped_column(Integer, nullable=False)
    fee_total: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    approval_status: Mapped[str] = mapped_column(String(50), nullable=False)
    current_step: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_report: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fee_application: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    standards_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CbStdMdRates(Base):
    __tablename__ = "cb_std_md_rates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard_code: Mapped[str] = mapped_column(String(40), nullable=False)
    md_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    travel_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CbTravelPolicy(Base):
    __tablename__ = "cb_travel_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_name: Mapped[str] = mapped_column(String(50), nullable=False)
    distance_km: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transport_fee: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accommodation_fee: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CertificationBodies(Base):
    __tablename__ = "certification_bodies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cb_initial: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cb_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    accreditation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # DB에는 tel만 존재 — phone은 API/UI 별칭 (동일 컬럼)
    phone = synonym("tel")
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    logo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="기관 소개")
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="최고 관리자 user_id"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ceo_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    biz_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    corp_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="법인번호")
    personal_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="개인사업자번호")
    fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    account_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_holder: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 레거시 컬럼 — 운영 규칙은 cb_operational_rules 로 이관 (하위 호환 유지)
    doc_rule_contract: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    doc_rule_report: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    doc_rule_ncr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fee_per_md: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    fee_travel: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    fee_cert: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    max_consecutive: Mapped[int] = mapped_column(Integer, nullable=False)
    impartiality_cycle_months: Mapped[int] = mapped_column(Integer, nullable=False)
    reg_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # --- 백오피스 마스터 확장 컬럼 (인정 정보, 평가, 세금계산서) ---
    accreditation_region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    accreditation_country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    accreditation_body: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="KAB 등 인정기구")
    stamp_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    accreditation_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    accredited_standards: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iaf_scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expire_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="정상/정지/취소")
    evaluation_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    tax_email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class CbOperationalRules(Base):
    """CB별 운용/수수료 규칙 (ISO 17021-1 조항 9.1~9.5 독립성)."""

    __tablename__ = "cb_operational_rules"

    cb_id: Mapped[int] = mapped_column(MySQLInteger(unsigned=True), primary_key=True)
    doc_rule_contract: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, default="CB-QE-{YYMMDD}-{SEQ3}"
    )
    doc_rule_report: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    doc_rule_ncr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fee_per_md: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fee_travel: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fee_cert: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_consecutive_audits: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    impartiality_cycle_months: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
