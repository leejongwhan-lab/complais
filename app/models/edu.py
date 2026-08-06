"""SQLAlchemy ORM models — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, SmallInteger, String, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base



class EduCategories(Base):
    __tablename__ = "edu_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="1=대분류 2=세부분야")
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


class EduCourses(Base):
    __tablename__ = "edu_courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="세부분야 (level=2)")
    course_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    objectives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    curriculum_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="[{day,topic,hours}]")
    prerequisites: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    duration_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_regular: Mapped[int] = mapped_column(Integer, nullable=False)
    price_discount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    refund_eligible: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    ceo_point: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    certificate_issue: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    cpd_credit_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    iso_standard: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, comment="예: 9001, 14001, 42001")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    view_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    apply_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rating_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric, nullable=True)
    rating_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EduEnrollments(Base):
    __tablename__ = "edu_enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    auditor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applicant_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    student_name: Mapped[str] = mapped_column(String(80), nullable=False)
    student_email: Mapped[str] = mapped_column(String(120), nullable=False)
    student_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    student_position: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    student_dept: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    emp_insurance_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="고용보험 피보험자번호")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    paid_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    invoice_no: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    refund_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    refund_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attended_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    certificate_no: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EduFavorites(Base):
    __tablename__ = "edu_favorites"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EduProviders(Base):
    __tablename__ = "edu_providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, comment="KFQ, KSA, KMA 등")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    biz_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ceo_name: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    reg_no: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, comment="훈련기관 인정번호")
    type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hrd_partner: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, comment="고용보험 환급 파트너")
    cpd_accredited: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, comment="심사원 CPD 인정기관")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="대표 계정 (users.id)")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EduReviews(Base):
    __tablename__ = "edu_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class EduSessions(Base):
    __tablename__ = "edu_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False)
    session_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, comment="서울/부산/대구/광주/대전/온라인")
    venue_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    venue_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    online_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enrolled: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    instructor_name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
