"""Resolve per-standard 인정기관(AB) / 인증기관(CB) for a company.

Sources (priority):
1. company_certificates (explicit)
2. certificates + contracts (legacy issued certs)
3. certification_applications (in-flight / approved) + cb_standard_accreditations for AB

Portal roles:
- CB portal: pass cb_id → only standards this CB audits/certifies for the company
- Enterprise / Platform Admin: omit cb_id → full held standards (all CBs)
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.data.standards_catalog import (
    StandardDisplayMode,
    format_standard_label,
    standard_display_payload,
    to_family_initial,
)
from app.models.cb import CertificationBodies
from app.models.certification import Certificates, CertificationApplications
from app.models.certification_body import CbStandardAccreditation
from app.models.contract import Contracts

logger = logging.getLogger(__name__)

_STD_RE = re.compile(
    r"(9001|14001|45001|27001|37001|37301|50001|22000|13485|19443|27701|42001|22301|"
    r"QMS|EMS|OHSMS|OHS|ISMS|ABMS|CMS|EnMS|FSMS|MDQMS|MDMS|BCMS)",
    re.I,
)


def _table_exists(db: Session, name: str) -> bool:
    try:
        return inspect(db.get_bind()).has_table(name)
    except Exception:
        return False


def _split_standards(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        out: List[str] = []
        for item in raw:
            if isinstance(item, dict):
                code = item.get("code") or item.get("standard") or item.get("initial")
                if code:
                    out.append(str(code))
            elif item:
                out.append(str(item))
        return out
    text_val = str(raw).strip()
    if not text_val:
        return []
    if text_val.startswith("[") or text_val.startswith("{"):
        try:
            parsed = json.loads(text_val)
            return _split_standards(parsed)
        except Exception:
            pass
    parts = re.split(r"[,;|/]+", text_val)
    return [p.strip() for p in parts if p and p.strip()]


def _norm_key(raw: str) -> str:
    payload = standard_display_payload(raw)
    code = (payload.get("code") or "").strip()
    initial = (payload.get("initial") or to_family_initial(raw) or "").strip()
    return code or initial or raw.strip().upper()


def _row_key(standard: str, cb_id: Optional[int]) -> str:
    """Dedupe by standard + CB so multi-CB holdings stay distinct."""
    return f"{_norm_key(standard)}#{int(cb_id) if cb_id else 0}"


def _iso_date(val: Any) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            return None
    text = str(val).strip()
    return text[:10] if text else None


def _merge_row(
    by_key: Dict[str, Dict[str, Any]],
    *,
    standard: str,
    ab_code: Optional[str] = None,
    cb_id: Optional[int] = None,
    cb_name: Optional[str] = None,
    cb_initial: Optional[str] = None,
    cert_no: Optional[str] = None,
    status: Optional[str] = None,
    issued_at: Any = None,
    valid_from: Any = None,
    valid_until: Any = None,
    source_id: Optional[int] = None,
    last_audit_date: Any = None,
    last_audit_type: Optional[str] = None,
    current_audit_type: Optional[str] = None,
    certificate_file_url: Optional[str] = None,
) -> None:
    key = _row_key(standard, cb_id)
    if not _norm_key(standard):
        return
    disp = standard_display_payload(standard)
    row = by_key.get(key) or {
        "standard_code": disp.get("code") or _norm_key(standard),
        "initial": disp.get("initial") or "",
        "iso_code": disp.get("iso_code") or "",
        "name_kr": disp.get("name_kr") or "",
        "label": disp.get("label") or _norm_key(standard),
        "ab_code": None,
        "cb_id": None,
        "cb_name": None,
        "cb_initial": None,
        "cert_no": None,
        "status": None,
        "issued_at": None,
        "valid_from": None,
        "valid_until": None,
        "source_id": None,
        "last_audit_date": None,
        "last_audit_type": None,
        "current_audit_type": None,
        "certificate_file_url": None,
    }
    if ab_code and not row.get("ab_code"):
        row["ab_code"] = ab_code.strip()
    if cb_id and not row.get("cb_id"):
        row["cb_id"] = int(cb_id)
    if cb_name and not row.get("cb_name"):
        row["cb_name"] = cb_name
    if cb_initial and not row.get("cb_initial"):
        row["cb_initial"] = cb_initial
    if cert_no and not row.get("cert_no"):
        row["cert_no"] = cert_no
    if status and not row.get("status"):
        row["status"] = status
    issued_s = _iso_date(issued_at)
    from_s = _iso_date(valid_from)
    until_s = _iso_date(valid_until)
    last_s = _iso_date(last_audit_date)
    if issued_s and not row.get("issued_at"):
        row["issued_at"] = issued_s
    if from_s and not row.get("valid_from"):
        row["valid_from"] = from_s
    if until_s and not row.get("valid_until"):
        row["valid_until"] = until_s
    if last_s and not row.get("last_audit_date"):
        row["last_audit_date"] = last_s
    if last_audit_type and not row.get("last_audit_type"):
        row["last_audit_type"] = str(last_audit_type).strip()
    if current_audit_type and not row.get("current_audit_type"):
        row["current_audit_type"] = str(current_audit_type).strip()
    if certificate_file_url and not row.get("certificate_file_url"):
        row["certificate_file_url"] = str(certificate_file_url).strip()
    if source_id is not None and row.get("source_id") is None:
        row["source_id"] = int(source_id)
    by_key[key] = row


def _cb_map(db: Session, cb_ids: Set[int]) -> Dict[int, Tuple[str, Optional[str]]]:
    if not cb_ids:
        return {}
    rows = (
        db.query(CertificationBodies.id, CertificationBodies.name, CertificationBodies.cb_initial)
        .filter(CertificationBodies.id.in_(list(cb_ids)))
        .all()
    )
    return {int(r[0]): (r[1] or "", r[2]) for r in rows}


def _ab_for_cb_std(db: Session, pairs: Set[Tuple[int, str]]) -> Dict[Tuple[int, str], str]:
    """Lookup ab_code from cb_standard_accreditations for (cb_id, standard token)."""
    out: Dict[Tuple[int, str], str] = {}
    if not pairs or not _table_exists(db, "cb_standard_accreditations"):
        return out
    cb_ids = {p[0] for p in pairs}
    try:
        rows = (
            db.query(
                CbStandardAccreditation.cb_id,
                CbStandardAccreditation.standard_code,
                CbStandardAccreditation.ab_code,
            )
            .filter(
                CbStandardAccreditation.cb_id.in_(list(cb_ids)),
                CbStandardAccreditation.is_active.is_(True),
            )
            .all()
        )
    except Exception:
        logger.exception("ab lookup failed")
        try:
            db.rollback()
        except Exception:
            pass
        return out
    for cid, std_code, ab in rows:
        if not ab:
            continue
        key = _norm_key(str(std_code))
        out[(int(cid), key)] = str(ab).strip()
        fam = to_family_initial(str(std_code))
        if fam:
            out[(int(cid), fam)] = str(ab).strip()
    return out


def list_company_held_standards(
    db: Session,
    company_id: int,
    cb_id: Optional[int] = None,
    display_mode: StandardDisplayMode = "enterprise",
) -> List[Dict[str, Any]]:
    """Return list of held standards with AB/CB for display.

    When ``cb_id`` is set, only include standards linked to that CB via
    company_certificates / contracts / certification_applications.
    Soft-fails to ``[]`` on per-source errors (never raises for empty data).
    ``display_mode`` controls the ``label`` field only (role-specific).
    """
    by_key: Dict[str, Dict[str, Any]] = {}
    pending_ab: Set[Tuple[int, str]] = set()
    filter_cb = int(cb_id) if cb_id is not None else None

    # 1) company_certificates
    if _table_exists(db, "company_certificates"):
        try:
            # Prefer extended audit/PDF columns when present (additive migration).
            cols = {c["name"] for c in inspect(db.get_bind()).get_columns("company_certificates")}
            has_audit = "last_audit_date" in cols
            has_pdf = "certificate_file_url" in cols
            select_cols = (
                "id, standard_code, ab_code, cb_id, cert_no, status, "
                "valid_from, valid_until"
            )
            if has_audit:
                select_cols += ", last_audit_date, last_audit_type, current_audit_type"
            if has_pdf:
                select_cols += ", certificate_file_url"
            sql = f"SELECT {select_cols} FROM company_certificates WHERE company_id = :cid"
            params: Dict[str, Any] = {"cid": company_id}
            if filter_cb is not None:
                sql += " AND cb_id = :cb_id"
                params["cb_id"] = filter_cb
            rows = db.execute(text(sql), params).fetchall()
            cb_ids = {int(r[3]) for r in rows if r[3]}
            cbs = _cb_map(db, cb_ids)
            for row in rows:
                row_id, std, ab, row_cb_id, cert_no, status, vf, vu = row[:8]
                idx = 8
                lad = lat = cat = pdf = None
                if has_audit:
                    lad, lat, cat = row[idx : idx + 3]
                    idx += 3
                if has_pdf:
                    pdf = row[idx]
                name, ini = (None, None)
                if row_cb_id and int(row_cb_id) in cbs:
                    name, ini = cbs[int(row_cb_id)]
                _merge_row(
                    by_key,
                    standard=str(std),
                    ab_code=ab,
                    cb_id=int(row_cb_id) if row_cb_id else None,
                    cb_name=name,
                    cb_initial=ini,
                    cert_no=cert_no,
                    status=status,
                    issued_at=vf,
                    valid_from=vf,
                    valid_until=vu,
                    source_id=int(row_id) if row_id is not None else None,
                    last_audit_date=lad,
                    last_audit_type=lat,
                    current_audit_type=cat,
                    certificate_file_url=pdf,
                )
                if row_cb_id and not ab:
                    pending_ab.add((int(row_cb_id), _norm_key(str(std))))
        except Exception:
            logger.exception("company_certificates read soft-fail company_id=%s", company_id)
            try:
                db.rollback()
            except Exception:
                pass

    # 2) certificates + contracts
    try:
        cert_rows = (
            db.query(Certificates, Contracts)
            .outerjoin(Contracts, Contracts.id == Certificates.contract_id)
            .filter(Certificates.company_id == company_id)
            .all()
        )
        cb_ids: Set[int] = set()
        resolved: List[Tuple[Any, Any, Optional[int]]] = []
        for cert, contract in cert_rows:
            cid: Optional[int] = None
            if contract and contract.cb_id:
                cid = int(contract.cb_id)
            elif getattr(cert, "issued_by", None):
                try:
                    cid = int(cert.issued_by)
                except (TypeError, ValueError):
                    cid = None
            if filter_cb is not None and cid != filter_cb:
                continue
            if cid:
                cb_ids.add(cid)
            resolved.append((cert, contract, cid))
        cbs = _cb_map(db, cb_ids)
        for cert, _contract, cid in resolved:
            name, ini = (None, None)
            if cid and cid in cbs:
                name, ini = cbs[cid]
            pdf = getattr(cert, "certificate_file_url", None)
            for std in _split_standards(cert.standards):
                _merge_row(
                    by_key,
                    standard=std,
                    cb_id=cid,
                    cb_name=name,
                    cb_initial=ini,
                    cert_no=cert.cert_no,
                    status=cert.status,
                    issued_at=cert.issued_at,
                    valid_from=cert.valid_from,
                    valid_until=cert.valid_until,
                    source_id=int(cert.id) if getattr(cert, "id", None) is not None else None,
                    certificate_file_url=pdf,
                )
                if cid:
                    pending_ab.add((cid, _norm_key(std)))
    except Exception:
        logger.exception("certificates read soft-fail company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass

    # 3) certification_applications
    try:
        q = db.query(CertificationApplications).filter(
            CertificationApplications.company_id == company_id
        )
        if filter_cb is not None:
            q = q.filter(CertificationApplications.cb_id == filter_cb)
        apps = q.all()
        cb_ids = {int(a.cb_id) for a in apps if a.cb_id}
        cbs = _cb_map(db, cb_ids)
        for app in apps:
            cid = int(app.cb_id) if app.cb_id else None
            if filter_cb is not None and cid != filter_cb:
                continue
            name, ini = (None, None)
            if cid and cid in cbs:
                name, ini = cbs[cid]
            for std in _split_standards(app.standards_json):
                _merge_row(
                    by_key,
                    standard=std,
                    cb_id=cid,
                    cb_name=name,
                    cb_initial=ini,
                    status=app.status,
                )
                if cid:
                    pending_ab.add((cid, _norm_key(std)))
    except Exception:
        logger.exception("cert apps held-std soft-fail company_id=%s", company_id)
        try:
            db.rollback()
        except Exception:
            pass

    # Fill AB from CB scope accreditations when missing
    ab_map = _ab_for_cb_std(db, pending_ab)
    for row in by_key.values():
        if row.get("ab_code") or not row.get("cb_id"):
            continue
        cid = int(row["cb_id"])
        key = _norm_key(row.get("standard_code") or row.get("label") or "")
        fam = row.get("initial") or to_family_initial(key)
        ab = ab_map.get((cid, key)) or (ab_map.get((cid, fam)) if fam else None)
        if ab:
            row["ab_code"] = ab

    order = [
        "QMS",
        "EMS",
        "OHSMS",
        "ISMS",
        "ABMS",
        "CMS",
        "EnMS",
        "FSMS",
        "MDQMS",
        "MDMS",
        "BCMS",
        "NSMS",
        "PIMS",
        "AIMS",
    ]
    rank = {k: i for i, k in enumerate(order)}

    def _sort_key(item: Dict[str, Any]) -> Tuple[int, str, int]:
        ini = item.get("initial") or ""
        return (rank.get(ini, 99), item.get("label") or "", int(item.get("cb_id") or 0))

    rows = sorted(by_key.values(), key=_sort_key)
    for item in rows:
        src = item.get("initial") or item.get("standard_code") or item.get("iso_code")
        item["label"] = format_standard_label(src, mode=display_mode)
    return rows


def company_held_standards(
    db: Session,
    company_id: int,
    cb_id: Optional[int] = None,
    display_mode: StandardDisplayMode = "enterprise",
) -> List[Dict[str, Any]]:
    """Alias for ``list_company_held_standards`` (backward compatible)."""
    return list_company_held_standards(
        db, company_id, cb_id=cb_id, display_mode=display_mode
    )


def _parse_iso_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def expiry_alert_fields(valid_until: Optional[str]) -> Dict[str, Any]:
    """Alert when expiry is within 3 months (≈92 days), including already expired."""
    until = _parse_iso_date(valid_until)
    if not until:
        return {
            "expiry_within_3_months": False,
            "days_to_expiry": None,
            "expiry_notice": None,
        }
    days = (until - date.today()).days
    within = days <= 92
    notice = None
    if within:
        if days < 0:
            notice = (
                f"인증 유효기간이 {abs(days)}일 전에 만료되었습니다. "
                "갱신·전환 심사를 검토하세요."
            )
        elif days == 0:
            notice = "인증 유효기간이 오늘 만료됩니다. 갱신·전환 심사를 검토하세요."
        else:
            notice = (
                f"인증 만료까지 {days}일 남았습니다(3개월 이내). "
                "갱신·전환 심사를 검토하세요."
            )
    return {
        "expiry_within_3_months": within,
        "days_to_expiry": days,
        "expiry_notice": notice,
    }


def list_company_held_cert_status(
    db: Session,
    company_id: int,
    cb_id: Optional[int] = None,
    display_mode: StandardDisplayMode = "enterprise",
) -> List[Dict[str, Any]]:
    """Held standards + expiry alert fields for Admin/CB/Enterprise cert status.

    Same sources as ``list_company_held_standards``; CB portal passes ``cb_id``.
    Soft-fails to ``[]``.
    """
    try:
        rows = list_company_held_standards(
            db, company_id, cb_id=cb_id, display_mode=display_mode
        )
    except Exception:
        logger.exception(
            "held cert status soft-fail company_id=%s cb_id=%s", company_id, cb_id
        )
        try:
            db.rollback()
        except Exception:
            pass
        return []

    out: List[Dict[str, Any]] = []
    for idx, r in enumerate(rows):
        label = (
            r.get("label")
            or format_standard_label(
                r.get("initial") or r.get("standard_code") or "",
                mode=display_mode,
            )
            or str(r.get("standard_code") or "-")
        )
        item = {
            "id": int(r.get("source_id") or (idx + 1)),
            "cert_no": r.get("cert_no"),
            "standards": label,
            "standard_label": label,
            "standard_code": r.get("standard_code"),
            "initial": r.get("initial"),
            "cb_id": r.get("cb_id"),
            "cb_name": r.get("cb_name"),
            "ab_code": r.get("ab_code"),
            "valid_from": r.get("valid_from"),
            "valid_until": r.get("valid_until"),
            "status": r.get("status") or "held",
            "issued_at": r.get("issued_at") or r.get("valid_from"),
            "last_audit_date": r.get("last_audit_date"),
            "last_audit_type": r.get("last_audit_type"),
            "current_audit_type": r.get("current_audit_type"),
            "certificate_file_url": r.get("certificate_file_url"),
        }
        item.update(expiry_alert_fields(r.get("valid_until")))
        out.append(item)
    return out


def company_held_standard_labels(
    db: Session,
    company_id: int,
    cb_id: Optional[int] = None,
    display_mode: StandardDisplayMode = "enterprise",
) -> List[str]:
    """Compact role-specific label list for held standards."""
    try:
        rows = list_company_held_standards(
            db, company_id, cb_id=cb_id, display_mode=display_mode
        )
    except Exception:
        logger.exception("held labels soft-fail company_id=%s", company_id)
        return []
    out: List[str] = []
    seen: Set[str] = set()
    for r in rows:
        label = (r.get("label") or r.get("initial") or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        out.append(label)
    return out


def company_held_standards_map(
    db: Session,
    company_ids: List[int],
    cb_id: Optional[int] = None,
    display_mode: StandardDisplayMode = "enterprise",
) -> Dict[int, List[Dict[str, Any]]]:
    return {
        cid: list_company_held_standards(
            db, cid, cb_id=cb_id, display_mode=display_mode
        )
        for cid in company_ids
    }
