"""emission_factor_master.total_ghg_factor — tCO2eq 합계 저장

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-07

Admin이 CO2/CH4/N2O를 수정하면
  total = CO2 + CH4×GWP_CH4 + N2O×GWP_N2O
를 저장한다. Additive ALTER only. No DROP/TRUNCATE.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    if not _has_table("emission_factor_master"):
        return
    if not _has_column("emission_factor_master", "total_ghg_factor"):
        op.add_column(
            "emission_factor_master",
            sa.Column(
                "total_ghg_factor",
                sa.Numeric(precision=18, scale=8),
                nullable=True,
                comment="tCO2eq합계 = CO2 + CH4×GWP_CH4 + N2O×GWP_N2O",
            ),
        )

    # Backfill from current GWP settings (defaults AR6: 27.9 / 273)
    conn = op.get_bind()
    gwp_ch4 = 27.9
    gwp_n2o = 273.0
    if _has_table("platform_settings"):
        rows = conn.execute(
            text(
                "SELECT `key`, value FROM platform_settings "
                "WHERE `key` IN ('gwp_ch4', 'gwp_n2o')"
            )
        ).fetchall()
        for key, value in rows:
            try:
                if key == "gwp_ch4":
                    gwp_ch4 = float(value)
                elif key == "gwp_n2o":
                    gwp_n2o = float(value)
            except (TypeError, ValueError):
                pass

    conn.execute(
        text(
            "UPDATE emission_factor_master SET total_ghg_factor = "
            "COALESCE(factor_co2, 0) + COALESCE(factor_ch4, 0) * :gwp_ch4 "
            "+ COALESCE(factor_n2o, 0) * :gwp_n2o "
            "WHERE total_ghg_factor IS NULL"
        ),
        {"gwp_ch4": gwp_ch4, "gwp_n2o": gwp_n2o},
    )


def downgrade() -> None:
    if _has_column("emission_factor_master", "total_ghg_factor"):
        op.drop_column("emission_factor_master", "total_ghg_factor")
