"""배출계수 마스터 조회·tCO2eq 합계 계산.

Admin 미리보기와 Enterprise 물질수지/탄소계산이 동일 로직을 공유한다.
  GHG = usage × total_ghg_factor
  total_ghg_factor = CO2 + CH4×GWP_CH4 + N2O×GWP_N2O
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple, Union

from sqlalchemy.orm import Session

from app.models.master import EmissionFactorMaster
from app.models.misc import MaterialBalanceItems
from app.models.platform import PlatformSettings

DEFAULT_GWP_CH4 = Decimal("27.9")
DEFAULT_GWP_N2O = Decimal("273")
_Q8 = Decimal("0.00000001")
_Q6 = Decimal("0.000001")


def _d(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def get_gwp(db: Session) -> Tuple[Decimal, Decimal]:
    """platform_settings에서 GWP 조회 (없으면 IPCC AR6 기본값)."""
    ch4, n2o = DEFAULT_GWP_CH4, DEFAULT_GWP_N2O
    rows = (
        db.query(PlatformSettings)
        .filter(PlatformSettings.key.in_(("gwp_ch4", "gwp_n2o")))
        .all()
    )
    for row in rows:
        try:
            val = Decimal(str(row.value).strip())
        except Exception:
            continue
        if row.key == "gwp_ch4" and val > 0:
            ch4 = val
        elif row.key == "gwp_n2o" and val > 0:
            n2o = val
    return ch4, n2o


def set_gwp(db: Session, gwp_ch4: Decimal, gwp_n2o: Decimal) -> None:
    """GWP 저장 후 활성 배출계수의 total_ghg_factor를 재계산."""
    now = datetime.utcnow()
    for key, value in (("gwp_ch4", gwp_ch4), ("gwp_n2o", gwp_n2o)):
        row = db.get(PlatformSettings, key)
        if row is None:
            db.add(PlatformSettings(key=key, value=str(value), updated_at=now))
        else:
            row.value = str(value)
            row.updated_at = now
    db.flush()
    recompute_all_totals(db, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)


def compute_total_ghg_factor(
    factor_co2: Any,
    factor_ch4: Any = 0,
    factor_n2o: Any = 0,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
) -> Decimal:
    """tCO2eq합계 = CO2 + CH4×GWP_CH4 + N2O×GWP_N2O."""
    ch4_gwp = gwp_ch4 if gwp_ch4 is not None else DEFAULT_GWP_CH4
    n2o_gwp = gwp_n2o if gwp_n2o is not None else DEFAULT_GWP_N2O
    total = _d(factor_co2) + _d(factor_ch4) * _d(ch4_gwp) + _d(factor_n2o) * _d(n2o_gwp)
    return total.quantize(_Q8, rounding=ROUND_HALF_UP)


def apply_total_ghg_factor(
    row: EmissionFactorMaster,
    *,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
    db: Optional[Session] = None,
) -> Decimal:
    """행의 total_ghg_factor를 계산·저장하고 반환."""
    if gwp_ch4 is None or gwp_n2o is None:
        if db is not None:
            gwp_ch4, gwp_n2o = get_gwp(db)
        else:
            gwp_ch4 = gwp_ch4 or DEFAULT_GWP_CH4
            gwp_n2o = gwp_n2o or DEFAULT_GWP_N2O
    total = compute_total_ghg_factor(
        row.factor_co2, row.factor_ch4, row.factor_n2o, gwp_ch4, gwp_n2o
    )
    row.total_ghg_factor = total
    return total


def recompute_all_totals(
    db: Session,
    *,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
) -> int:
    if gwp_ch4 is None or gwp_n2o is None:
        gwp_ch4, gwp_n2o = get_gwp(db)
    rows = db.query(EmissionFactorMaster).all()
    for row in rows:
        apply_total_ghg_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
    return len(rows)


def get_emission_factor(
    db: Session,
    year: int,
    fuel_type: str,
    *,
    active_only: bool = True,
) -> Optional[EmissionFactorMaster]:
    """연도·연료 키로 활성 배출계수 1건 조회.

    fuel_type: fuel_code / fuel_name / fuel_type(enum) 중 하나.
    """
    key = (fuel_type or "").strip()
    if not year or not key:
        return None

    q = db.query(EmissionFactorMaster).filter(
        EmissionFactorMaster.factor_year == int(year)
    )
    if active_only:
        q = q.filter(EmissionFactorMaster.is_active.is_(True))

    row = q.filter(EmissionFactorMaster.fuel_code == key).first()
    if row:
        return row
    row = q.filter(EmissionFactorMaster.fuel_name == key).first()
    if row:
        return row
    return q.filter(EmissionFactorMaster.fuel_type == key).first()


def resolve_fuel_code_for_item(
    db: Session, item: Union[MaterialBalanceItems, Any]
) -> Optional[str]:
    """물질수지 항목 → 배출계수 fuel_code."""
    ef_id = getattr(item, "emission_factor_id", None)
    if ef_id:
        linked = db.get(EmissionFactorMaster, int(ef_id))
        if linked and linked.fuel_code:
            return linked.fuel_code
    item_code = getattr(item, "item_code", None)
    return item_code or None


def get_emission_factor_for_item(
    db: Session,
    item: Union[MaterialBalanceItems, Any],
    year: int,
    *,
    active_only: bool = True,
) -> Optional[EmissionFactorMaster]:
    """항목의 연결 fuel_code로 해당 연도 활성 계수를 조회."""
    fuel_code = resolve_fuel_code_for_item(db, item)
    if not fuel_code:
        return None
    return get_emission_factor(db, year, fuel_code, active_only=active_only)


def effective_total_factor(
    row: Optional[EmissionFactorMaster],
    *,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
    db: Optional[Session] = None,
) -> Decimal:
    if row is None:
        return Decimal("0")
    if row.total_ghg_factor is not None:
        return _d(row.total_ghg_factor)
    return apply_total_ghg_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o, db=db)


def calc_ghg(
    usage: Any,
    row: Optional[EmissionFactorMaster],
    *,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
    db: Optional[Session] = None,
) -> Decimal:
    """GHG(tCO2eq) = usage × year master emission factor."""
    if usage is None or row is None:
        return Decimal("0")
    factor = effective_total_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o, db=db)
    if factor <= 0:
        return Decimal("0")
    return (_d(usage) * factor).quantize(_Q6, rounding=ROUND_HALF_UP)


def serialize_ef(
    row: EmissionFactorMaster,
    *,
    gwp_ch4: Optional[Decimal] = None,
    gwp_n2o: Optional[Decimal] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    total = effective_total_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o, db=db)
    return {
        "id": row.id,
        "fuel_code": row.fuel_code,
        "fuel_name": row.fuel_name,
        "fuel_type": row.fuel_type,
        "factor_year": row.factor_year,
        "factor_co2": float(_d(row.factor_co2)),
        "factor_ch4": float(_d(row.factor_ch4)),
        "factor_n2o": float(_d(row.factor_n2o)),
        "total_ghg_factor": float(total),
        "unit_input": row.unit_input,
        "scope_type": row.scope_type,
        "fuel_category": row.fuel_category,
        "fuel_subcategory": row.fuel_subcategory,
        "source_name": row.source_name,
        "source": row.source_name,
        "is_active": bool(row.is_active) if row.is_active is not None else True,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_emission_factors(
    db: Session,
    year: int,
    *,
    active_only: bool = False,
) -> list[EmissionFactorMaster]:
    q = db.query(EmissionFactorMaster).filter(
        EmissionFactorMaster.factor_year == int(year)
    )
    if active_only:
        q = q.filter(EmissionFactorMaster.is_active.is_(True))
    return (
        q.order_by(
            EmissionFactorMaster.scope_type.asc(),
            EmissionFactorMaster.fuel_category.asc(),
            EmissionFactorMaster.fuel_subcategory.asc(),
            EmissionFactorMaster.id.asc(),
        )
        .all()
    )
