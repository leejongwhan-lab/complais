"""company_aspects — EMS / OHS / EnMS characteristic JSON per company."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyAspects(Base):
    __tablename__ = "company_aspects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    ems_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    ohs_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    enms_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
