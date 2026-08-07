"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class Certificates(Base):
    __tablename__ = "certificates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    cert_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    standards: Mapped[str] = mapped_column(Text, nullable=False)
    scope_kr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issued_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    issued_by: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CertificationApplicationAnswers(Base):
    __tablename__ = "certification_application_answers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard_code: Mapped[str] = mapped_column(String(30), nullable=False)
    question_key: Mapped[str] = mapped_column(String(100), nullable=False)
    answer_value: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CertificationApplicationReviewLogs(Base):
    __tablename__ = "certification_application_review_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    after_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CertificationApplicationSites(Base):
    __tablename__ = "certification_application_sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False)
    site_no: Mapped[int] = mapped_column(Integer, nullable=False)
    site_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_kr: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    work_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    regular_count: Mapped[int] = mapped_column(Integer, nullable=False)
    irregular_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    checked: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CertificationApplications(Base):
    __tablename__ = "certification_applications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_no: Mapped[str] = mapped_column(String(50), nullable=False)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    applicant_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    contract_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    application_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    standards_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    standard_audit_types_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    iaf_codes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ksic_codes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    questionnaire_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company_snapshot_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    integrated_check_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_kr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scope_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ksic_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    regular_count: Mapped[int] = mapped_column(Integer, nullable=False)
    irregular_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    work_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    desired_audit_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    desired_audit_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    site_count: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_design_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclusion_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    audit_mode: Mapped[str] = mapped_column(String(50), nullable=False)


class CertificationApplicationMdReviews(Base):
    """레거시 certification_application_md_reviews — 기업 인증신청 MD 검토."""

    __tablename__ = "certification_application_md_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    base_md: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False, default=0)
    base_md_detail_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_md_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    base_md_calculated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    add_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    subtract_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    add_md: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False, default=0)
    subtract_md: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False, default=0)
    final_md: Mapped[float] = mapped_column(Numeric(15, 4), nullable=False, default=0)
    calculation_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_design_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    exclusion_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reviewer_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanyCertificates(Base):
    """기업 보유 인증 — 표준별 인정기관(AB) / 인증기관(CB)."""

    __tablename__ = "company_certificates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    standard_code: Mapped[str] = mapped_column(String(50), nullable=False)
    ab_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    cb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cert_no: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_audit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_audit_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_audit_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    certificate_file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class CompanyKsicCodes(Base):
    """기업별 KSIC 복수 코드 (주업종·부업종)."""

    __tablename__ = "company_ksic_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ksic_code: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
