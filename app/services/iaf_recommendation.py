"""전공/기업(KSIC) 기반 IAF 코드 추천·매핑 서비스."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Set

from sqlalchemy.orm import Session, joinedload

from app.models.company import Companies
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


def resolve_iaf_from_ksic(db: Session, ksic_code: Optional[str]) -> List[IafHint]:
    """KSIC → IAF (5→4→3자리 fallback). 동일 레벨의 1:N 매핑을 모두 반환."""
    clean = _digits(ksic_code)
    if len(clean) < 2:
        return []

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
    return []


def resolve_iaf_from_company_field(db: Session, iaf_field: Optional[str]) -> List[IafHint]:
    """companies.iaf_code 문자열(콤마 구분 가능)을 마스터와 매칭."""
    if not iaf_field:
        return []
    raw_parts = [p.strip() for p in str(iaf_field).replace(";", ",").split(",") if p.strip()]
    if not raw_parts:
        return []

    hints: List[IafHint] = []
    seen: Set[int] = set()
    for part in raw_parts:
        candidates = [part, part.lstrip("0") or part]
        # "IAF 14" / "14" / "19B" 형태 모두 허용
        digits_only = _digits(part)
        if digits_only:
            candidates.append(digits_only)
            candidates.append(digits_only.lstrip("0") or digits_only)

        iaf = None
        for cand in candidates:
            iaf = db.query(IafCode).filter(IafCode.code == cand).first()
            if iaf:
                break
            # 접두 숫자 매칭 (19B → 19)
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
