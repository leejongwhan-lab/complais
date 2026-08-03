"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionSeatsSeatType, SubscriptionsStatus


class SubscriptionPlansBase(BaseModel):
    name: str
    base_seats: int
    price_per_extra_seat: int
    auditor_seat_price: int
    is_active: bool
    created_at: Optional[datetime] = None


class SubscriptionPlansCreate(SubscriptionPlansBase):
    pass


class SubscriptionPlansUpdate(BaseModel):
    name: Optional[str] = None
    base_seats: Optional[int] = None
    price_per_extra_seat: Optional[int] = None
    auditor_seat_price: Optional[int] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class SubscriptionPlansResponse(SubscriptionPlansBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SubscriptionSeatsBase(BaseModel):
    subscription_id: int
    user_id: int
    seat_type: Optional[SubscriptionSeatsSeatType] = None
    assigned_at: Optional[datetime] = None


class SubscriptionSeatsCreate(SubscriptionSeatsBase):
    pass


class SubscriptionSeatsUpdate(BaseModel):
    subscription_id: Optional[int] = None
    user_id: Optional[int] = None
    seat_type: Optional[SubscriptionSeatsSeatType] = None
    assigned_at: Optional[datetime] = None


class SubscriptionSeatsResponse(SubscriptionSeatsBase):
    id: int
    assigned_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class SubscriptionsBase(BaseModel):
    cb_id: int
    plan_id: int
    base_seats: int
    extra_seats: int
    total_seats: Optional[int] = None
    status: SubscriptionsStatus
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    memo: Optional[str] = None
    updated_at: Optional[datetime] = None


class SubscriptionsCreate(SubscriptionsBase):
    pass


class SubscriptionsUpdate(BaseModel):
    cb_id: Optional[int] = None
    plan_id: Optional[int] = None
    base_seats: Optional[int] = None
    extra_seats: Optional[int] = None
    total_seats: Optional[int] = None
    status: Optional[SubscriptionsStatus] = None
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    memo: Optional[str] = None
    updated_at: Optional[datetime] = None


class SubscriptionsResponse(SubscriptionsBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
