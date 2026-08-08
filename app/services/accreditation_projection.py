"""Project approved accreditation-request scopes into operational SoT + IAF matrix.

SoT: ``cb_standard_accreditations``
IAF: ``cb_scope_matrix`` (subordinate via optional ``standard_accreditation_id`` FK)
NO writes to legacy ``cb_accredited_scopes``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.data.scope_taxonomies import normalize_scope_code, taxonomy_for_standard
from app.models.admin import CBAccreditation, CBAccreditationStatus, CBAccreditedScope
from app.models.cb import CbAccreditationScopes
from app.models.certification_body import CbAccreditationScope, CbStandardAccreditation
from app.models.standard import StandardMaster


def _standard_code_for_scope(db: Session, scope: CBAccreditedScope) -> Optional[str]:
    std = db.get(StandardMaster, scope.iso_standard_id)
    if std is None:
        return None
    return (std.standard_code or "").strip() or None


def _ensure_standard_accreditation(
    db: Session,
    *,
    cb_id: int,
    standard_code: str,
    ab_code: Optional[str],
    registration_no: Optional[str],
) -> CbStandardAccreditation:
    now = datetime.utcnow()
    row = (
        db.query(CbStandardAccreditation)
        .filter(
            CbStandardAccreditation.cb_id == cb_id,
            CbStandardAccreditation.standard_code == standard_code,
        )
        .first()
    )
    if row is None:
        row = CbStandardAccreditation(
            cb_id=cb_id,
            standard_code=standard_code,
            ab_code=ab_code,
            registration_no=registration_no,
            expiry_date=None,
            md_rate=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.flush()
        return row

    if ab_code:
        row.ab_code = ab_code
    if registration_no:
        row.registration_no = registration_no
    row.is_active = True
    row.updated_at = now
    db.flush()
    return row


def _upsert_matrix_row(
    db: Session,
    *,
    cb_id: int,
    standard_code: str,
    iaf_code: str,
    standard_accreditation_id: Optional[int],
) -> CbAccreditationScope:
    now = datetime.utcnow()
    tax = taxonomy_for_standard(standard_code)
    code = normalize_scope_code(tax, iaf_code) if tax != "none" else (iaf_code or "").strip()
    if not code:
        code = (iaf_code or "").strip()
    row = (
        db.query(CbAccreditationScope)
        .filter(
            CbAccreditationScope.cb_id == cb_id,
            CbAccreditationScope.standard_code == standard_code,
            CbAccreditationScope.iaf_code == code,
        )
        .first()
    )
    if row is None:
        row = CbAccreditationScope(
            cb_id=cb_id,
            standard_code=standard_code,
            iaf_code=code,
            is_active=True,
            granted_date=now.date(),
            expiry_date=None,
            created_at=now,
            updated_at=now,
            standard_accreditation_id=standard_accreditation_id,
        )
        db.add(row)
    else:
        row.is_active = True
        if standard_accreditation_id is not None:
            row.standard_accreditation_id = standard_accreditation_id
        if row.granted_date is None:
            row.granted_date = now.date()
        row.updated_at = now
    db.flush()
    return row


def _sync_legacy_comma_iaf(db: Session, cb_id: int, standard_code: str, iaf_code: str) -> None:
    """Best-effort sync into legacy cb_accreditation_scopes (QMS/EMS/OHSMS comma IAF)."""
    tax = taxonomy_for_standard(standard_code)
    if tax != "iaf39":
        return
    code = normalize_scope_code(tax, iaf_code)
    if not code:
        return
    now = datetime.utcnow()
    row = (
        db.query(CbAccreditationScopes)
        .filter(
            CbAccreditationScopes.cb_id == cb_id,
            CbAccreditationScopes.standard_code == standard_code,
        )
        .first()
    )
    if row:
        existing = {x.strip() for x in (row.iaf_codes or "").split(",") if x.strip()}
        existing.add(code)
        row.iaf_codes = ",".join(sorted(existing, key=lambda x: (len(x), x)))
        row.is_active = True
        row.updated_at = now
    else:
        db.add(
            CbAccreditationScopes(
                cb_id=cb_id,
                standard_code=standard_code,
                standard_name=standard_code,
                iaf_codes=code,
                use_nace=0,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )


def project_scope_approval(
    db: Session,
    accreditation: CBAccreditation,
    scope: CBAccreditedScope,
) -> dict:
    """Approve one request scope and project into SoT + matrix. Returns summary dict."""
    standard_code = _standard_code_for_scope(db, scope)
    if not standard_code:
        raise ValueError(f"표준 마스터를 찾을 수 없습니다 (iso_standard_id={scope.iso_standard_id})")

    ab = (accreditation.accreditation_body or "").strip() or None
    reg = (accreditation.certificate_number or "").strip() or None
    sot = _ensure_standard_accreditation(
        db,
        cb_id=int(accreditation.cb_id),
        standard_code=standard_code,
        ab_code=ab,
        registration_no=reg,
    )
    matrix = _upsert_matrix_row(
        db,
        cb_id=int(accreditation.cb_id),
        standard_code=standard_code,
        iaf_code=scope.iaf_code,
        standard_accreditation_id=int(sot.id),
    )
    _sync_legacy_comma_iaf(db, int(accreditation.cb_id), standard_code, scope.iaf_code)

    scope.is_approved = True
    if hasattr(scope, "status"):
        scope.status = "APPROVED"
    if hasattr(scope, "reject_reason"):
        scope.reject_reason = None

    return {
        "scope_id": scope.id,
        "standard_code": standard_code,
        "iaf_code": matrix.iaf_code,
        "standard_accreditation_id": sot.id,
        "matrix_id": matrix.id,
    }


def reject_scope(
    scope: CBAccreditedScope,
    *,
    reject_reason: Optional[str],
) -> None:
    scope.is_approved = False
    if hasattr(scope, "status"):
        scope.status = "REJECTED"
    if hasattr(scope, "reject_reason"):
        scope.reject_reason = (reject_reason or "").strip() or None


def refresh_accreditation_status(db: Session, accreditation: CBAccreditation) -> str:
    """Roll up parent record status from child scopes. Returns new status."""
    scopes = list(accreditation.scopes or [])
    if not scopes:
        return accreditation.status or CBAccreditationStatus.PENDING.value

    statuses = []
    for s in scopes:
        st = getattr(s, "status", None)
        if st:
            statuses.append(str(st).upper())
        elif s.is_approved:
            statuses.append("APPROVED")
        else:
            statuses.append("PENDING")

    if any(st == "PENDING" for st in statuses):
        accreditation.status = CBAccreditationStatus.PENDING.value
        return accreditation.status

    if all(st == "REJECTED" for st in statuses):
        accreditation.status = CBAccreditationStatus.REJECTED.value
        accreditation.approved_at = None
        return accreditation.status

    # All decided and at least one APPROVED
    accreditation.status = CBAccreditationStatus.APPROVED.value
    accreditation.reject_reason = None
    if accreditation.approved_at is None:
        accreditation.approved_at = datetime.utcnow()
    return accreditation.status


def project_all_pending_scopes(db: Session, accreditation: CBAccreditation) -> list[dict]:
    """Batch-approve convenience: project every non-rejected pending scope."""
    results = []
    for scope in list(accreditation.scopes or []):
        st = str(getattr(scope, "status", "") or "").upper()
        if st == "REJECTED":
            continue
        if st == "APPROVED" and scope.is_approved:
            continue
        results.append(project_scope_approval(db, accreditation, scope))
    refresh_accreditation_status(db, accreditation)
    return results
