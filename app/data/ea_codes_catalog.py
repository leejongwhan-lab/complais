"""EA(IAF) 산업분류 마스터 — FE constants/eaCodeMasterData 동기."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal


@dataclass(frozen=True)
class EACodeDef:
    code: str
    name_ko: str
    risk_category: Literal["HIGH", "MEDIUM", "LOW"]


EA_CODE_MASTERS: List[EACodeDef] = [
    EACodeDef("EA_04", "화학제품 및 화학섬유 제조업", "HIGH"),
    EACodeDef("EA_14", "고무 및 플라스틱 제품 제조업", "MEDIUM"),
    EACodeDef("EA_18", "기계 및 장비 제조업", "MEDIUM"),
    EACodeDef("EA_19", "전기 및 광학기기 제조업 (의료기기 포함)", "HIGH"),
    EACodeDef("EA_28", "건설업", "HIGH"),
    EACodeDef("EA_33", "정보기술 (IT, S/W 개발 및 정보보안)", "LOW"),
    EACodeDef("EA_35", "전문, 과학 및 기술 서비스업", "LOW"),
]

# 하위 호환
DEFAULT_EA_CODE_MASTERS = EA_CODE_MASTERS

EA_CODE_BY_CODE: Dict[str, EACodeDef] = {e.code: e for e in EA_CODE_MASTERS}


def ea_code_to_iaf_number(ea_code: str) -> str:
    """EA_14 → 14 (zero-pad 2)."""
    import re

    m = re.search(r"(?:EA[_-]?)?(\d{1,2})", (ea_code or "").upper())
    if not m:
        return ""
    return f"{int(m.group(1)):02d}"
