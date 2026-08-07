"""KAB-AR-MD17 / IAF MD 17 Witness Assessment models."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WitnessingScheme(Base):
    __tablename__ = "witnessing_schemes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name_kr: Mapped[str] = mapped_column(String(100), nullable=False)
    iso_ref: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    has_cluster_logic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    cycle_years_default: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default=text("5")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )


class TechnicalCluster(Base):
    __tablename__ = "technical_clusters"
    __table_args__ = (
        UniqueConstraint("scheme_id", "cluster_code", name="uk_tech_clusters_scheme_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("witnessing_schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name_kr: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )


class WitnessingIafTemplate(Base):
    """Global IAF template per scheme — copied into witnessing_codes per CB."""

    __tablename__ = "witnessing_iaf_templates"
    __table_args__ = (
        UniqueConstraint("scheme_id", "iaf_code", name="uk_wit_tmpl_scheme_iaf"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scheme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("witnessing_schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("technical_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    eligible_for_coverage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    cycle_years: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default=text("5")
    )


class WitnessingCode(Base):
    __tablename__ = "witnessing_codes"
    __table_args__ = (
        UniqueConstraint(
            "cb_id", "scheme_id", "iaf_code", name="uk_wit_codes_cb_scheme_iaf"
        ),
    )

    id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True), primary_key=True, autoincrement=True
    )
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheme_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("witnessing_schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    cluster_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("technical_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )
    iaf_code: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_critical: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    eligible_for_coverage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    cycle_years: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default=text("5")
    )
    last_witness_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_auto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
