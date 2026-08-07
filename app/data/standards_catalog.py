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
from typing import Dict, List, Literal, Optional

# Role-specific display modes (display only — internal codes unchanged)
StandardDisplayMode = Literal[
    "enterprise",
    "cb",
    "auditor",
    "admin_company",
    "admin_cb",
]


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


# Bare numeric / short codes used by cert questionnaires & legacy storage
_CODE_FALLBACKS: Dict[str, Dict[str, str]] = {
    "9001": {"initial": "QMS", "iso_code": "ISO 9001:2015", "name_kr": "품질경영시스템"},
    "14001": {"initial": "EMS", "iso_code": "ISO 14001:2015", "name_kr": "환경경영시스템"},
    "45001": {"initial": "OHSMS", "iso_code": "ISO 45001:2018", "name_kr": "안전보건경영시스템"},
    "27001": {"initial": "ISMS", "iso_code": "ISO/IEC 27001:2022", "name_kr": "정보보안경영시스템"},
    "27701": {"initial": "PIMS", "iso_code": "ISO/IEC 27701:2019", "name_kr": "개인정보보호경영시스템"},
    "22000": {"initial": "FSMS", "iso_code": "ISO 22000:2018", "name_kr": "식품안전경영시스템"},
    "50001": {"initial": "EnMS", "iso_code": "ISO 50001:2018", "name_kr": "에너지경영시스템"},
    "13485": {"initial": "MDQMS", "iso_code": "ISO 13485:2016", "name_kr": "의료기기품질경영시스템"},
    "19443": {"initial": "NSMS", "iso_code": "ISO 19443:2018", "name_kr": "원자력공급망품질경영시스템"},
    "37001": {"initial": "ABMS", "iso_code": "ISO 37001:2016", "name_kr": "부패방지경영시스템"},
    "37301": {"initial": "CMS", "iso_code": "ISO 37301:2021", "name_kr": "준법경영시스템"},
    "42001": {"initial": "AIMS", "iso_code": "ISO/IEC 42001:2023", "name_kr": "인공지능경영시스템"},
    "22301": {"initial": "BCMS", "iso_code": "ISO 22301:2019", "name_kr": "사업연속성경영시스템"},
}


def _prefer_edition(defs: List[StandardDefinition]) -> Optional[StandardDefinition]:
    """Prefer READY edition; for QMS/EMS prefer 2015 over PENDING 2026."""
    if not defs:
        return None
    ready = [d for d in defs if d.clauses_status == "READY"]
    pool = ready or defs
    pool = sorted(pool, key=lambda d: d.edition_year or 0)
    return pool[0]


def _parts_from_def(s: StandardDefinition) -> Dict[str, str]:
    return {
        "initial": s.family_code,
        "iso_code": s.display_code,
        "name_kr": s.name_ko.replace(" ", ""),
    }


def standard_display_parts(raw: Optional[str]) -> Dict[str, str]:
    """UI 표기 부품 — {initial, iso_code, name_kr}.

    역할별 조합은 ``format_standard_label(..., mode=)`` 를 사용한다.
    DB/API 내부 코드(9001 등)는 그대로 두고 화면에서만 변환한다.
    ``standard_key`` / ``display_code`` 가 주어지면 해당 판본을 그대로 쓴다.
    """
    import re

    text = str(raw or "").strip()
    if not text:
        return {"initial": "", "iso_code": "", "name_kr": ""}

    # exact standard_key (QMS_2015 / QMS_2026 …)
    by_key = STANDARD_BY_KEY.get(text) or STANDARD_BY_KEY.get(text.upper())
    if by_key and by_key.role == "CERTIFIABLE":
        return _parts_from_def(by_key)

    # exact display_code (ISO 9001:2026)
    by_display = next((s for s in OPERATING_STANDARDS if s.display_code == text), None)
    if by_display:
        return _parts_from_def(by_display)

    # bare numeric code
    digits = re.sub(r"[^0-9]", "", text)
    if digits in _CODE_FALLBACKS and (
        text == digits or re.fullmatch(r"(?i)iso(?:/iec)?\s*" + digits, text.replace(" ", ""))
        or text.lower() in {digits, f"iso{digits}", f"iso/iec{digits}"}
    ):
        return dict(_CODE_FALLBACKS[digits])

    fam = to_family_initial(text)
    if fam:
        defs = [s for s in OPERATING_STANDARDS if s.family_code == fam]
        chosen = _prefer_edition(defs)
        if chosen:
            return _parts_from_def(chosen)
        fb = next((v for v in _CODE_FALLBACKS.values() if v["initial"] == fam), None)
        if fb:
            return dict(fb)

    m = re.search(
        r"(9001|14001|45001|27001|37001|37301|50001|22000|13485|19443|27701|42001|22301)",
        text,
        re.I,
    )
    if m and m.group(1) in _CODE_FALLBACKS:
        return dict(_CODE_FALLBACKS[m.group(1)])

    # last resort — do not invent junk English; surface cleaned tokens
    return {
        "initial": fam or text.upper()[:12],
        "iso_code": text if text.upper().startswith("ISO") else "",
        "name_kr": "",
    }


