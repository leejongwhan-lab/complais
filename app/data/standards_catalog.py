"""ComplAIs 인증 표준 카탈로그 (프론트 lib/standards.ts 와 동일 출처).

용어
----
family_code   : KAB 이니셜 계열 (QMS, EMS …) — 판본 무관
edition_year  : 판본 연도 (2015, 2026 …)
standard_key  : DB/API 고유키 `{FAMILY}_{YEAR}` (예: QMS_2015) — 매핑·저장 기준
iso_number    : 연도 없는 ISO 번호 (ISO 9001)
display_code  : 화면 표기 (ISO 9001:2015)
name_ko       : 국문 표준명
clauses_status: READY | PENDING
role          : CERTIFIABLE (운영 14) | META (COMMON/IMS)

운영 14규격 = QMS:2015/2026 + EMS:2015/2026 + OHSMS~AIMS 10개.
QMS/EMS 2026 은 조항 미확정(PENDING) — 확정 후 clause 시드.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StandardDefinition:
    standard_key: str
    family_code: str
    edition_year: Optional[int]
    iso_number: str
    display_code: str
    name_ko: str
    clauses_status: str  # READY | PENDING
    role: str  # CERTIFIABLE | META
    clauses_note: Optional[str] = None


def _def(
    family: str,
    year: Optional[int],
    iso_number: str,
    name_ko: str,
    *,
    clauses_status: str = "READY",
    role: str = "CERTIFIABLE",
    clauses_note: Optional[str] = None,
) -> StandardDefinition:
    if year is None or family in {"COMMON", "IMS"}:
        display = iso_number
        key = family
    else:
        display = f"{iso_number}:{year}"
        key = f"{family}_{year}"
    return StandardDefinition(
        standard_key=key,
        family_code=family,
        edition_year=year,
        iso_number=iso_number,
        display_code=display,
        name_ko=name_ko,
        clauses_status=clauses_status,
        role=role,
        clauses_note=clauses_note,
    )


STANDARD_CATALOG: List[StandardDefinition] = [
    _def("COMMON", None, "COMMON", "공통 적용요인", role="META"),
    _def("IMS", None, "IMS", "통합경영시스템", role="META"),
    _def("QMS", 2015, "ISO 9001", "품질경영시스템"),
    _def(
        "QMS",
        2026,
        "ISO 9001",
        "품질경영시스템",
        clauses_status="PENDING",
        clauses_note="2026년 판 조항번호·조항제목 확정 후 시드",
    ),
    _def("EMS", 2015, "ISO 14001", "환경경영시스템"),
    _def(
        "EMS",
        2026,
        "ISO 14001",
        "환경경영시스템",
        clauses_status="PENDING",
        clauses_note="2026년 판 조항번호·조항제목 확정 후 시드",
    ),
    _def("OHSMS", 2018, "ISO 45001", "안전보건경영시스템"),
    _def("ISMS", 2022, "ISO/IEC 27001", "정보보안경영시스템"),
    _def("ABMS", 2016, "ISO 37001", "부패방지경영시스템"),
    _def("CMS", 2021, "ISO 37301", "준법경영시스템"),
    _def("EnMS", 2018, "ISO 50001", "에너지경영시스템"),
    _def("FSMS", 2018, "ISO 22000", "식품안전경영시스템"),
    _def("MDQMS", 2016, "ISO 13485", "의료기기 품질경영시스템"),
    _def("NSMS", 2018, "ISO 19443", "원자력 공급망 품질경영시스템"),
    _def("PIMS", 2019, "ISO/IEC 27701", "개인정보보호 경영시스템"),
    _def("AIMS", 2023, "ISO/IEC 42001", "인공지능 경영시스템"),
]

OPERATING_STANDARDS: List[StandardDefinition] = [
    s for s in STANDARD_CATALOG if s.role == "CERTIFIABLE"
]

STANDARD_BY_KEY: Dict[str, StandardDefinition] = {s.standard_key: s for s in STANDARD_CATALOG}

# KAB 이니셜 — 목록 "보유 표준" 표시용 (판본 무관, 중복 제거 순서)
FAMILY_DISPLAY_ORDER: List[str] = [
    "QMS",
    "EMS",
    "OHSMS",
    "ISMS",
    "ABMS",
    "CMS",
    "EnMS",
    "FSMS",
    "MDQMS",
    "NSMS",
    "PIMS",
    "AIMS",
]
ALLOWED_FAMILY_INITIALS = frozenset(FAMILY_DISPLAY_ORDER)

# 별칭 → 공식 이니셜 (레거시/오타/약칭)
_FAMILY_ALIASES: Dict[str, str] = {
    "OHS": "OHSMS",
    "OH&S": "OHSMS",
    "OH&SMS": "OHSMS",
    "ISO45001": "OHSMS",
    "ISO9001": "QMS",
    "ISO14001": "EMS",
    "ISO27001": "ISMS",
    "ISO37001": "ABMS",
    "ISO37301": "CMS",
    "ISO50001": "EnMS",
    "ISO22000": "FSMS",
    "ISO13485": "MDQMS",
    "ISO19443": "NSMS",
    "ISO27701": "PIMS",
    "ISO42001": "AIMS",
    "NQMS": "NSMS",
    "ENMS": "EnMS",
}


def to_family_initial(raw: Optional[str]) -> Optional[str]:
    """표준 코드/표시명 → 지정 이니셜. 매핑 불가( junk )는 None."""
    import re

    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # family_code / standard_key (QMS, QMS_2015)
    upper = text.upper().replace(" ", "")
    if text in ALLOWED_FAMILY_INITIALS:
        return text
    # EnMS is mixed-case
    for fam in ALLOWED_FAMILY_INITIALS:
        if text == fam or upper == fam.upper():
            return fam
    if "_" in text:
        head = text.split("_", 1)[0]
        for fam in ALLOWED_FAMILY_INITIALS:
            if head == fam or head.upper() == fam.upper():
                return fam
    alias = _FAMILY_ALIASES.get(upper) or _FAMILY_ALIASES.get(text)
    if alias:
        return alias
    # ISO 9001:2015 / ISO/IEC 27001 → family via catalog
    for s in OPERATING_STANDARDS:
        if text == s.display_code or text == s.iso_number or text == s.standard_key:
            return s.family_code
        if upper == s.display_code.upper().replace(" ", "") or upper == s.iso_number.upper().replace(" ", ""):
            return s.family_code
    m = re.search(
        r"(?:ISO(?:/IEC)?\s*)?(9001|14001|45001|27001|37001|37301|50001|22000|13485|19443|27701|42001)\b",
        text,
        re.I,
    )
    if m:
        num = m.group(1)
        return _FAMILY_ALIASES.get(f"ISO{num}") or {
            "9001": "QMS",
            "14001": "EMS",
            "45001": "OHSMS",
            "27001": "ISMS",
            "37001": "ABMS",
            "37301": "CMS",
            "50001": "EnMS",
            "22000": "FSMS",
            "13485": "MDQMS",
            "19443": "NSMS",
            "27701": "PIMS",
            "42001": "AIMS",
        }.get(num)
    return None


def held_standards_as_initials(codes: List[str]) -> List[str]:
    """보유 표준 목록을 지정 이니셜만으로 정규화·정렬. junk 제거."""
    seen = set()
    out: List[str] = []
    for raw in codes or []:
        fam = to_family_initial(raw)
        if not fam or fam in seen:
            continue
        seen.add(fam)
        out.append(fam)
    order = {f: i for i, f in enumerate(FAMILY_DISPLAY_ORDER)}
    out.sort(key=lambda x: order.get(x, 99))
    return out


assert len(OPERATING_STANDARDS) == 14, f"운영 규격은 14개여야 함: {len(OPERATING_STANDARDS)}"

OPERATING_FAMILY_INITIALS = ALLOWED_FAMILY_INITIALS
