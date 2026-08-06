"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlatformContactsStatus, PlatformContactsType, PlatformFaqCategory, PlatformNoticesType


class PlatformContactsBase(BaseModel):
    name: str
    email: str
    type: Optional[PlatformContactsType] = None
    subject: str
    message: str
    reply: Optional[str] = None
    status: Optional[PlatformContactsStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlatformContactsCreate(PlatformContactsBase):
    pass


class PlatformContactsUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    type: Optional[PlatformContactsType] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    reply: Optional[str] = None
    status: Optional[PlatformContactsStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlatformContactsResponse(PlatformContactsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PlatformFaqBase(BaseModel):
    category: Optional[PlatformFaqCategory] = None
    question: str
    answer: str
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class PlatformFaqCreate(PlatformFaqBase):
    pass


class PlatformFaqUpdate(BaseModel):
    category: Optional[PlatformFaqCategory] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class PlatformFaqResponse(PlatformFaqBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PlatformNoticesBase(BaseModel):
    notice_date: date
    type: Optional[PlatformNoticesType] = None
    title: str
    content: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlatformNoticesCreate(PlatformNoticesBase):
    pass


class PlatformNoticesUpdate(BaseModel):
    notice_date: Optional[date] = None
    type: Optional[PlatformNoticesType] = None
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PlatformNoticesResponse(PlatformNoticesBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class PlatformSettingsBase(BaseModel):
    value: str
    updated_at: datetime


class PlatformSettingsCreate(PlatformSettingsBase):
    pass


class PlatformSettingsUpdate(BaseModel):
    value: Optional[str] = None
    updated_at: Optional[datetime] = None


class PlatformSettingsResponse(PlatformSettingsBase):
    key: str
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
