"""UPSERT helpers for company_aspects (EMS/OHS/EnMS JSON)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.company_aspects import CompanyAspects

logger = logging.getLogger(__name__)


def _as_dict(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


def aspects_to_dict(row: Optional[CompanyAspects]) -> Dict[str, Any]:
    if row is None:
        return {"ems": None, "ohs": None, "enms": None}
    return {
        "ems": _as_dict(row.ems_json),
        "ohs": _as_dict(row.ohs_json),
        "enms": _as_dict(row.enms_json),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_company_aspects(db: Session, company_id: int) -> Optional[CompanyAspects]:
    try:
        return (
            db.query(CompanyAspects)
            .filter(CompanyAspects.company_id == company_id)
            .first()
        )
    except Exception:
        logger.exception("get_company_aspects soft-fail company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def upsert_company_aspects(
    db: Session,
    company_id: int,
    *,
    ems: Any = None,
    ohs: Any = None,
    enms: Any = None,
    merge: bool = True,
) -> Tuple[CompanyAspects, bool]:
    """UPSERT by company_id. When merge=True, only non-None fields overwrite."""
    now = datetime.now()
    row = (
        db.query(CompanyAspects)
        .filter(CompanyAspects.company_id == company_id)
        .first()
    )
    created = False
    if row is None:
        row = CompanyAspects(
            company_id=company_id,
            ems_json=None,
            ohs_json=None,
            enms_json=None,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        created = True

    ems_d = _as_dict(ems)
    ohs_d = _as_dict(ohs)
    enms_d = _as_dict(enms)

    if ems_d is not None or (not merge and ems is not None):
        row.ems_json = ems_d
    if ohs_d is not None or (not merge and ohs is not None):
        row.ohs_json = ohs_d
    if enms_d is not None or (not merge and enms is not None):
        row.enms_json = enms_d

    row.updated_at = now
    if created and row.created_at is None:
        row.created_at = now
    db.flush()
    return row, created
