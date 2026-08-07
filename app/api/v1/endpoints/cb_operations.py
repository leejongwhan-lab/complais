"""CB Portal — 인증원 운영 (Witness Assessment / KAB-AR-MD17 & IAF MD 17).

Auth: require_cb_portal_user (platform_admin 금지).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_cb_portal_user
from app.db.session import get_db
from app.models.witnessing import WitnessingCode, WitnessingScheme
from app.schemas.cb_operations import (
    WitnessCodeRow,
    WitnessCompleteRequest,
    WitnessCompleteResponse,
    WitnessDashboardResponse,
    WitnessSchemeTab,
    WitnessSettingsItem,
    WitnessSettingsPutRequest,
    WitnessSettingsResponse,
    WitnessSummary,
)
from app.services import cb_witnessing as wit

router = APIRouter(prefix="/cb-admin/operations", tags=["CB Operations"])
logger = logging.getLogger(__name__)


def _scheme_tab(s: WitnessingScheme) -> WitnessSchemeTab:
    return WitnessSchemeTab(
        id=s.id,
        code=s.code,
        name_kr=s.name_kr,
        iso_ref=s.iso_ref,
        label=wit.scheme_label(s),
        has_cluster_logic=bool(s.has_cluster_logic),
    )


def _resolve_scheme(db: Session, scheme_q: Optional[str]) -> WitnessingScheme:
    q = (scheme_q or "").strip()
    query = db.query(WitnessingScheme).filter(WitnessingScheme.is_active.is_(True))
    if q:
        row = query.filter(WitnessingScheme.code == q).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"scheme not found: {q}")
        return row
    row = query.order_by(WitnessingScheme.sort_order).first()
    if not row:
        raise HTTPException(status_code=404, detail="witnessing_schemes empty — run migration")
    return row


def _cb_schemes(db: Session, cb_id: int) -> List[WitnessingScheme]:
    codes = wit.cb_accredited_scheme_codes(db, cb_id)
    rows = (
        db.query(WitnessingScheme)
        .filter(
            WitnessingScheme.is_active.is_(True),
            WitnessingScheme.code.in_(codes) if codes else True,
        )
        .order_by(WitnessingScheme.sort_order)
        .all()
    )
    if not rows:
        rows = (
            db.query(WitnessingScheme)
            .filter(WitnessingScheme.is_active.is_(True))
            .order_by(WitnessingScheme.sort_order)
            .all()
        )
    return rows


def _row_payload(
    row: WitnessingCode,
    scheme: WitnessingScheme,
    cluster_names: dict,
    db: Session,
    cb_id: int,
) -> WitnessCodeRow:
    st = wit.compute_status(row.last_witness_date, row.next_due_date)
    others = wit.find_same_iaf_other_schemes(db, cb_id, row.iaf_code, row.scheme_id)
    other_payload = []
    for o in others:
        sch = db.get(WitnessingScheme, o.scheme_id)
        other_payload.append(
            {
                "id": o.id,
                "scheme_id": o.scheme_id,
                "scheme_code": sch.code if sch else str(o.scheme_id),
                "label": wit.scheme_label(sch) if sch else str(o.scheme_id),
                "status": wit.compute_status(o.last_witness_date, o.next_due_date),
            }
        )
    return WitnessCodeRow(
        id=row.id,
        scheme_id=row.scheme_id,
        scheme_code=scheme.code,
        cluster_id=row.cluster_id,
        cluster_name=cluster_names.get(row.cluster_id) if row.cluster_id else None,
        iaf_code=row.iaf_code,
        description=row.description,
        is_critical=bool(row.is_critical),
        eligible_for_coverage=bool(row.eligible_for_coverage),
        cycle_years=int(row.cycle_years or 5),
        last_witness_date=row.last_witness_date,
        next_due_date=row.next_due_date,
        is_auto=bool(row.is_auto),
        status=st,
        same_iaf_other_schemes=other_payload,
    )


@router.get("/witnessing", response_model=WitnessDashboardResponse)
def get_witnessing_dashboard(
    scheme: Optional[str] = Query(None, description="QMS|EMS|OHSMS|ISMS…"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    cb_id = int(current_user.cb_id)
    schemes = _cb_schemes(db, cb_id)
    tabs = [_scheme_tab(s) for s in schemes]
    if not tabs:
        return WitnessDashboardResponse(
            schemes=[], scheme=None, summary=WitnessSummary(), items=[]
        )

    # Prefer requested scheme if CB holds it; else first accredited
    if scheme:
        active = next((s for s in schemes if s.code == scheme), None)
        if active is None:
            # still allow viewing any seeded scheme
            active = _resolve_scheme(db, scheme)
    else:
        active = schemes[0]

    try:
        wit.ensure_cb_codes(db, cb_id, active)
        db.commit()
    except Exception as exc:
        logger.exception("ensure_cb_codes failed")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"seed witnessing codes failed: {exc}") from exc

    cluster_names = wit.cluster_name_map(db, active.id)
    rows = (
        db.query(WitnessingCode)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.scheme_id == active.id,
        )
        .order_by(WitnessingCode.iaf_code)
        .all()
    )
    items = [_row_payload(r, active, cluster_names, db, cb_id) for r in rows]
    summary = WitnessSummary(
        total=len(items),
        due_soon=sum(1 for i in items if i.status == wit.STATUS_DUE),
        expired=sum(1 for i in items if i.status == wit.STATUS_EXPIRED),
        missing=sum(1 for i in items if i.status == wit.STATUS_MISSING),
    )
    return WitnessDashboardResponse(
        schemes=tabs,
        scheme=_scheme_tab(active),
        summary=summary,
        items=items,
    )


@router.post(
    "/witnessing/{code_id}/complete",
    response_model=WitnessCompleteResponse,
)
def complete_witnessing(
    code_id: int,
    payload: WitnessCompleteRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    cb_id = int(current_user.cb_id)
    row = (
        db.query(WitnessingCode)
        .filter(WitnessingCode.id == code_id, WitnessingCode.cb_id == cb_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="witnessing code not found")
    scheme = db.get(WitnessingScheme, row.scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="scheme not found")

    witness_date = payload.last_witness_date
    if witness_date > date.today():
        raise HTTPException(status_code=400, detail="last_witness_date cannot be in the future")

    updated: List[int] = []
    auto_ids: List[int] = []
    integrated: List[int] = []

    try:
        wit.apply_complete(row, witness_date, is_auto=False)
        updated.append(row.id)
        db.flush()

        auto_ids = wit.auto_propagate_cluster(
            db, cb_id, scheme, row, witness_date
        )
        db.flush()

        if payload.complete_integrated:
            others = wit.find_same_iaf_other_schemes(
                db, cb_id, row.iaf_code, row.scheme_id
            )
            for o in others:
                o_scheme = db.get(WitnessingScheme, o.scheme_id)
                wit.apply_complete(o, witness_date, is_auto=False)
                integrated.append(o.id)
                if o_scheme:
                    more = wit.auto_propagate_cluster(
                        db, cb_id, o_scheme, o, witness_date
                    )
                    auto_ids.extend(more)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        logger.exception("complete_witnessing failed")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return WitnessCompleteResponse(
        updated_ids=updated,
        auto_propagated_ids=sorted(set(auto_ids)),
        integrated_ids=integrated,
    )


@router.get("/witnessing/settings", response_model=WitnessSettingsResponse)
def get_witnessing_settings(
    scheme: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    cb_id = int(current_user.cb_id)
    schemes = _cb_schemes(db, cb_id)
    active = None
    if scheme:
        active = next((s for s in schemes if s.code == scheme), None) or _resolve_scheme(
            db, scheme
        )
    else:
        active = schemes[0] if schemes else _resolve_scheme(db, None)

    wit.ensure_cb_codes(db, cb_id, active)
    db.commit()

    cluster_names = wit.cluster_name_map(db, active.id)
    rows = (
        db.query(WitnessingCode)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.scheme_id == active.id,
        )
        .order_by(WitnessingCode.iaf_code)
        .all()
    )
    items = [
        WitnessSettingsItem(
            id=r.id,
            iaf_code=r.iaf_code,
            description=r.description,
            cluster_id=r.cluster_id,
            cluster_name=cluster_names.get(r.cluster_id) if r.cluster_id else None,
            is_critical=bool(r.is_critical),
            eligible_for_coverage=bool(r.eligible_for_coverage),
            cycle_years=int(r.cycle_years or 5),
            last_witness_date=r.last_witness_date,
            next_due_date=r.next_due_date,
            status=wit.compute_status(r.last_witness_date, r.next_due_date),
        )
        for r in rows
    ]
    return WitnessSettingsResponse(
        scheme=_scheme_tab(active),
        has_cluster_logic=bool(active.has_cluster_logic),
        items=items,
    )


@router.put("/witnessing/settings", response_model=WitnessSettingsResponse)
def put_witnessing_settings(
    payload: WitnessSettingsPutRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    cb_id = int(current_user.cb_id)
    scheme = _resolve_scheme(db, payload.scheme)
    wit.ensure_cb_codes(db, cb_id, scheme)

    id_set = {i.id for i in payload.items}
    rows = (
        db.query(WitnessingCode)
        .filter(
            WitnessingCode.cb_id == cb_id,
            WitnessingCode.scheme_id == scheme.id,
            WitnessingCode.id.in_(id_set) if id_set else False,
        )
        .all()
    )
    by_id = {r.id: r for r in rows}

    try:
        for item in payload.items:
            row = by_id.get(item.id)
            if not row:
                continue
            if item.is_critical is not None:
                row.is_critical = bool(item.is_critical)
            if item.eligible_for_coverage is not None:
                row.eligible_for_coverage = bool(item.eligible_for_coverage)
            # Rule: critical ⇒ eligible_for_coverage forced off
            if row.is_critical:
                row.eligible_for_coverage = False
            if item.cycle_years is not None:
                cy = int(item.cycle_years)
                if cy < 1 or cy > 10:
                    raise HTTPException(status_code=400, detail="cycle_years must be 1–10")
                row.cycle_years = cy
            if item.last_witness_date is not None:
                row.last_witness_date = item.last_witness_date
                row.next_due_date = wit.next_due_from(
                    item.last_witness_date, row.cycle_years or 5
                )
                row.is_auto = False
            row.updated_at = datetime.utcnow()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return get_witnessing_settings(scheme=scheme.code, db=db, current_user=current_user)
