"""가격·출장·할인 정책 ORM."""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    func,
)

from app.core.database import Base


class StandardPriceMasterRow(Base):
    __tablename__ = "standard_price_masters"

    id = Column(String(40), primary_key=True)
    standard_code = Column(String(20), nullable=False, index=True)
    base_price_per_md = Column(Numeric(15, 2), nullable=False)
    minimum_md = Column(Numeric(8, 2), nullable=False, default=1)
    currency = Column(String(10), nullable=False, default="KRW")
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class TravelExpensePolicyRow(Base):
    __tablename__ = "travel_expense_policies"

    region_code = Column(String(40), primary_key=True)
    region_name = Column(String(80), nullable=False)
    per_diem_per_md = Column(Numeric(15, 2), nullable=False, default=0)
    accommodation_per_night = Column(Numeric(15, 2), nullable=False, default=0)
    flat_travel_fee = Column(Numeric(15, 2), nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class DiscountPolicyRow(Base):
    __tablename__ = "discount_policies"

    discount_code = Column(String(40), primary_key=True)
    discount_name = Column(String(120), nullable=False)
    discount_type = Column(String(20), nullable=False)  # PERCENTAGE | FIXED_AMOUNT
    value = Column(Numeric(15, 2), nullable=False)
    max_discount_amount = Column(Numeric(15, 2), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
