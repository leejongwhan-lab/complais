"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EduCoursesDeliveryMode, EduCoursesStatus, EduEnrollmentsPaymentStatus, EduEnrollmentsRefundStatus, EduEnrollmentsStatus, EduProvidersStatus, EduProvidersType, EduSessionsStatus


class EduCategoriesBase(BaseModel):
    parent_id: Optional[int] = None
    level: int = Field(description="1=대분류 2=세부분야")
    code: str
    name: str
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class EduCategoriesCreate(EduCategoriesBase):
    pass


class EduCategoriesUpdate(BaseModel):
    parent_id: Optional[int] = None
    level: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class EduCategoriesResponse(EduCategoriesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class EduCoursesBase(BaseModel):
    provider_id: int
    category_id: int = Field(description="세부분야 (level=2)")
    course_code: Optional[str] = None
    title: str
    title_en: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    objectives: Optional[str] = None
    curriculum_json: Optional[str] = Field(default=None, description="[{day,topic,hours}]")
    prerequisites: Optional[str] = None
    delivery_mode: EduCoursesDeliveryMode
    duration_days: Optional[Decimal] = None
    duration_hours: Optional[int] = None
    price_regular: int
    price_discount: Optional[int] = None
    refund_eligible: Optional[int] = None
    ceo_point: Optional[int] = None
    certificate_issue: Optional[int] = None
    cpd_credit_hours: Optional[int] = None
    iso_standard: Optional[str] = Field(default=None, description="예: 9001, 14001, 42001")
    status: Optional[EduCoursesStatus] = None
    published_at: Optional[datetime] = None
    view_count: Optional[int] = None
    apply_count: Optional[int] = None
    rating_avg: Optional[Decimal] = None
    rating_count: Optional[int] = None
    thumbnail_path: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduCoursesCreate(EduCoursesBase):
    pass


class EduCoursesUpdate(BaseModel):
    provider_id: Optional[int] = None
    category_id: Optional[int] = None
    course_code: Optional[str] = None
    title: Optional[str] = None
    title_en: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    objectives: Optional[str] = None
    curriculum_json: Optional[str] = None
    prerequisites: Optional[str] = None
    delivery_mode: Optional[EduCoursesDeliveryMode] = None
    duration_days: Optional[Decimal] = None
    duration_hours: Optional[int] = None
    price_regular: Optional[int] = None
    price_discount: Optional[int] = None
    refund_eligible: Optional[int] = None
    ceo_point: Optional[int] = None
    certificate_issue: Optional[int] = None
    cpd_credit_hours: Optional[int] = None
    iso_standard: Optional[str] = None
    status: Optional[EduCoursesStatus] = None
    published_at: Optional[datetime] = None
    view_count: Optional[int] = None
    apply_count: Optional[int] = None
    rating_avg: Optional[Decimal] = None
    rating_count: Optional[int] = None
    thumbnail_path: Optional[str] = None
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduCoursesResponse(EduCoursesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EduEnrollmentsBase(BaseModel):
    session_id: int
    company_id: Optional[int] = None
    auditor_id: Optional[int] = None
    applicant_user_id: Optional[int] = None
    student_name: str
    student_email: str
    student_phone: Optional[str] = None
    student_position: Optional[str] = None
    student_dept: Optional[str] = None
    emp_insurance_no: Optional[str] = Field(default=None, description="고용보험 피보험자번호")
    status: Optional[EduEnrollmentsStatus] = None
    payment_status: Optional[EduEnrollmentsPaymentStatus] = None
    paid_amount: Optional[int] = None
    invoice_no: Optional[str] = None
    refund_status: Optional[EduEnrollmentsRefundStatus] = None
    refund_amount: Optional[int] = None
    attended_hours: Optional[int] = None
    completion_rate: Optional[Decimal] = None
    certificate_no: Optional[str] = None
    score: Optional[Decimal] = None
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduEnrollmentsCreate(EduEnrollmentsBase):
    pass


class EduEnrollmentsUpdate(BaseModel):
    session_id: Optional[int] = None
    company_id: Optional[int] = None
    auditor_id: Optional[int] = None
    applicant_user_id: Optional[int] = None
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    student_phone: Optional[str] = None
    student_position: Optional[str] = None
    student_dept: Optional[str] = None
    emp_insurance_no: Optional[str] = None
    status: Optional[EduEnrollmentsStatus] = None
    payment_status: Optional[EduEnrollmentsPaymentStatus] = None
    paid_amount: Optional[int] = None
    invoice_no: Optional[str] = None
    refund_status: Optional[EduEnrollmentsRefundStatus] = None
    refund_amount: Optional[int] = None
    attended_hours: Optional[int] = None
    completion_rate: Optional[Decimal] = None
    certificate_no: Optional[str] = None
    score: Optional[Decimal] = None
    applied_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduEnrollmentsResponse(EduEnrollmentsBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EduFavoritesBase(BaseModel):
    created_at: Optional[datetime] = None


class EduFavoritesCreate(EduFavoritesBase):
    pass


class EduFavoritesUpdate(BaseModel):
    created_at: Optional[datetime] = None


class EduFavoritesResponse(EduFavoritesBase):
    user_id: int
    course_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EduProvidersBase(BaseModel):
    code: str = Field(description="KFQ, KSA, KMA 등")
    name: str
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    ceo_name: Optional[str] = None
    reg_no: Optional[str] = Field(default=None, description="훈련기관 인정번호")
    type: Optional[EduProvidersType] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    intro: Optional[str] = None
    logo_path: Optional[str] = None
    hrd_partner: Optional[int] = Field(default=None, description="고용보험 환급 파트너")
    cpd_accredited: Optional[int] = Field(default=None, description="심사원 CPD 인정기관")
    status: Optional[EduProvidersStatus] = None
    owner_user_id: Optional[int] = Field(default=None, description="대표 계정 (users.id)")
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduProvidersCreate(EduProvidersBase):
    pass


class EduProvidersUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    biz_no: Optional[str] = None
    ceo_name: Optional[str] = None
    reg_no: Optional[str] = None
    type: Optional[EduProvidersType] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    intro: Optional[str] = None
    logo_path: Optional[str] = None
    hrd_partner: Optional[int] = None
    cpd_accredited: Optional[int] = None
    status: Optional[EduProvidersStatus] = None
    owner_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduProvidersResponse(EduProvidersBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EduReviewsBase(BaseModel):
    enrollment_id: int
    course_id: int
    rating: int
    comment: Optional[str] = None
    is_public: Optional[bool] = None
    created_at: Optional[datetime] = None


class EduReviewsCreate(EduReviewsBase):
    pass


class EduReviewsUpdate(BaseModel):
    enrollment_id: Optional[int] = None
    course_id: Optional[int] = None
    rating: Optional[int] = None
    comment: Optional[str] = None
    is_public: Optional[bool] = None
    created_at: Optional[datetime] = None


class EduReviewsResponse(EduReviewsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class EduSessionsBase(BaseModel):
    course_id: int
    session_code: Optional[str] = None
    start_date: date
    end_date: date
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    region: Optional[str] = Field(default=None, description="서울/부산/대구/광주/대전/온라인")
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    online_url: Optional[str] = None
    capacity: Optional[int] = None
    enrolled: Optional[int] = None
    instructor_name: Optional[str] = None
    status: Optional[EduSessionsStatus] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduSessionsCreate(EduSessionsBase):
    pass


class EduSessionsUpdate(BaseModel):
    course_id: Optional[int] = None
    session_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    region: Optional[str] = None
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    online_url: Optional[str] = None
    capacity: Optional[int] = None
    enrolled: Optional[int] = None
    instructor_name: Optional[str] = None
    status: Optional[EduSessionsStatus] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EduSessionsResponse(EduSessionsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
