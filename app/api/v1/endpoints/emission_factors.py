"""Admin 배출계수 마스터 + Enterprise 물질수지/탄소계산 API.

Admin 수정 → emission_factor_master.total_ghg_factor 자동 저장
Enterprise 탄소계산 → 연도·활성 마스터 계수 JOIN (하드코딩 금지)
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.security import CurrentUser, get_current_admin_user, get_current_user
from app.models.master import EmissionFactorMaster
from app.models.misc import MaterialBalanceActuals, MaterialBalanceItems
from app.services import emission_factor as ef_svc

logger = logging.getLogger(__name__)

admin_router = APIRouter(prefix="/admin", tags=["Admin Emission Factors"])
user_router = APIRouter(prefix="/user", tags=["User Material Balance / Carbon"])

_VALID_FUEL_TYPES = {"electricity", "fossil_fuel", "renewable", "steam", "other"}


# ── Schemas ──────────────────────────────────────────────────────

class GwpSettingsOut(BaseModel):
    gwp_ch4: float
    gwp_n2o: float


class GwpSettingsUpdate(BaseModel):
    gwp_ch4: float = Field(..., gt=0)
    gwp_n2o: float = Field(..., gt=0)


class EmissionFactorOut(BaseModel):
    id: int
    fuel_code: str
    fuel_name: str
    fuel_type: Optional[str] = None
    factor_year: int
    factor_co2: float = 0
    factor_ch4: float = 0
    factor_n2o: float = 0
    total_ghg_factor: float = 0
    unit_input: Optional[str] = None
    scope_type: Optional[int] = None
    fuel_category: Optional[str] = None
    fuel_subcategory: Optional[str] = None
    source_name: Optional[str] = None
    source: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class EmissionFactorListOut(BaseModel):
    year: int
    gwp_ch4: float
    gwp_n2o: float
    items: List[EmissionFactorOut]
    total: int


class EmissionFactorUpsert(BaseModel):
    fuel_code: Optional[str] = None
    fuel_name: str
    fuel_type: Optional[str] = "fossil_fuel"
    factor_year: int
    factor_co2: Decimal
    factor_ch4: Optional[Decimal] = Decimal("0")
    factor_n2o: Optional[Decimal] = Decimal("0")
    unit_input: Optional[str] = None
    scope_type: Optional[int] = 1
    fuel_category: Optional[str] = None
    fuel_subcategory: Optional[str] = None
    source_name: Optional[str] = None
    is_active: Optional[bool] = True


class EmissionFactorCopyIn(BaseModel):
    from_year: int
    to_year: int


class MaterialBalanceSaveIn(BaseModel):
    item_id: int
    year: int
    value: Optional[Decimal] = None
    note: Optional[str] = None


class MaterialBalanceSaveOut(BaseModel):
    ok: bool = True
    ghg: float = 0
    factor: Optional[EmissionFactorOut] = None


# ── Admin endpoints ──────────────────────────────────────────────

@admin_router.get("/emission-factors", response_model=EmissionFactorListOut)
def admin_list_emission_factors(
    year: int = Query(default=None, description="적용연도"),
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    y = int(year or datetime.utcnow().year)
    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    rows = ef_svc.list_emission_factors(db, y, active_only=False)
    items = [
        EmissionFactorOut(**ef_svc.serialize_ef(r, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o))
        for r in rows
    ]
    return EmissionFactorListOut(
        year=y,
        gwp_ch4=float(gwp_ch4),
        gwp_n2o=float(gwp_n2o),
        items=items,
        total=len(items),
    )


@admin_router.post("/emission-factors", response_model=EmissionFactorOut, status_code=201)
def admin_create_emission_factor(
    body: EmissionFactorUpsert,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    code = (body.fuel_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="연료코드 필수")
    ftype = (body.fuel_type or "fossil_fuel").strip()
    if ftype not in _VALID_FUEL_TYPES:
        raise HTTPException(status_code=400, detail="연료 유형 오류")
    exists = (
        db.query(EmissionFactorMaster)
        .filter(
            EmissionFactorMaster.fuel_code == code,
            EmissionFactorMaster.factor_year == int(body.factor_year),
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail=f"{code} / {body.factor_year}년 배출계수가 이미 있습니다.",
        )

    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    row = EmissionFactorMaster(
        fuel_code=code,
        fuel_name=body.fuel_name.strip(),
        fuel_type=ftype,
        factor_year=int(body.factor_year),
        factor_co2=body.factor_co2,
        factor_ch4=body.factor_ch4 or Decimal("0"),
        factor_n2o=body.factor_n2o or Decimal("0"),
        unit_input=(body.unit_input or "").strip() or None,
        scope_type=int(body.scope_type or 1),
        fuel_category=(body.fuel_category or "").strip() or None,
        fuel_subcategory=(body.fuel_subcategory or "").strip() or None,
        source_name=(body.source_name or "").strip() or None,
        is_active=True if body.is_active is None else bool(body.is_active),
        created_at=datetime.utcnow(),
    )
    ef_svc.apply_total_ghg_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
    db.add(row)
    db.commit()
    db.refresh(row)
    return EmissionFactorOut(**ef_svc.serialize_ef(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o))


# Static paths BEFORE /{ef_id} so "copy"/"preview-total" are not parsed as ids.
@admin_router.get("/emission-factors/preview-total")
def admin_preview_total(
    factor_co2: float = Query(0),
    factor_ch4: float = Query(0),
    factor_n2o: float = Query(0),
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    """Admin UI 실시간 미리보기 — 저장 전 tCO2eq 합계."""
    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    total = ef_svc.compute_total_ghg_factor(
        factor_co2, factor_ch4, factor_n2o, gwp_ch4, gwp_n2o
    )
    return {
        "total_ghg_factor": float(total),
        "gwp_ch4": float(gwp_ch4),
        "gwp_n2o": float(gwp_n2o),
        "formula": f"CO2 + CH4×{gwp_ch4} + N2O×{gwp_n2o}",
    }


@admin_router.post("/emission-factors/copy")
def admin_copy_emission_factors(
    body: EmissionFactorCopyIn,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    if not body.from_year or not body.to_year or body.from_year == body.to_year:
        raise HTTPException(status_code=400, detail="연도 오류")
    src = ef_svc.list_emission_factors(db, body.from_year, active_only=False)
    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    copied = 0
    for r in src:
        exists = (
            db.query(EmissionFactorMaster)
            .filter(
                EmissionFactorMaster.fuel_code == r.fuel_code,
                EmissionFactorMaster.factor_year == int(body.to_year),
            )
            .first()
        )
        if exists:
            continue
        neo = EmissionFactorMaster(
            fuel_code=r.fuel_code,
            fuel_name=r.fuel_name,
            fuel_type=r.fuel_type,
            factor_year=int(body.to_year),
            factor_co2=r.factor_co2,
            factor_ch4=r.factor_ch4,
            factor_n2o=r.factor_n2o,
            unit_input=r.unit_input,
            scope_type=r.scope_type,
            fuel_category=r.fuel_category,
            fuel_subcategory=r.fuel_subcategory,
            source_name=r.source_name,
            is_active=r.is_active,
            created_at=datetime.utcnow(),
        )
        ef_svc.apply_total_ghg_factor(neo, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
        db.add(neo)
        copied += 1
    db.commit()
    return {"ok": True, "copied": copied}


@admin_router.get("/gwp-settings", response_model=GwpSettingsOut)
def admin_get_gwp(
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    ch4, n2o = ef_svc.get_gwp(db)
    return GwpSettingsOut(gwp_ch4=float(ch4), gwp_n2o=float(n2o))


@admin_router.put("/gwp-settings", response_model=GwpSettingsOut)
def admin_put_gwp(
    body: GwpSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    ef_svc.set_gwp(db, Decimal(str(body.gwp_ch4)), Decimal(str(body.gwp_n2o)))
    db.commit()
    return GwpSettingsOut(gwp_ch4=body.gwp_ch4, gwp_n2o=body.gwp_n2o)


@admin_router.put("/emission-factors/{ef_id}", response_model=EmissionFactorOut)
def admin_update_emission_factor(
    ef_id: int,
    body: EmissionFactorUpsert,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    row = db.get(EmissionFactorMaster, ef_id)
    if row is None:
        raise HTTPException(status_code=404, detail="배출계수를 찾을 수 없습니다.")

    ftype = (body.fuel_type or row.fuel_type or "fossil_fuel").strip()
    if ftype not in _VALID_FUEL_TYPES:
        raise HTTPException(status_code=400, detail="연료 유형 오류")

    row.fuel_name = body.fuel_name.strip()
    row.fuel_type = ftype
    row.factor_year = int(body.factor_year)
    row.factor_co2 = body.factor_co2
    row.factor_ch4 = body.factor_ch4 or Decimal("0")
    row.factor_n2o = body.factor_n2o or Decimal("0")
    row.unit_input = (body.unit_input or "").strip() or None
    row.scope_type = int(body.scope_type or 1)
    row.fuel_category = (body.fuel_category or "").strip() or None
    row.fuel_subcategory = (body.fuel_subcategory or "").strip() or None
    row.source_name = (body.source_name or "").strip() or None
    if body.is_active is not None:
        row.is_active = bool(body.is_active)

    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    ef_svc.apply_total_ghg_factor(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
    db.commit()
    db.refresh(row)
    return EmissionFactorOut(**ef_svc.serialize_ef(row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o))


@admin_router.patch("/emission-factors/{ef_id}/toggle")
def admin_toggle_emission_factor(
    ef_id: int,
    db: Session = Depends(get_db),
    _admin: CurrentUser = Depends(get_current_admin_user),
):
    row = db.get(EmissionFactorMaster, ef_id)
    if row is None:
        raise HTTPException(status_code=404, detail="배출계수를 찾을 수 없습니다.")
    row.is_active = not bool(row.is_active)
    db.commit()
    return {"ok": True, "is_active": bool(row.is_active)}


# ── Enterprise endpoints ─────────────────────────────────────────

@user_router.get("/material-balance")
def user_load_material_balance(
    year: int = Query(default=None),
    company_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    y = int(year or datetime.utcnow().year)
    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)

    items = (
        db.query(MaterialBalanceItems)
        .filter(MaterialBalanceItems.is_active.is_(True))
        .order_by(
            MaterialBalanceItems.category.desc(),
            MaterialBalanceItems.sort_order.asc(),
            MaterialBalanceItems.id.asc(),
        )
        .all()
    )
    actuals = (
        db.query(MaterialBalanceActuals)
        .filter(
            MaterialBalanceActuals.company_id == cid,
            MaterialBalanceActuals.measured_year == y,
        )
        .all()
    )
    act_map = {a.item_id: a for a in actuals}

    # 연도별 활성 배출계수 (fuel_code → row)
    ef_rows = ef_svc.list_emission_factors(db, y, active_only=True)
    ef_by_code = {r.fuel_code: r for r in ef_rows}
    ef_by_id = {r.id: r for r in ef_rows}

    out_items: List[Dict[str, Any]] = []
    carbon_rows: List[Dict[str, Any]] = []
    scope1 = Decimal("0")
    scope2 = Decimal("0")
    sources: List[str] = []

    for it in items:
        act = act_map.get(it.id)
        fuel_code = ef_svc.resolve_fuel_code_for_item(db, it)
        ef_row = ef_by_code.get(fuel_code) if fuel_code else None
        # fallback: linked id if same year
        if ef_row is None and it.emission_factor_id:
            ef_row = ef_by_id.get(it.emission_factor_id)

        ef_payload = (
            ef_svc.serialize_ef(ef_row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
            if ef_row
            else None
        )
        measured = float(act.measured_value) if act and act.measured_value is not None else None
        # 저장값 우선, 없으면 실시간 재계산 (마스터 변경 즉시 반영)
        if measured is not None and ef_row is not None:
            ghg = float(ef_svc.calc_ghg(measured, ef_row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o))
        elif act and act.ghg_calc is not None:
            ghg = float(act.ghg_calc)
        else:
            ghg = 0.0

        item_payload = {
            "id": it.id,
            "item_code": it.item_code,
            "category": it.category,
            "item_type": it.item_type,
            "item_name": it.item_name,
            "unit": it.unit,
            "is_energy": bool(it.is_energy),
            "emission_factor_id": it.emission_factor_id,
            "kpi_code": it.kpi_code,
            "sort_order": it.sort_order,
            "measured_value": measured,
            "ghg_calc": ghg,
            "note": act.note if act else None,
            "ef": ef_payload,
        }
        out_items.append(item_payload)

        if it.is_energy:
            carbon_rows.append(item_payload)
            if ef_row and ghg > 0:
                st = int(ef_row.scope_type or 0)
                if st == 1:
                    scope1 += Decimal(str(ghg))
                elif st == 2:
                    scope2 += Decimal(str(ghg))
                if ef_row.source_name and ef_row.source_name not in sources:
                    sources.append(ef_row.source_name)

    total = scope1 + scope2
    return {
        "ok": True,
        "year": y,
        "gwp_ch4": float(gwp_ch4),
        "gwp_n2o": float(gwp_n2o),
        "items": out_items,
        "emission_factors": [
            ef_svc.serialize_ef(r, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o) for r in ef_rows
        ],
        "carbon": {
            "scope1": float(scope1),
            "scope2": float(scope2),
            "total": float(total),
            "rows": carbon_rows,
            "sources": sources,
        },
    }


@user_router.post("/material-balance", response_model=MaterialBalanceSaveOut)
def user_save_material_balance(
    body: MaterialBalanceSaveIn,
    company_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    if not body.item_id or not body.year:
        raise HTTPException(status_code=400, detail="파라미터 오류")

    item = db.get(MaterialBalanceItems, body.item_id)
    if item is None or not item.is_active:
        raise HTTPException(status_code=404, detail="물질수지 항목 없음")

    gwp_ch4, gwp_n2o = ef_svc.get_gwp(db)
    ef_row = ef_svc.get_emission_factor_for_item(db, item, body.year, active_only=True)
    ghg = (
        ef_svc.calc_ghg(body.value, ef_row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o)
        if body.value is not None
        else Decimal("0")
    )

    now = datetime.utcnow()
    act = (
        db.query(MaterialBalanceActuals)
        .filter(
            MaterialBalanceActuals.company_id == cid,
            MaterialBalanceActuals.item_id == body.item_id,
            MaterialBalanceActuals.measured_year == int(body.year),
        )
        .first()
    )
    if act is None:
        act = MaterialBalanceActuals(
            company_id=cid,
            item_id=body.item_id,
            measured_year=int(body.year),
            created_at=now,
        )
        db.add(act)

    act.measured_value = body.value
    act.ghg_calc = ghg if body.value is not None else Decimal("0")
    act.note = body.note
    act.updated_at = now
    db.commit()

    factor_out = (
        EmissionFactorOut(**ef_svc.serialize_ef(ef_row, gwp_ch4=gwp_ch4, gwp_n2o=gwp_n2o))
        if ef_row
        else None
    )
    return MaterialBalanceSaveOut(ok=True, ghg=float(ghg), factor=factor_out)


@user_router.get("/carbon")
def user_carbon_summary(
    year: int = Query(default=None),
    company_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """탄소계산 전용 — material-balance.carbon 과 동일 소스."""
    data = user_load_material_balance(
        year=year, company_id=company_id, db=db, current_user=current_user
    )
    return {
        "ok": True,
        "year": data["year"],
        "gwp_ch4": data["gwp_ch4"],
        "gwp_n2o": data["gwp_n2o"],
        **data["carbon"],
        "emission_factors": data["emission_factors"],
    }
