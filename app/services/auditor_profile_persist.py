"""심사원 가입/소속신청 시 학력·경력·자격 행 저장 헬퍼."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.auditor import (
    AuditorEducation,
    AuditorExternalCert,
    AuditorQualification,
    AuditorWorkExperience,
)
from app.services.auditor_grade import to_db_grade


def parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def normalize_iaf_codes(codes: Optional[Sequence[Any]]) -> List[str]:
    out: List[str] = []
    seen = set()
    for c in codes or []:
        text = str(c).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def add_educations(
    db: Session,
    *,
    auditor_id: int,
    items: Iterable[Any],
    now: datetime,
) -> int:
    n = 0
    for edu in items or []:
        school = getattr(edu, "school_name", None) or (edu.get("school_name") if isinstance(edu, dict) else None)
        degree = getattr(edu, "degree", None) or (edu.get("degree") if isinstance(edu, dict) else None) or "bachelor"
        major = getattr(edu, "major", None) or (edu.get("major") if isinstance(edu, dict) else None)
        if not school:
            continue
        entered = getattr(edu, "entered_at", None) if not isinstance(edu, dict) else edu.get("entered_at")
        graduated = getattr(edu, "graduated_at", None) if not isinstance(edu, dict) else edu.get("graduated_at")
        db.add(
            AuditorEducation(
                auditor_id=auditor_id,
                school_name=str(school).strip(),
                degree=str(degree).strip() or "bachelor",
                major=(str(major).strip() if major else "-") or "-",
                entered_at=parse_date(entered) if not isinstance(entered, date) else entered,
                graduated_at=parse_date(graduated) if not isinstance(graduated, date) else graduated,
                is_verified=False,
                created_at=now,
            )
        )
        n += 1
    return n


def add_work_experiences(
    db: Session,
    *,
    auditor_id: int,
    items: Iterable[Any],
    now: datetime,
) -> int:
    n = 0
    for work in items or []:
        def _g(key: str, default=None):
            if isinstance(work, dict):
                return work.get(key, default)
            return getattr(work, key, default)

        company_name = (_g("company_name") or "").strip()
        if not company_name:
            continue
        start_raw = _g("start_date")
        start_date = start_raw if isinstance(start_raw, date) else parse_date(start_raw)
        if start_date is None:
            continue
        end_raw = _g("end_date")
        end_date = end_raw if isinstance(end_raw, date) else parse_date(end_raw)
        department = _g("department")
        duties = _g("duties")
        note = _g("note")
        note_parts = [p for p in (department, note) if p]
        db.add(
            AuditorWorkExperience(
                auditor_id=auditor_id,
                company_name=company_name,
                company_id=_g("company_id"),
                biz_no=(_g("biz_no") or None),
                position=_g("position"),
                department=department,
                ksic_code=_g("ksic_code"),
                iaf_code=_g("iaf_code"),
                start_date=start_date,
                end_date=end_date,
                is_current=bool(_g("is_current") or False),
                is_temporary=bool(_g("is_temporary") or False),
                duties=(str(duties).strip() if duties else None),
                note=" / ".join(note_parts) if note_parts else None,
                is_verified=False,
                created_at=now,
            )
        )
        n += 1
    return n


def add_qualifications(
    db: Session,
    *,
    auditor_id: int,
    items: Iterable[Any],
    now: datetime,
    cb_id: Optional[int] = None,
    membership_id: Optional[int] = None,
    default_major: Optional[str] = None,
    default_iaf_codes: Optional[Sequence[str]] = None,
) -> int:
    """auditor_qualifications + auditor_external_certs 동시 저장."""
    n = 0
    default_iaf = normalize_iaf_codes(default_iaf_codes)
    for item in items or []:
        def _g(key: str, default=None):
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        standard = (_g("standard_code") or _g("standard") or "").strip().upper()
        if not standard:
            continue
        grade = to_db_grade(_g("auditor_grade") or _g("grade") or "auditor")
        cert_body = (_g("cert_body_name") or _g("cert_body") or _g("issuer") or "").strip() or None
        cert_no = (_g("cert_no") or "").strip() or None
        major_name = (_g("major_name") or default_major or "").strip() or None
        iaf = normalize_iaf_codes(_g("iaf_codes") or default_iaf)
        item_cb = _g("cb_id")
        use_cb = int(item_cb) if item_cb is not None else cb_id

        db.add(
            AuditorQualification(
                auditor_id=auditor_id,
                cb_id=use_cb,
                standard_code=standard[:20],
                grade=grade,
                cert_body_name=cert_body,
                cert_no=cert_no,
                iaf_codes=iaf or None,
                major_name=major_name,
                membership_id=membership_id,
                is_active=False,  # CB 승인 전
                created_at=now,
                updated_at=now,
            )
        )
        # 외부 자격증 원본 보관 (cert body/no 있을 때)
        if cert_body and cert_no:
            db.add(
                AuditorExternalCert(
                    auditor_id=auditor_id,
                    cert_name=standard[:20],
                    issuer=cert_body[:50],
                    cert_no=cert_no[:100],
                    grade=grade,
                    note=f"major={major_name}" if major_name else None,
                    created_at=now,
                )
            )
        n += 1
    return n


def career_from_affiliation(
    *,
    company_id: Optional[int],
    company_name: Optional[str],
    biz_no: Optional[str],
    ksic_code: Optional[str],
    is_temporary: bool,
    start_date: Optional[str],
    end_date: Optional[str],
    duties: Optional[str],
    position: Optional[str],
    iaf_codes: Optional[Sequence[str]] = None,
) -> Optional[Dict[str, Any]]:
    name = (company_name or "").strip()
    if not name and not company_id:
        return None
    primary_iaf = None
    codes = normalize_iaf_codes(iaf_codes)
    if codes:
        primary_iaf = codes[0]
    return {
        "company_id": company_id,
        "company_name": name or f"company#{company_id}",
        "biz_no": biz_no,
        "ksic_code": ksic_code,
        "is_temporary": bool(is_temporary) or (company_id is None and bool(name)),
        "start_date": start_date or date.today().isoformat(),
        "end_date": end_date,
        "is_current": not bool(end_date),
        "duties": duties,
        "position": position,
        "iaf_code": primary_iaf,
        "note": duties,
    }
