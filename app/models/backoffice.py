"""백오피스 마스터 확장 테이블 — 기존 companies/auditors/certification_bodies에는
대응 개념이 없는, 순수 신규 서브 엔티티만 모아둔다.

(보유자격/CPD/자문경력/추가사업장 등은 이미 존재하는 kar_qualifications,
kar_cpd_records, auditor_consulting_experiences, company_sites를 확장해 재사용한다.
자세한 매핑은 app/models/misc.py, app/models/auditor.py, app/models/company.py 참고.)
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


class CompanyStaff(Base):
    """기업 담당 직원 (최대 5명)."""
    __tablename__ = "company_staff_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(MySQLInteger(unsigned=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    staff_name = Column(String(50), nullable=False)
    department = Column(String(100), nullable=True)
    position = Column(String(50), nullable=True)
    mobile = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Companies", backref="staff_members")


class CompanyAuditHistory(Base):
    """기업 심사이력 (최초/사후/갱신 및 인수인계 내역)."""
    __tablename__ = "company_audit_history_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(MySQLInteger(unsigned=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    initial_cert_date = Column(Date, nullable=True, comment="최초인증일")
    surveillance_1_date = Column(Date, nullable=True, comment="1차 사후심사일")
    surveillance_2_date = Column(Date, nullable=True, comment="2차 사후심사일")
    renewal_date = Column(Date, nullable=True, comment="갱신심사일")
    manager_auditor = Column(String(50), nullable=True, comment="담당 심사원명")
    transfer_history = Column(Text, nullable=True, comment="담당자 인수인계 내역")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    company = relationship("Companies", backref="audit_history")


class AuditorExperienceRecord(Base):
    """심사원 최근 3년 심사통계 (연도별 최초/사후/갱신 건수 및 총 심사일수)."""
    __tablename__ = "auditor_experience_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False, index=True)
    period_year = Column(Integer, nullable=False, comment="통계 연도")
    initial_count = Column(Integer, default=0, nullable=False)
    surveillance_count = Column(Integer, default=0, nullable=False)
    renewal_count = Column(Integer, default=0, nullable=False)
    total_audit_days = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    auditor = relationship("Auditor", backref="experience_records")


class CBStaff(Base):
    """인증기관(CB) 운영 직원."""
    __tablename__ = "cb_staff_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cb_id = Column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id", ondelete="CASCADE"), nullable=False, index=True)
    emp_no = Column(String(30), nullable=True, comment="사번")
    name = Column(String(50), nullable=False)
    position = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    mobile = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    task_type = Column(String(50), nullable=True, comment="담당 업무 유형")
    role_level = Column(String(20), nullable=True, comment="직급/권한 레벨")
    created_at = Column(DateTime, server_default=func.now())

    cb = relationship("CertificationBodies", backref="staff_members")
