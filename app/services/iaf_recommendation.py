"""전공/기업(KSIC) 기반 IAF 코드 추천·매핑 서비스."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Set

from sqlalchemy import inspect
from sqlalchemy.orm import Session, joinedload

from app.models.company import Companies
from app.models.master import MasterIafCodes, MasterKsicIaf
from app.models.master_data import IafCode, KsicCode, KsicIafMapping, Major, MajorIafMapping


@dataclass(frozen=True)
class IafHint:
    iaf_code_id: int
    iaf_code: str
    industry_name_ko: str
    name_en: Optional[str]
    source: str  # major | company_ksic | company_iaf
    extra_exp_years: int = 0
    requires_committee: bool = False
    notes: Optional[str] = None


def _digits(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _has_table(db: Session, table: str) -> bool:
    try:
        return inspect(db.get_bind()).has_table(table)
    except Exception:
        return False


def _hint_from_master(row: MasterIafCodes, source: str) -> IafHint:
    return IafHint(
        iaf_code_id=row.id,
        iaf_code=row.iaf_code,
        industry_name_ko=row.name_kr or row.scope_name_ko or row.iaf_code,
        name_en=row.name_en,
        source=source,
    )


def resolve_iaf_from_ksic(db: Session, ksic_code: Optional[str]) -> List[IafHint]:
    """KSIC → IAF (5→4→3자리 fallback). 동일 레벨의 1:N 매핑을 모두 반환."""
    clean = _digits(ksic_code)
    if len(clean) < 2:
        return []

    if _has_table(db, "ksic_codes") and _has_table(db, "iaf_codes"):
        for length in range(min(5, len(clean)), 2, -1):
            sub = clean[:length]
            ksic = (
                db.query(KsicCode)
                .options(joinedload(KsicCode.iaf_mappings).joinedload(KsicIafMapping.iaf))
                .filter(KsicCode.code == sub)
                .first()
            )
            if not ksic or not ksic.iaf_mappings:
                continue
            hints: List[IafHint] = []
            seen: Set[int] = set()
            for mapping in ksic.iaf_mappings:
                iaf = mapping.iaf
                if not iaf or iaf.id in seen:
                    continue
                if getattr(iaf, "is_active", True) is False:
                    continue
                seen.add(iaf.id)
                hints.append(
                    IafHint(
                        iaf_code_id=iaf.id,
                        iaf_code=iaf.code,
                        industry_name_ko=iaf.name_ko,
                        name_en=iaf.name_en,
                        source="company_ksic",
                    )
                )
            if hints:
                return hints

    # Legacy master_ksic_iaf → master_iaf_codes
    if _has_table(db, "master_ksic_iaf") and _has_table(db, "master_iaf_codes"):
        for length in range(min(5, len(clean)), 2, -1):
            sub = clean[:length]
            links = (
                db.query(MasterKsicIaf)
                .filter(MasterKsicIaf.ksic_code.like(f"{sub}%"))
                .limit(20)
                .all()
            )
            if not links:
                continue
            hints = []
            seen: Set[str] = set()
            for link in links:
                code = (link.iaf_code or "").strip()
                if not code or code in seen:
                    continue
                seen.add(code)
                row = (
                    db.query(MasterIafCodes)
                    .filter(MasterIafCodes.iaf_code == code, MasterIafCodes.is_active.is_(True))
                    .first()
                )
                if row:
                    hints.append(_hint_from_master(row, "company_ksic"))
            if hints:
                return hints
    return []


def resolve_iaf_from_company_field(db: Session, iaf_field: Optional[str]) -> List[IafHint]:
    """companies.iaf_code 문자열(콤마 구분 가능)을 마스터와 매칭."""
    if not iaf_field:
        return []
    raw_parts = [p.strip() for p in str(iaf_field).replace(";", ",").split(",") if p.strip()]
    if not raw_parts:
        return []

    use_new = _has_table(db, "iaf_codes")
    hints: List[IafHint] = []
    seen: Set[int] = set()
    for part in raw_parts:
        candidates = [part, part.lstrip("0") or part]
        digits_only = _digits(part)
        if digits_only:
            candidates.append(digits_only)
            candidates.append(digits_only.lstrip("0") or digits_only)
            candidates.append(digits_only.zfill(2))

        if use_new:
            iaf = None
            for cand in candidates:
                iaf = db.query(IafCode).filter(IafCode.code == cand).first()
                if iaf:
                    break
                if digits_only:
                    iaf = (
                        db.query(IafCode)
                        .filter(IafCode.code.like(f"{digits_only}%"))
                        .order_by(IafCode.code.asc())
                        .first()
                    )
                    if iaf:
                        break
            if not iaf or iaf.id in seen:
                continue
            if getattr(iaf, "is_active", True) is False:
                continue
            seen.add(iaf.id)
            hints.append(
                IafHint(
                    iaf_code_id=iaf.id,
                    iaf_code=iaf.code,
                    industry_name_ko=iaf.name_ko,
                    name_en=iaf.name_en,
                    source="company_iaf",
                )
            )
        else:
            row = None
            for cand in candidates:
                row = (
                    db.query(MasterIafCodes)
                    .filter(MasterIafCodes.iaf_code == cand, MasterIafCodes.is_active.is_(True))
                    .first()
                )
                if row:
                    break
            if not row or row.id in seen:
                continue
            seen.add(row.id)
            hints.append(_hint_from_master(row, "company_iaf"))
    return hints


def resolve_iaf_for_company(db: Session, company: Companies) -> List[IafHint]:
    """기업 KSIC 매핑 우선, 없으면 companies.iaf_code 폴백."""
    from_ksic = resolve_iaf_from_ksic(db, company.ksic_code)
    if from_ksic:
        return from_ksic
    return resolve_iaf_from_company_field(db, company.iaf_code)


def resolve_iaf_from_major(db: Session, major_name: Optional[str]) -> List[IafHint]:
    if not major_name or not major_name.strip():
        return []
    clean = major_name.strip()
    if not (_has_table(db, "majors") and _has_table(db, "iaf_codes")):
        return []
    majors = (
        db.query(Major)
        .options(joinedload(Major.iaf_mappings).joinedload(MajorIafMapping.iaf))
        .filter(Major.name.like(f"%{clean}%"))
        .all()
    )
    hints: List[IafHint] = []
    seen: Set[int] = set()
    for major in majors:
        for mapping in major.iaf_mappings:
            iaf = mapping.iaf
            if not iaf or iaf.id in seen:
                continue
            if getattr(iaf, "is_active", True) is False:
                continue
            seen.add(iaf.id)
            hints.append(
                IafHint(
                    iaf_code_id=iaf.id,
                    iaf_code=iaf.code,
                    industry_name_ko=iaf.name_ko,
                    name_en=iaf.name_en,
                    source="major",
                    extra_exp_years=mapping.extra_exp_years or 0,
                    requires_committee=bool(mapping.requires_committee),
                    notes=mapping.notes,
                )
            )
    return hints


def merge_hints(groups: Sequence[Iterable[IafHint]]) -> List[IafHint]:
    """중복 제거. major 출처를 우선 보존하고 source를 합치지 않음."""
    by_id: dict[int, IafHint] = {}
    source_rank = {"major": 0, "company_ksic": 1, "company_iaf": 2}
    for group in groups:
        for hint in group:
            prev = by_id.get(hint.iaf_code_id)
            if prev is None or source_rank.get(hint.source, 9) < source_rank.get(prev.source, 9):
                by_id[hint.iaf_code_id] = hint
    return sorted(by_id.values(), key=lambda h: (h.source != "major", h.iaf_code))


def recommend_iaf(
    db: Session,
    *,
    major: Optional[str] = None,
    company_id: Optional[int] = None,
) -> List[IafHint]:
    major_hints = resolve_iaf_from_major(db, major)
    company_hints: List[IafHint] = []
    if company_id is not None:
        company = db.get(Companies, company_id)
        if company:
            company_hints = resolve_iaf_for_company(db, company)
    return merge_hints([major_hints, company_hints])