def format_standard_label(
    raw: Optional[str],
    mode: StandardDisplayMode = "enterprise",
) -> str:
    """Role-specific standard label (never all three parts at once).

    Modes
    -----
    enterprise / admin_company : ``ISO 9001:2015 품질경영시스템``
    cb / admin_cb              : ``QMS``
    auditor                    : ``ISO 9001:2015``
    """
    p = standard_display_parts(raw)
    initial = (p.get("initial") or "").strip()
    iso = (p.get("iso_code") or "").strip()
    name = (p.get("name_kr") or "").strip()

    if mode in ("cb", "admin_cb"):
        return initial or iso or name or str(raw or "")
    if mode == "auditor":
        return iso or initial or str(raw or "")
    # enterprise | admin_company — ISO code + Korean name
    if iso and name:
        return f"{iso} {name}"
    return iso or name or initial or str(raw or "")


def standard_display_payload(
    raw: Optional[str],
    *,
    code: Optional[str] = None,
    mode: StandardDisplayMode = "enterprise",
) -> Dict[str, str]:
    """API/UI payload: internal code + part fields + role-specific label.

    Prefer ``standard_key`` (QMS_2015) as ``code`` when the input is a catalog key
    or when ``code=`` is explicitly passed. Bare numeric codes (9001) remain for
    legacy storage.
    """
    import re

    text = str(raw or "").strip()
    explicit = str(code).strip() if code is not None else ""
    resolve_from = explicit or text

    by_key = STANDARD_BY_KEY.get(resolve_from) or STANDARD_BY_KEY.get(resolve_from.upper())
    if by_key and by_key.role == "CERTIFIABLE":
        code_out = by_key.standard_key
        parts = _parts_from_def(by_key)
        label = format_standard_label(by_key.standard_key, mode=mode)
        return {
            "code": code_out,
            "standard_key": by_key.standard_key,
            "initial": parts["initial"],
            "iso_code": parts["iso_code"],
            "name_kr": parts["name_kr"],
            "label": label,
            "name": label,
            "mode": mode,
        }

    if explicit:
        code_out = explicit
    else:
        m = re.search(
            r"(9001|14001|45001|27001|37001|37301|50001|22000|13485|19443|27701|42001|22301)",
            resolve_from,
            re.I,
        )
        code_out = m.group(1) if m else resolve_from

    parts = standard_display_parts(resolve_from or text)
    label = format_standard_label(resolve_from or text, mode=mode)
    return {
        "code": code_out,
        "standard_key": "",
        "initial": parts["initial"],
        "iso_code": parts["iso_code"],
        "name_kr": parts["name_kr"],
        "label": label,
        "name": label,  # legacy alias for forms
        "mode": mode,
    }


assert len(OPERATING_STANDARDS) == 14, f"운영 규격은 14개여야 함: {len(OPERATING_STANDARDS)}"

OPERATING_FAMILY_INITIALS = ALLOWED_FAMILY_INITIALS
