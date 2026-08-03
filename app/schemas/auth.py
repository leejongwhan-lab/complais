"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InvitationsRole, InvitationsStatus, NotificationsChannel, TenantsCbType, TenantsPlanType, TenantsStatus, UsersMemberType, UsersRole


class InvitationsBase(BaseModel):
    cb_id: int
    invited_by: int
    email: str
    role: InvitationsRole
    token: str
    status: InvitationsStatus
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class InvitationsCreate(InvitationsBase):
    pass


class InvitationsUpdate(BaseModel):
    cb_id: Optional[int] = None
    invited_by: Optional[int] = None
    email: Optional[str] = None
    role: Optional[InvitationsRole] = None
    token: Optional[str] = None
    status: Optional[InvitationsStatus] = None
    expires_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class InvitationsResponse(InvitationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class NotificationsBase(BaseModel):
    user_id: int
    type: str
    title: str
    body: Optional[str] = None
    link: Optional[str] = None
    channel: NotificationsChannel
    is_read: bool
    sent_at: datetime


class NotificationsCreate(NotificationsBase):
    pass


class NotificationsUpdate(BaseModel):
    user_id: Optional[int] = None
    type: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    link: Optional[str] = None
    channel: Optional[NotificationsChannel] = None
    is_read: Optional[bool] = None
    sent_at: Optional[datetime] = None


class NotificationsResponse(NotificationsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TenantsBase(BaseModel):
    cb_id: int
    cb_type: TenantsCbType
    plan_type: TenantsPlanType
    status: TenantsStatus
    activated_at: Optional[date] = None
    expires_at: Optional[date] = None
    max_auditors: int
    max_contracts_pm: int
    base_fee: Decimal = Field(description="기본금(인증기관) / 월구독료(컨설팅)")
    per_auditor_fee: Decimal = Field(description="심사원 1인당 단가(인증기관)")
    current_auditors: int = Field(description="현재 등록 심사원 수")
    credit_balance: Decimal = Field(description="크레딧 잔액(교육기관)")
    credit_per_day: Decimal = Field(description="홍보 노출 1일당 차감 크레딧")
    consulting_fee: Decimal = Field(description="컨설팅 월구독료")
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TenantsCreate(TenantsBase):
    pass


class TenantsUpdate(BaseModel):
    cb_id: Optional[int] = None
    cb_type: Optional[TenantsCbType] = None
    plan_type: Optional[TenantsPlanType] = None
    status: Optional[TenantsStatus] = None
    activated_at: Optional[date] = None
    expires_at: Optional[date] = None
    max_auditors: Optional[int] = None
    max_contracts_pm: Optional[int] = None
    base_fee: Optional[Decimal] = None
    per_auditor_fee: Optional[Decimal] = None
    current_auditors: Optional[int] = None
    credit_balance: Optional[Decimal] = None
    credit_per_day: Optional[Decimal] = None
    consulting_fee: Optional[Decimal] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TenantsResponse(TenantsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UsersBase(BaseModel):
    member_no: Optional[int] = None
    member_type: Optional[UsersMemberType] = None
    complais_no: Optional[str] = Field(default=None, description="ComplAIs 개인번호 (YYYYMMDD-NNN)")
    email: str
    password_hash: str
    name: str
    role: UsersRole
    cb_id: Optional[int] = None
    company_id: Optional[int] = None
    phone: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    status: str


class UsersCreate(UsersBase):
    pass


class UsersUpdate(BaseModel):
    member_no: Optional[int] = None
    member_type: Optional[UsersMemberType] = None
    complais_no: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None
    name: Optional[str] = None
    role: Optional[UsersRole] = None
    cb_id: Optional[int] = None
    company_id: Optional[int] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: Optional[str] = None


class UsersResponse(UsersBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
