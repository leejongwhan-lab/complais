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

assert len(OPERATING_STANDARDS) == 14, f"운영 규격은 14개여야 함: {len(OPERATING_STANDARDS)}"
