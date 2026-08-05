"""레거시 cb_accreditation_scopes(콤마 IAF) → cb_accredited_scopes(1행=1IAF) 이관."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cb import CbAccreditationScopes, CertificationBodies
from app.models.master_data import CbAccreditedScope, IafCode, IsoStandard


def _get_or_create_standard(db: Session, standard_code: str, standard_name: Optional[str] = None) -> IsoStandard:
    code = (standard_code or "").strip()
    row = db.query(IsoStandard).filter(IsoStandard.standard_code == code).first()
    if row:
        return row
    # 부분 매칭 (ISO 9001 vs ISO 9001:2015)
    row = (
        db.query(IsoStandard)
        .filter(IsoStandard.standard_code.ilike(f"%{code.split(':')[0].strip()}%"))
        .first()
    )
    if row:
        return row
    now = datetime.utcnow()
    row = IsoStandard(
        standard_code=code,
        standard_name_ko=(standard_name or code).strip(),
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def _get_or_create_iaf(db: Session, iaf_code: str) -> IafCode:
    code = (iaf_code or "").strip().lstrip("0") or (iaf_code or "").strip()
    # 원본/패딩 모두 시도
    candidates = [(iaf_code or "").strip(), code, code.zfill(2)]
    for cand in candidates:
        if not cand:
            continue
        row = db.query(IafCode).filter(IafCode.code == cand).first()
        if row:
            return row
    now = datetime.utcnow()
    row = IafCode(
        code=(iaf_code or "").strip() or code,
        name_ko=f"IAF {(iaf_code or '').strip()}",
        name_en=None,
        is_active=True,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    return row


def migrate_legacy_scopes_to_normalized(db: Session, *, cb_id: Optional[int] = None) -> dict:
    """레거시 iaf_codes 콤마 셀을 개별 cb_accredited_scopes 행으로 분리 저장."""
    query = db.query(CbAccreditationScopes).filter(CbAccreditationScopes.is_active.is_(True))
    if cb_id is not None:
        query = query.filter(CbAccreditationScopes.cb_id == cb_id)

    created = 0
    skipped = 0
    errors = []

    for legacy in query.all():
        if not db.query(CertificationBodies.id).filter(CertificationBodies.id == legacy.cb_id).first():
            errors.append({"legacy_id": legacy.id, "error": f"cb_id={legacy.cb_id} 없음"})
            continue

        standard = _get_or_create_standard(db, legacy.standard_code, legacy.standard_name)
        tokens = [
            t.strip()
            for t in (legacy.iaf_codes or "").replace(";", ",").split(",")
            if t.strip()
        ]
        if not tokens:
            skipped += 1
            continue

        for token in tokens:
            try:
                iaf = _get_or_create_iaf(db, token)
            except Exception as e:  # noqa: BLE001
                errors.append({"legacy_id": legacy.id, "iaf": token, "error": str(e)})
                continue

            exists = (
                db.query(CbAccreditedScope.id)
                .filter(
                    CbAccreditedScope.cb_id == legacy.cb_id,
                    CbAccreditedScope.standard_id == standard.id,
                    CbAccreditedScope.iaf_code_id == iaf.id,
                )
                .first()
            )
            if exists:
                skipped += 1
                continue

            now = datetime.utcnow()
            db.add(
                CbAccreditedScope(
                    cb_id=legacy.cb_id,
                    standard_id=standard.id,
                    iaf_code_id=iaf.id,
                    accreditation_body="KAB",
                    approval_date=None,
                    expiry_date=None,
                    status="active" if legacy.is_active else "suspended",
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1

    db.commit()
    return {"created": created, "skipped": skipped, "error_count": len(errors), "errors": errors[:30]}
