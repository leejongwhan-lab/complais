"""모니터링 등 API 응답용 이름 마스킹 (백엔드).

Examples
--------
>>> mask_company_name("주식회사 마린텍")
'주식회사 마***'
>>> mask_company_name("삼성전자")
'삼***'
>>> mask_auditor_name("홍길동")
'홍*동'
>>> mask_auditor_name("김철")
'김*철'
>>> mask_auditor_name("박")
'박*'
"""
from __future__ import annotations

import re
from typing import Optional

_LEGAL_PREFIXES = (
    "주식회사",
    "유한회사",
    "유한책임회사",
    "합자회사",
    "합명회사",
    "(주)",
    "(유)",
    "㈜",
    "㈔",
)


def mask_company_name(name: Optional[str]) -> str:
    """기업명: 법인형태 접두 + 의미 있는 첫 글자 + *** .

    - '주식회사 마린텍' → '주식회사 마***'
    - '삼성전자' → '삼***'
    - 빈 값 → ''
    """
    raw = (name or "").strip()
    if not raw:
        return ""

    prefix = ""
    rest = raw
    for p in _LEGAL_PREFIXES:
        if rest.startswith(p):
            prefix = p
            rest = rest[len(p) :].lstrip(" \t·.-")
            break

    if not rest:
        # 접두만 있는 경우
        return f"{prefix}***" if prefix else "***"

    # 한글/영문/숫자 첫 의미 글자
    m = re.search(r"[A-Za-z0-9가-힣]", rest)
    if not m:
        return f"{prefix} ***".strip() if prefix else "***"
    first = m.group(0)
    if prefix:
        return f"{prefix} {first}***"
    return f"{first}***"


def mask_auditor_name(name: Optional[str]) -> str:
    """심사원명: 첫글자 + * + 마지막글자 (2글자 이상).

    - '홍길동' → '홍*동'
    - '김철' → '김*철'
    - '박' → '박*'
    """
    raw = (name or "").strip()
    if not raw:
        return ""
    # 공백 제거한 표시용 코어 (성은 보통 붙여씀)
    core = re.sub(r"\s+", "", raw)
    if len(core) == 1:
        return f"{core}*"
    if len(core) == 2:
        return f"{core[0]}*{core[1]}"
    # 3글자 이상: 첫 + * + 끝 (중간 길이 노출 최소화)
    return f"{core[0]}*{core[-1]}"
