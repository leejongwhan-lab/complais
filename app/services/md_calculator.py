"""KAB MD(Man-Day) 산출 엔진 — kab_audit_days.js 1:1 Python 포트.

데이터: app/data/md_calc_config.json (= 루트 md_calc_config.json)
규칙: kab_audit_days.js 의 lookupMD5Table / CALC_* / calcStd / calc() /
      onKsicChange / MD11 / multi-site 로직을 의도적 변경 없이 이식.

DOM 의존부(g/gv/gi)는 CalcInput 파라미터로 대체한다.
CB 검토 가감: cb_application_review.php 의 app_review_* 공식도 유지
(calculate_review_md / apply_cb_adjustment_ratio).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

_CONFIG_CANDIDATES = [
    Path(__file__).resolve().parents[1] / "data" / "md_calc_config.json",
    Path(__file__).resolve().parents[2] / "md_calc_config.json",
]


@lru_cache(maxsize=1)
def load_md_calc_config() -> Dict[str, Any]:
    """md_calc_config.php::load_md_calc_config() 대응."""
    for path in _CONFIG_CANDIDATES:
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        "md_calc_config.json 을 찾을 수 없습니다. "
        f"candidates={[str(p) for p in _CONFIG_CANDIDATES]}"
    )


def r1(v: float) -> float:
    """JS: Math.round(v*10)/10"""
    return round(v * 10) / 10


def snap05(v: float) -> float:
    """JS: Math.round(v*2)/2 — 0.5 M/D 단위 반올림."""
    return round(v * 2) / 2


def round_half(val: float) -> float:
    """cb_application_review.php md_round_half 별칭."""
    return snap05(val)


FLOOR_INITIAL = 1.0
FLOOR_SURV = 0.5

MD11_MATRIX = {
    100: {20: 0, 40: 5, 60: 10, 80: 15, 100: 20},
    80: {20: 0, 40: 5, 60: 10, 80: 15, 100: 15},
    60: {20: 0, 40: 5, 60: 10, 80: 10, 100: 10},
    40: {20: 0, 40: 5, 60: 5, 80: 5, 100: 5},
    20: {20: 0, 40: 0, 60: 0, 80: 0, 100: 0},
    0: {20: 0, 40: 0, 60: 0, 80: 0, 100: 0},
}

COMPLEXITY_LABEL_TO_KEY = {
    "높음": "high",
    "중간": "med",
    "낮음": "low",
    "제한": "restrict",
    "특별": "special",
    "HIGH": "high",
    "MEDIUM": "med",
    "LOW": "low",
    "LIMITED": "restrict",
    "high": "high",
    "med": "med",
    "medium": "med",
    "low": "low",
    "restrict": "restrict",
    "limited": "restrict",
}

COMPLEXITY_KEY_TO_ENUM = {
    "high": "HIGH",
    "med": "MEDIUM",
    "low": "LOW",
    "restrict": "LIMITED",
    "special": "LIMITED",
}

ATYPE_LABEL = {
    "initial": "최초",
    "surv6": "사후(6개월)",
    "surv12": "사후(12개월)",
    "recert": "갱신",
    "transfer_surv6": "전환·사후(6개월)",
    "transfer_surv12": "전환·사후(12개월)",
    "transfer_recert": "전환·갱신",
}


@dataclass
class CalcInput:
    """DOM 상태 대체 — kab_audit_days.js 의 입력 컨트롤 값."""

    standards: Sequence[str] = field(default_factory=lambda: ["9001"])
    employees: int = 50
    audit_type: str = "initial"  # initial|surv6|surv12|recert|transfer_*
    std_atype_overrides: Dict[str, str] = field(default_factory=dict)
    mode: str = "single"  # single|integrated
    complexity: str = "med"  # QMS cx (high|med|low|restrict)
    risk14: str = "med"  # EMS
    risk45: str = "med"  # OHSMS
    ksic_code: str = ""
    shift_type: str = "same"  # same|diff
    shift_cnt: int = 2
    site_total: int = 1
    site_factor: float = 0.5
    recert_mature: bool = False
    # integrated
    intg_level: float = 40.0
    intg_team_z: int = 1
    intg_team_sumx: int = 0
    # FSMS
    fsms_cat: str = "CI"
    haccp: int = 1
    fsms_outsource: int = 1
    # EN50
    en_tj: float = 50.0
    seu: int = 3
    en_complexity: int = 2
    # IS27
    it_users: int = 100
    it_systems: int = 2
    it_sensitivity: int = 2
    # MD13
    md_risk: int = 1
    md_proc: int = 2
    md_reg: int = 2
    md_cats: Sequence[str] = field(default_factory=lambda: ["AI"])
    # 27701
    pii_role: str = "controller"


@dataclass
class MdCalcResult:
    final_days: float
    base_days: float
    stage1_md: float
    stage2_md: float
    surveillance_md: float
    recertification_md: float
    complexity_key: str
    complexity_level: str  # HIGH|MEDIUM|LOW|LIMITED
    iaf_main: Optional[str]
    iaf_sub: Optional[str]
    ksic_code: str
    employees: int
    audit_type: str
    standards: List[str]
    detail_log: Dict[str, Any]
    per_standard: List[Dict[str, Any]]


def complexity_key_from_label(v: Optional[str]) -> str:
    if not v:
        return "med"
    return COMPLEXITY_LABEL_TO_KEY.get(str(v).strip(), "med")


def resolve_ksic(ksic_code: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """onKsicChange 매칭 — ksic_iaf_map exact match."""
    cfg = cfg or load_md_calc_config()
    v = (ksic_code or "").strip()
    if not v:
        return None
    for row in cfg.get("ksic_iaf_map") or []:
        if str(row.get("ksic", "")).strip() == v:
            return row
    # digit-only fallback (leading zeros)
    digits = "".join(ch for ch in v if ch.isdigit())
    if digits and digits != v:
        for row in cfg.get("ksic_iaf_map") or []:
            if str(row.get("ksic", "")).strip() == digits:
                return row
    return None


def apply_ksic_to_input(inp: CalcInput, cfg: Optional[Dict[str, Any]] = None) -> CalcInput:
    """KSIC → complexity/risk14/risk45 자동 주입 (onKsicChange)."""
    match = resolve_ksic(inp.ksic_code, cfg)
    if not match:
        return inp
    inp.complexity = complexity_key_from_label(match.get("qms"))
    inp.risk14 = complexity_key_from_label(match.get("ems"))
    inp.risk45 = complexity_key_from_label(match.get("ohsms"))
    return inp


def _kab_ratios(cfg: Dict[str, Any]) -> Dict[str, float]:
    return cfg["kab_ratios"]


def lookup_md5_table(std_code: str, emp: int, cx: str, cfg: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """kab_audit_days.js::lookupMD5Table 1:1."""
    m = cfg["md5_standard_map"].get(std_code)
    if not m:
        raise ValueError(f"md5_standard_map에 {std_code} 정의가 없습니다")
    table = cfg["md5_employee_table"][m["table"]]
    schema = cfg["md5_table_schema"][m["table"]]

    row = table[-1]
    for i in range(len(table) - 1):
        if emp >= table[i][0] and emp < table[i + 1][0]:
            row = table[i]
            break

    categories = schema["categories"]
    cat_idx = categories.index(cx) if cx in categories else (
        0 if schema["survMode"] == "single" else min(1, len(categories) - 1)
    )
    mult = float(m["multiplier"])
    st1 = row[schema["stageColBase"] + cat_idx * 2] * mult
    st2 = row[schema["stageColBase"] + cat_idx * 2 + 1] * mult
    total = r1(st1 + st2)

    surv = recert = None
    if schema["survMode"] == "single":
        surv = row[schema["survColBase"]]
        recert = row[schema["recertColBase"]]
    elif schema["survMode"] == "per_category":
        surv = row[schema["survColBase"] + cat_idx]
        recert = row[schema["recertColBase"] + cat_idx]

    return {
        "total": r1(total),
        "st1": r1(st1),
        "st2": r1(st2),
        "surv": r1(surv * mult) if surv is not None else None,
        "recert": r1(recert * mult) if recert is not None else None,
    }


def _lk(table: List[List[float]], e: int) -> float:
    for r in table:
        if e >= r[0] and e <= r[1]:
            return r[2]
    return table[-1][2]


def _effective_emp(inp: CalcInput) -> int:
    e = max(1, int(inp.employees or 1))
    if inp.shift_type == "diff":
        return e * max(1, int(inp.shift_cnt or 2))
    return e


def _get_atype(inp: CalcInput, code: str) -> str:
    return inp.std_atype_overrides.get(code) or inp.audit_type or "initial"


def _calc_md5(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any]) -> Dict[str, Any]:
    log: List[List[str]] = []
    at = _get_atype(inp, code)
    cx = inp.complexity or "med"
    r14, r45 = inp.risk14 or "med", inp.risk45 or "med"
    ratios = _kab_ratios(cfg)
    std_meta = next((s for s in cfg["standards"] if s["code"] == code), None)
    family = "14001" if code.startswith("14001") else "45001" if code.startswith("45001") else "9001"

    if family == "14001":
        looked = lookup_md5_table(code, emp_n, r14, cfg)
        cx_label = f"환경위험: {r14}"
    elif family == "45001":
        looked = lookup_md5_table(code, emp_n, r45, cfg)
        cx_label = f"안전위험: {r45}"
    else:
        looked = lookup_md5_table(code, emp_n, "single", cfg)
        cx_label = "인원수 단일트랙(위험도 구분 없음, KAB-AR-MD5 Table QMS1 원문 기준)"
        addon = cfg.get("qms_complexity_addon") or {}
        if addon.get("enabled"):
            pct = addon.get("high_pct") if cx == "high" else addon.get("low_pct") if cx == "low" else addon.get("med_pct")
            if pct:
                mult = 1 + pct / 100
                before = looked["total"]
                looked = {
                    "total": r1(looked["total"] * mult),
                    "st1": r1(looked["st1"] * mult),
                    "st2": r1(looked["st2"] * mult),
                    "surv": r1(looked["surv"] * mult) if looked["surv"] is not None else None,
                    "recert": r1(looked["recert"] * mult) if looked["recert"] is not None else None,
                }
                log.append([
                    "QMS 고복잡도 가산 (인증기관 정책, 조정 가능)",
                    f"KSIC 크로스워크 복잡도 '{cx}' → +{pct}%",
                    f"{before}→{looked['total']} M/D",
                ])

    if std_meta and std_meta.get("status") and std_meta["status"] != "active":
        log.append([f"⚠ {std_meta.get('full')}", std_meta.get("note") or "개정판 반영 전", "잠정치"])

    base_init = looked["total"]
    log.append([
        f"① 최초 기준일수 ({(std_meta or {}).get('full') or code} KAB 기준표)",
        f"{cx_label} | 인원: {emp_n}명 | 합계: {base_init} M/D (1단계 {looked['st1']} + 2단계 {looked['st2']})",
        f"{base_init} M/D",
    ])

    base = base_init
    if at == "surv6":
        if looked["surv"] and looked["surv"] > 0:
            surv_val = r1(looked["surv"] * ratios["surv6"] / ratios["surv12"])
        else:
            surv_val = r1(base_init * ratios["surv6"])
        base = surv_val
        log.append(["② 심사유형 — 사후관리(6개월)", f"최초×{ratios['surv6']:.4f} (KAB 기준: 4/15)", f"{base} M/D"])
    elif at == "surv12":
        surv_val = looked["surv"] if looked["surv"] and looked["surv"] > 0 else r1(base_init * ratios["surv12"])
        base = surv_val
        log.append(["② 심사유형 — 사후관리(12개월)", f"최초×{ratios['surv12']:.4f} (KAB 기준: 6/15)", f"{base} M/D"])
    elif at == "recert":
        recert_val = looked["recert"] if looked["recert"] and looked["recert"] > 0 else r1(base_init * ratios["recert"])
        base = recert_val
        log.append(["② 심사유형 — 갱신인증", f"최초×{ratios['recert']:.4f} (KAB 기준: 8/15)", f"{base} M/D"])
    elif at == "transfer_surv6":
        if looked["surv"] and looked["surv"] > 0:
            surv_val = r1(looked["surv"] * ratios["surv6"] / ratios["surv12"])
        else:
            surv_val = r1(base_init * ratios["surv6"])
        base = r1(surv_val + ratios["transfer_review_add"])
        log.append(["② 심사유형 — 전환심사(사후 6개월 시점)", f"사후(6개월) {surv_val} + 이력검토 {ratios['transfer_review_add']}", f"{base} M/D"])
    elif at == "transfer_surv12":
        surv_val = looked["surv"] if looked["surv"] and looked["surv"] > 0 else r1(base_init * ratios["surv12"])
        base = r1(surv_val + ratios["transfer_review_add"])
        log.append(["② 심사유형 — 전환심사(사후 12개월 시점)", f"사후(12개월) {surv_val} + 이력검토", f"{base} M/D"])
    elif at == "transfer_recert":
        recert_val = looked["recert"] if looked["recert"] and looked["recert"] > 0 else r1(base_init * ratios["recert"])
        base = r1(recert_val + ratios["transfer_review_add"])
        log.append(["② 심사유형 — 전환심사(갱신 시점)", f"갱신 {recert_val} + 이력검토", f"{base} M/D"])
    else:
        log.append(["② 심사유형 — 최초인증 (1단계+2단계)", f"1단계 {looked['st1']} + 2단계 {looked['st2']}", f"{base} M/D"])

    return {"base": base, "log": log, "looked": looked, "skipAuditType": True}


def _calc_fsms(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any]) -> Dict[str, Any]:
    log: List[List[str]] = []
    cats = cfg["fsms_categories"]["22000"]
    cat = next((x for x in cats if x["k"] == inp.fsms_cat), cats[1])
    haccp = max(0, int(inp.haccp))
    outsource = int(inp.fsms_outsource)
    td = cat["td"]
    log.append(["TD — 식품사슬 범주 기본일수", f"범주: {cat['k']}", f"{td} M/D"])
    th = r1(haccp * cat["th"])
    log.append(["TH — HACCP 연구 가산", f"{haccp}건 × {cat['th']}", f"+{th} M/D"])
    tfte = 0 if emp_n <= 5 else 0.5 if emp_n <= 49 else 1.0 if emp_n <= 99 else 1.5 if emp_n <= 199 else 2.0 if emp_n <= 499 else 2.5 if emp_n <= 999 else 3.0
    log.append(["TFTE — 상근상당 종업원", f"{emp_n}명", f"+{tfte} M/D"])
    outsource_adj = 0
    if outsource > 0:
        outsource_adj = 0.25 if outsource == 1 else 0.5
        log.append(["외주처리 비율 보정(보조)", str(outsource), f"+{outsource_adj} M/D"])
    base = r1(td + th + tfte + outsource_adj)
    log.append(["소계 (DS = TD + TH + TFTE, + 보조조정)", "KAB-SR-FSMS 부속서B", f"{base} M/D"])
    return {"base": base, "log": log}


def _calc_en50(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any]) -> Dict[str, Any]:
    log: List[List[str]] = []
    tj = max(0.0, float(inp.en_tj))
    seu = max(0, int(inp.seu))
    ec = int(inp.en_complexity)
    td = 1.5 if tj < 10 else 2 if tj < 50 else 2.5 if tj < 100 else 3 if tj < 500 else 3.5 if tj < 1000 else 4 if tj < 5000 else 5 if tj < 10000 else 6
    log.append(["TD — 연간 에너지 소비량 기준", f"{tj} TJ", f"{td} M/D"])
    seu_factor = round((1 + min(seu * 0.05, 0.5)) * 100) / 100
    log.append(["SEU 계수", "1 + min(SEU수×0.05, 0.5)", f"×{seu_factor}"])
    ec_factor = 1.0 if ec == 1 else 1.1 if ec == 2 else 1.2
    log.append(["에너지복잡도 계수", str(ec), f"×{ec_factor}"])
    base = r1(td * seu_factor * ec_factor)
    log.append(["소계", "TD × SEU계수 × 복잡도계수", f"{base} M/D"])
    return {"base": base, "log": log}


def _calc_is27(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any]) -> Dict[str, Any]:
    log: List[List[str]] = []
    it_users = max(1, int(inp.it_users))
    it_sys = int(inp.it_systems)
    it_sens = int(inp.it_sensitivity)
    base0 = _lk(cfg["is27_table"], it_users)
    log.append(["기본일수 (27001 IT사용자 기준표)", f"IT 사용자: {it_users}명", f"{base0} M/D"])
    sys_factor = {1: 0.9, 2: 1.0, 3: 1.15}.get(it_sys, 1.3)
    log.append(["정보시스템 수 계수", str(it_sys), f"×{sys_factor}"])
    sens_factor = {1: 0.9, 2: 1.0}.get(it_sens, 1.2)
    log.append(["데이터 민감도 계수", str(it_sens), f"×{sens_factor}"])
    base = r1(base0 * sys_factor * sens_factor)
    log.append(["소계", "기본 × 시스템 × 민감도", f"{base} M/D"])
    return {"base": base, "log": log}


def _calc_md13(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any], visiting: Set[str]) -> Dict[str, Any]:
    log: List[List[str]] = []
    md_risk = int(inp.md_risk)
    md_proc = int(inp.md_proc)
    md_reg = int(inp.md_reg)
    cat_count = max(1, len(inp.md_cats or ["AI"]))
    cx = inp.complexity or "med"
    base0 = r1(lookup_md5_table("9001", emp_n, cx, cfg)["total"] * 1.15)
    log.append(["기본일수 (9001 KAB 기준표 × 1.15 의료기기 가중)", f"인원: {emp_n}명", f"{base0} M/D"])
    risk_factor = min(1.5, 1 + md_risk * 0.2)
    risk_factor = round(risk_factor * 10) / 10
    log.append(["제품 등급 계수", "1 + (등급 × 0.2), 최대 1.5", f"×{risk_factor}"])
    proc_factor = {1: 0.9, 2: 1.0, 3: 1.15}.get(md_proc, 1.3)
    log.append(["제조 공정 복잡도", str(md_proc), f"×{proc_factor}"])
    reg_factor = {1: 1.0, 2: 1.1}.get(md_reg, 1.25)
    log.append(["규제 적용 지역", str(md_reg), f"×{reg_factor}"])
    cat_adj = r1(1 + min(cat_count - 1, 5) * 0.04)
    if cat_count > 1:
        log.append(["의료기기 분류 수 보정", f"{cat_count}개 분류", f"×{cat_adj}"])
    base = r1(base0 * risk_factor * proc_factor * reg_factor * cat_adj)
    log.append(["소계", "기본 × 등급 × 공정 × 규제 × 분류수", f"{base} M/D"])
    return {"base": base, "log": log}


def _apply_audit_type(base: float, log: List[List[str]], code: str, inp: CalcInput, cfg: Dict[str, Any]) -> Tuple[float, List[List[str]]]:
    at = _get_atype(inp, code)
    ratios = _kab_ratios(cfg)
    result = base
    if at == "surv6":
        result = r1(base * ratios["surv6"])
        log.append(["심사유형 — 사후관리(6개월)", "최초×4/15 (KAB 기준)", f"{result} M/D"])
    elif at == "surv12":
        result = r1(base * ratios["surv12"])
        log.append(["심사유형 — 사후관리(12개월)", "최초×6/15 (KAB 기준)", f"{result} M/D"])
    elif at == "recert":
        result = r1(base * ratios["recert"])
        log.append(["심사유형 — 갱신인증", "최초×8/15 (KAB 기준)", f"{result} M/D"])
    elif at == "transfer_surv6":
        surv_part = r1(base * ratios["surv6"])
        result = r1(surv_part + ratios["transfer_review_add"])
        log.append(["심사유형 — 전환심사(사후 6개월 시점)", f"사후(6개월) {surv_part} + 이력검토", f"{result} M/D"])
    elif at == "transfer_surv12":
        surv_part = r1(base * ratios["surv12"])
        result = r1(surv_part + ratios["transfer_review_add"])
        log.append(["심사유형 — 전환심사(사후 12개월 시점)", f"사후(12개월) {surv_part} + 이력검토", f"{result} M/D"])
    elif at == "transfer_recert":
        recert_part = r1(base * ratios["recert"])
        result = r1(recert_part + ratios["transfer_review_add"])
        log.append(["심사유형 — 전환심사(갱신 시점)", f"갱신 {recert_part} + 이력검토", f"{result} M/D"])
    else:
        log.append(["심사유형 — 최초인증", "—", f"{result} M/D"])
    return result, log


def _calc_gen(code: str, emp_n: int, inp: CalcInput, cfg: Dict[str, Any], visiting: Set[str]) -> Dict[str, Any]:
    log: List[List[str]] = []
    std = next((s for s in cfg["standards"] if s["code"] == code), None)
    if code == "27701" and std and std.get("base_standard"):
        role_table = {
            "controller": {"pct": 0.30, "min": 3},
            "processor": {"pct": 0.20, "min": 2.5},
            "both": {"pct": 0.50, "min": 3.5},
        }
        r = role_table.get(inp.pii_role or "controller", role_table["controller"])
        base27001 = calc_std(std["base_standard"], emp_n, inp, cfg, visiting)
        log.extend([[f"[27001 기준] {x[0]}", x[1], x[2]] for x in base27001["log"]])
        base = r1(base27001["base"] * (1 + r["pct"]))
        log.append([f"PII 역할 가산 ({inp.pii_role})", f"27001 기준 × (1+{r['pct']})", f"{base} M/D"])
        if _get_atype(inp, code) == "initial" and base < r["min"]:
            log.append(["최소일수 하한 (KAB-SR-PIMS)", f"최소 {r['min']}일", f"→ {r['min']} M/D"])
            base = r["min"]
        log.append(["참고 — ISMS와 별도심사 시", "PIMS +0.5일 별도 고려 필요", "수동 확인"])
        return {"base": base, "log": log}

    f = (std or {}).get("gf") or 1.0
    cx = inp.complexity or "med"
    looked = lookup_md5_table("9001", emp_n, cx, cfg)
    base0 = looked["total"]
    log.append(["기본일수 (ISO 9001 KAB 기준표, 잠정 기준)", f"인원: {emp_n}명", f"{base0} M/D"])
    base = r1(base0 * f)
    if f != 1:
        log.append(["표준 계수(잠정)", f"×{f}", f"{base} M/D"])
    return {"base": base, "log": log}


def calc_std(
    code: str,
    emp_n: int,
    inp: CalcInput,
    cfg: Optional[Dict[str, Any]] = None,
    visiting: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """kab_audit_days.js::calcStd 1:1."""
    cfg = cfg or load_md_calc_config()
    visiting = visiting if visiting is not None else set()
    if code in visiting:
        return {
            "base": 0,
            "log": [["⚠ 순환 참조 오류", f"{code} 순환", "0 M/D"]],
            "std": None,
            "looked": None,
        }
    visiting.add(code)
    try:
        std = next((s for s in cfg["standards"] if s["code"] == code), None)
        if not std:
            return {"base": 0, "log": [], "std": None, "looked": None}
        t = std.get("type")
        looked = None
        if t == "MD5":
            res = _calc_md5(code, emp_n, inp, cfg)
            looked = res.get("looked")
        elif t == "FSMS":
            res = _calc_fsms(code, emp_n, inp, cfg)
        elif t == "EN50":
            res = _calc_en50(code, emp_n, inp, cfg)
        elif t == "IS27":
            res = _calc_is27(code, emp_n, inp, cfg)
        elif t == "MD13":
            res = _calc_md13(code, emp_n, inp, cfg, visiting)
        elif t == "GEN":
            res = _calc_gen(code, emp_n, inp, cfg, visiting)
        else:
            res = {"base": 0, "log": []}
        if not res.get("skipAuditType"):
            result, log = _apply_audit_type(res["base"], res["log"], code, inp, cfg)
            res["base"] = result
            res["log"] = log
        return {"base": res["base"], "log": res["log"], "std": std, "looked": looked}
    finally:
        visiting.discard(code)


def multi_site_sample_count(sites: int, atype: str, mature: bool) -> Dict[str, Any]:
    if sites <= 1:
        return {"sample": 0, "raw": 0, "label": ""}
    if atype in ("surv6", "surv12", "transfer_surv6", "transfer_surv12"):
        raw = 0.6 * math.sqrt(sites)
        label = "0.6√x (사후)"
    elif atype in ("recert", "transfer_recert") and mature:
        raw = 0.8 * math.sqrt(sites)
        label = "0.8√x (갱신·성숙)"
    else:
        raw = math.sqrt(sites)
        label = "√x (갱신)" if atype in ("recert", "transfer_recert") else "√x (최초)"
    return {"sample": math.ceil(raw), "raw": raw, "label": label}


def snap_bucket20(v: float) -> int:
    buckets = [0, 20, 40, 60, 80, 100]
    best, bd = 0, float("inf")
    for b in buckets:
        d = abs(v - b)
        if d < bd:
            bd, best = d, b
    return best


def calc_team_capability_pct(z: int, sum_x: int, y: int) -> float:
    z = max(1, z or 1)
    y = max(1, y or 1)
    if y <= 1 or z <= 0:
        return 0.0
    val = 100 * (sum_x - z) / (z * (y - 1))
    return max(0.0, min(100.0, val))


def md11_reduction_rate(level_pct: float, cap_pct: float) -> float:
    lvl = snap_bucket20(level_pct)
    cap = snap_bucket20(cap_pct)
    if cap == 0:
        cap = 20
    row = MD11_MATRIX.get(lvl) or MD11_MATRIX[0]
    return (row.get(cap, 0)) / 100


def normalize_standard_code(raw: str) -> str:
    """'ISO 9001' / '9001' / 'iso-9001' → config code."""
    s = str(raw or "").strip()
    digits = "".join(ch for ch in s.lower() if ch.isdigit() or ch == "-")
    # prefer known codes
    cfg = load_md_calc_config()
    codes = {x["code"] for x in cfg["standards"]}
    if s in codes:
        return s
    # strip non-alnum except hyphen
    cleaned = "".join(ch for ch in s.lower() if ch.isalnum() or ch == "-")
    for c in codes:
        if cleaned == c or cleaned.endswith(c) or c in cleaned:
            return c
    # year-suffixed
    for c in ("9001-2026", "14001-2026", "9001", "14001", "45001", "22000", "13485", "50001", "27001", "27701"):
        if c.replace("-", "") in cleaned.replace("-", ""):
            return c
    return cleaned or s


def calculate_base_md(inp: CalcInput, auto_ksic: bool = True) -> MdCalcResult:
    """kab_audit_days.js::calc() 헤드리스 버전 — 기본 MD + stage/surv/recert 스냅샷."""
    cfg = load_md_calc_config()
    if auto_ksic and inp.ksic_code:
        apply_ksic_to_input(inp, cfg)

    emp_n = _effective_emp(inp)
    std_arr = [normalize_standard_code(c) for c in (inp.standards or ["9001"])]
    std_arr = [c for c in std_arr if c]
    if not std_arr:
        std_arr = ["9001"]
    at = inp.audit_type or "initial"
    mode = inp.mode or "single"

    rows: List[Dict[str, Any]] = []
    all_logs: List[Dict[str, Any]] = []
    total_base = 0.0
    first_looked: Optional[Dict[str, Optional[float]]] = None

    for code in std_arr:
        res = calc_std(code, emp_n, inp, cfg)
        base = float(res["base"] or 0)
        total_base = r1(total_base + base)
        used_atype = _get_atype(inp, code)
        std = res.get("std") or {}
        label = f"{std.get('full') or code} — {ATYPE_LABEL.get(used_atype, used_atype)}"
        rows.append({"label": label, "atype": used_atype, "md": base, "code": code})
        all_logs.append({"label": label, "log": res.get("log") or []})
        if first_looked is None and res.get("looked"):
            first_looked = res["looked"]

    intg_reduction = 0.0
    if mode == "integrated" and len(std_arr) >= 2:
        cap_pct = calc_team_capability_pct(inp.intg_team_z, inp.intg_team_sumx, len(std_arr))
        rate = md11_reduction_rate(float(inp.intg_level or 0), cap_pct)
        intg_reduction = r1(total_base * rate)
        if intg_reduction > 0:
            total_base = r1(total_base - intg_reduction)
            all_logs.append({
                "label": "통합심사 감축 (IAF MD11 Fig.1)",
                "log": [[
                    f"통합수준 {inp.intg_level}% × 팀능력비율 {cap_pct:.1f}%",
                    f"단축률 {rate*100:.0f}%",
                    f"-{intg_reduction} M/D",
                ]],
            })

    # multi-site
    sites = max(1, int(inp.site_total or 1))
    site_add = 0.0
    if sites > 1:
        ms = multi_site_sample_count(sites, at, bool(inp.recert_mature))
        site_factor = float(inp.site_factor or 0.5)
        site_days = r1(total_base * site_factor)
        extra = max(0, ms["sample"] - 1)
        site_add = r1(site_days * extra)
        all_logs.append({
            "label": "복수사업장 (IAF MD1)",
            "log": [[
                f"복수사업장 샘플링: y={ms['label']}",
                f"총 {sites}개 → 샘플 {ms['sample']} | 가산",
                f"+{site_add} M/D",
            ]],
        })

    base_days = r1(total_base + site_add)
    final = snap05(base_days)
    limit_min = snap05(base_days * 0.7)
    limit_max = snap05(base_days * 1.3)
    limit_applied = ""
    if final < limit_min:
        final = limit_min
        limit_applied = f"하한 (기준{base_days}×0.7={limit_min})"
    if final > limit_max:
        final = limit_max
        limit_applied = f"상한 (기준{base_days}×1.3={limit_max})"

    is_surv = at in ("surv6", "surv12", "transfer_surv6", "transfer_surv12")
    floor = FLOOR_SURV if is_surv else FLOOR_INITIAL
    floor_applied = False
    if final < floor:
        final = floor
        floor_applied = True

    # stage1/2 + surv/recert 스냅샷 (DDL 컬럼용)
    # 단일 MD5 → 표의 st1/st2/surv/recert; 그 외 → 20/80 배분 + 비율
    ratios = _kab_ratios(cfg)
    if len(std_arr) == 1 and std_arr[0] in cfg.get("md5_standard_map", {}) and first_looked:
        stage1 = snap05(float(first_looked["st1"] or 0))
        stage2 = snap05(float(first_looked["st2"] or 0))
        surv = first_looked["surv"] if first_looked["surv"] is not None else r1((stage1 + stage2) * ratios["surv12"])
        recert = first_looked["recert"] if first_looked["recert"] is not None else r1((stage1 + stage2) * ratios["recert"])
        surv = snap05(float(surv))
        recert = snap05(float(recert))
    else:
        stage1 = snap05(final * 0.2) if at == "initial" else 0.0
        stage2 = snap05(final * 0.8) if at == "initial" else 0.0
        if at == "initial":
            init_total = final
        else:
            # reverse-ish: store initial-equivalent from type MD when possible
            init_total = final
        surv = snap05(r1(init_total * ratios["surv12"])) if at == "initial" else snap05(final if is_surv else r1(init_total * ratios["surv12"]))
        recert = snap05(r1(init_total * ratios["recert"])) if at != "recert" else snap05(final)
        if at == "initial":
            # keep stage split; surv/recert from ratios of stage1+stage2
            init_sum = r1(stage1 + stage2) if (stage1 + stage2) > 0 else final
            surv = snap05(r1(init_sum * ratios["surv12"]))
            recert = snap05(r1(init_sum * ratios["recert"]))
        elif is_surv:
            surv = snap05(final)
            # stage kept as 0 for non-initial application events; still persist table values when MD5 looked
            if first_looked:
                stage1 = snap05(float(first_looked["st1"] or 0))
                stage2 = snap05(float(first_looked["st2"] or 0))
                recert = snap05(float(first_looked["recert"] or r1((stage1 + stage2) * ratios["recert"])))
        elif at == "recert":
            recert = snap05(final)
            if first_looked:
                stage1 = snap05(float(first_looked["st1"] or 0))
                stage2 = snap05(float(first_looked["st2"] or 0))
                surv = snap05(float(first_looked["surv"] or r1((stage1 + stage2) * ratios["surv12"])))

    ksic_match = resolve_ksic(inp.ksic_code, cfg)
    cx_key = inp.complexity or "med"

    detail = {
        "timestamp": None,
        "standards": std_arr,
        "perStandard": rows,
        "employees": emp_n,
        "auditType": at,
        "baseDays": base_days,
        "siteSampling": {"total": sites, "add": site_add, "factor": inp.site_factor},
        "integration": {
            "mode": mode,
            "levelPct": inp.intg_level,
            "teamZ": inp.intg_team_z,
            "teamSumX": inp.intg_team_sumx,
            "reduction": intg_reduction,
        },
        "limitApplied": limit_applied,
        "floor": {"applied": floor_applied, "value": floor},
        "finalDays": final,
        "logs": all_logs,
        "ksic": ksic_match,
        "complexity": cx_key,
        "risk14": inp.risk14,
        "risk45": inp.risk45,
    }

    return MdCalcResult(
        final_days=final,
        base_days=base_days,
        stage1_md=float(stage1),
        stage2_md=float(stage2),
        surveillance_md=float(surv),
        recertification_md=float(recert),
        complexity_key=cx_key,
        complexity_level=COMPLEXITY_KEY_TO_ENUM.get(cx_key, "MEDIUM"),
        iaf_main=str(ksic_match["iaf_main"]) if ksic_match else None,
        iaf_sub=str(ksic_match["iaf_sub"]) if ksic_match else None,
        ksic_code=(inp.ksic_code or "").strip(),
        employees=emp_n,
        audit_type=at,
        standards=std_arr,
        detail_log=detail,
        per_standard=rows,
    )


def calculate_review_md(
    base_md: float,
    add_pct: int,
    subtract_pct: int,
    is_integrated: bool = False,
) -> Tuple[float, float, float]:
    """cb_application_review.php::app_review_* 가감 계산 (기존 md_reviews API 호환)."""
    if base_md <= 0:
        return 0.0, 0.0, 0.0

    limit_pct = 20 if is_integrated else 30
    net_pct = add_pct - subtract_pct
    if net_pct > limit_pct:
        add_pct = subtract_pct + limit_pct
    elif net_pct < -limit_pct:
        subtract_pct = add_pct + limit_pct

    add_md = base_md * (add_pct / 100.0)
    subtract_md = base_md * (subtract_pct / 100.0)
    raw_final = max(0.0, base_md + add_md - subtract_md)
    final_md = snap05(raw_final)
    return round(add_md, 2), round(subtract_md, 2), final_md


def apply_cb_adjustment_ratio(base_md: float, ratio_pct: float) -> float:
    """사용자 DDL 공식: final = base * (1 + ratio/100), 0.5 단위 반올림.

    base_md 는 심사유형에 맞는 기본 MD
    (INITIAL → stage1+stage2, SURVEILLANCE → base_surveillance_md, RECERT → base_recertification_md).
    """
    if base_md is None or base_md <= 0:
        return 0.0
    return snap05(max(0.0, float(base_md) * (1.0 + float(ratio_pct or 0) / 100.0)))


def base_md_for_audit_type(
    audit_type: str,
    stage1: float,
    stage2: float,
    surv: float,
    recert: float,
    engine_final: Optional[float] = None,
) -> float:
    """CB 가감 대상 base 선택."""
    at = (audit_type or "INITIAL").upper()
    if at in ("INITIAL", "SPECIAL", "TRANSFER"):
        return r1(float(stage1 or 0) + float(stage2 or 0)) or float(engine_final or 0)
    if at.startswith("SURVEILLANCE") or at in ("SURV6", "SURV12", "SURVEILLANCE"):
        return float(surv or engine_final or 0)
    if at in ("RECERT", "RECERTIFICATION", "RENEWAL"):
        return float(recert or engine_final or 0)
    return float(engine_final or r1(float(stage1 or 0) + float(stage2 or 0)))


def map_api_audit_type_to_engine(audit_type: str) -> str:
    """API/DDL audit_type → 엔진 atype."""
    key = (audit_type or "INITIAL").strip().upper().replace("-", "_")
    mapping = {
        "INITIAL": "initial",
        "SURVEILLANCE": "surv12",
        "SURVEILLANCE_1": "surv12",
        "SURVEILLANCE_2": "surv12",
        "SURV6": "surv6",
        "SURV12": "surv12",
        "RECERT": "recert",
        "RECERTIFICATION": "recert",
        "RENEWAL": "recert",
        "TRANSFER": "transfer_surv12",
        "SPECIAL": "initial",
    }
    return mapping.get(key, "initial")


def map_engine_atype_to_api(atype: str) -> str:
    m = {
        "initial": "INITIAL",
        "surv6": "SURVEILLANCE_1",
        "surv12": "SURVEILLANCE_1",
        "recert": "RECERT",
        "transfer_surv6": "TRANSFER",
        "transfer_surv12": "TRANSFER",
        "transfer_recert": "TRANSFER",
    }
    return m.get(atype or "initial", "INITIAL")
