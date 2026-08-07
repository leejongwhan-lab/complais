"""기업 인증신청 설문 카탈로그 (공통 + 표준별 + IAF MD11 통합).

답변 저장:
- certification_application_answers (standard_code / question_key / answer_value / answer_text)
- certification_applications.questionnaire_json
- certification_applications.integrated_check_json (MD11 7문항, 별도)

input types:
- yes_no  → answer_value = yes|no
- select  → answer_value = option value (e.g. 0/1/2/3)
- fill    → answer_value = "fill", answer_text = 사용자 입력
"""
from __future__ import annotations

from typing import Any, Dict, List

from app.data.standards_catalog import format_standard_label, standard_display_payload


def _q(
    key: str,
    label: str,
    input_type: str = "yes_no",
    options: List[str] | None = None,
) -> Dict[str, Any]:
    item: Dict[str, Any] = {"key": key, "label": label, "input": input_type}
    if options is not None:
        item["options"] = options
    return item


# ── A. 공통 질문 (신청 1회) ─────────────────────────────────────────
COMMON_QUESTIONS: List[Dict[str, Any]] = [
    _q(
        "common_q1",
        "교대근무를 운영하고 있습니까? (운영 시 교대조 수)",
        "select",
        ["0", "1", "2", "3"],
    ),
    _q("common_q2", "핵심 공정/업무를 외주(아웃소싱)에 위탁하고 있습니까?", "yes_no"),
    _q("common_q3", "통합심사를 신청하십니까?", "yes_no"),
    _q("common_q4", "원격/재택 근무 인원이 있습니까?", "yes_no"),
]


# ── B. 표준별 질문 ──────────────────────────────────────────────────
QUESTIONNAIRE_CATALOG: Dict[str, Dict[str, Any]] = {
    "9001": {
        "title": "ISO 9001",
        "items": [
            _q("9001_q1", "제품·서비스 설계/개발을 직접 수행합니까?", "yes_no"),
            _q(
                "9001_q2",
                "생산/서비스 공정 단계는 몇 단계입니까? (또는 주요 공정 나열)",
                "fill",
            ),
            _q(
                "9001_q3",
                "고객·법규가 요구하는 특수 사양/규제 적용 대상입니까?",
                "yes_no",
            ),
            _q("9001_q4", "생산 품목(SKU) 수는?", "fill"),
        ],
    },
    "14001": {
        "title": "ISO 14001",
        "items": [
            _q("14001_q1", "배출시설(대기/수질/폐기물) 인허가 대상입니까?", "yes_no"),
            _q("14001_q2", "폐수·폐기물·대기오염물질이 발생합니까?", "yes_no"),
            _q("14001_q3", "유해화학물질을 취급합니까?", "yes_no"),
            _q("14001_q4", "환경영향평가 대상 사업장입니까?", "yes_no"),
            _q("14001_q5", "사업장이 주거지역·생태보호구역에 인접합니까?", "yes_no"),
            _q("14001_q6", "최근 3년간 환경 위반 이력이 있습니까?", "yes_no"),
        ],
    },
    "45001": {
        "title": "ISO 45001",
        "items": [
            _q("45001_q1", "고소·밀폐공간·중장비 작업이 있습니까?", "yes_no"),
            _q("45001_q2", "유해화학물질을 취급합니까?", "yes_no"),
            _q("45001_q3", "건설현장·야외 작업이 있습니까?", "yes_no"),
            _q("45001_q4", "협력업체(외주) 근로자가 상시 함께 작업합니까?", "yes_no"),
            _q("45001_q5", "최근 3년간 중대재해 이력이 있습니까?", "yes_no"),
        ],
    },
    "22000": {
        "title": "ISO 22000",
        "items": [
            _q("22000_q1", "식품을 직접 제조/가공합니까?", "yes_no"),
            _q("22000_q2", "냉장/냉동 유통(콜드체인) 공정을 운영합니까?", "yes_no"),
            _q("22000_q3", "알레르기 유발물질(알러젠)을 취급합니까?", "yes_no"),
            _q("22000_q4", "HACCP 지정/인증 대상입니까?", "yes_no"),
            _q("22000_q5", "생산 품목(SKU) 수는?", "fill"),
        ],
    },
    "27001": {
        "title": "ISO/IEC 27001",
        "items": [
            _q("27001_q1", "자체 IT 시스템·플랫폼·서비스를 운영합니까?", "yes_no"),
            _q("27001_q2", "개인정보를 처리합니까?", "yes_no"),
            _q("27001_q3", "클라우드(IaaS/PaaS/SaaS)를 사용합니까?", "yes_no"),
            _q("27001_q4", "사내 소프트웨어를 개발합니까?", "yes_no"),
            _q("27001_q5", "IT 운영/개발을 외주합니까?", "yes_no"),
            _q("27001_q6", "금융·의료 등 규제 산업에 해당합니까?", "yes_no"),
        ],
    },
    "27701": {
        "title": "ISO/IEC 27701",
        "items": [
            _q(
                "27701_q1",
                "처리하는 정보주체(개인정보) 규모는 대략 얼마입니까?",
                "fill",
            ),
            _q("27701_q2", "민감정보(건강·신념 등)를 처리합니까?", "yes_no"),
            _q("27701_q3", "개인정보를 제3자에게 제공합니까?", "yes_no"),
            _q("27701_q4", "개인정보 처리 업무를 외주합니까?", "yes_no"),
            _q("27701_q5", "개인정보 국외이전이 있습니까?", "yes_no"),
        ],
    },
    "50001": {
        "title": "ISO 50001",
        "items": [
            _q(
                "50001_q1",
                "제조설비를 운영합니까? (주요 에너지 사용 설비 나열)",
                "fill",
            ),
            _q(
                "50001_q2",
                "사용하는 에너지원 종류 수는? (전기·가스·스팀 등)",
                "fill",
            ),
            _q("50001_q3", "연간 에너지 사용 규모는? (예: TOE)", "fill"),
            _q("50001_q4", "에너지 효율 개선 투자/활동을 수행합니까?", "yes_no"),
        ],
    },
    "13485": {
        "title": "ISO 13485",
        "items": [
            _q("13485_q1", "의료기기를 직접 제조합니까? (품목 수)", "fill"),
            _q("13485_q2", "멸균·클린룸 공정이 있습니까?", "yes_no"),
            _q("13485_q3", "취급 의료기기 위험등급은? (1–4)", "fill"),
            _q(
                "13485_q4",
                "해외 인허가(FDA, CE 등) 취득/준비 중입니까?",
                "yes_no",
            ),
            _q("13485_q5", "설계/개발을 직접 수행합니까?", "yes_no"),
        ],
    },
    "37001": {
        "title": "ISO 37001",
        "items": [
            _q(
                "37001_q1",
                "공공기관/정부 업무(입찰·인허가 등)를 수행합니까?",
                "yes_no",
            ),
            _q(
                "37001_q2",
                "대리점·에이전트·중개자를 통한 거래가 있습니까?",
                "yes_no",
            ),
            _q("37001_q3", "해외 사업을 수행합니까?", "yes_no"),
            _q(
                "37001_q4",
                "TI 부패인식지수 하위 국가와 거래가 있습니까?",
                "yes_no",
            ),
        ],
    },
    "37301": {
        "title": "ISO 37301",
        "items": [
            _q(
                "37301_q1",
                "적용 관련 법령 영역 수는? (금융·환경·노동 등)",
                "fill",
            ),
            _q("37301_q2", "해외 사업을 수행합니까?", "yes_no"),
            _q("37301_q3", "규제기관의 정기 관리·감독 대상입니까?", "yes_no"),
            _q(
                "37301_q4",
                "전담 컴플라이언스 조직/인력이 있습니까? (인원 수)",
                "fill",
            ),
        ],
    },
    "22301": {
        "title": "ISO 22301",
        "items": [
            _q("22301_q1", "시스템·핵심 서비스를 24시간 운영합니까?", "yes_no"),
            _q("22301_q2", "장애 시 목표 복구시간(RTO)은?", "fill"),
            _q("22301_q3", "데이터센터·핵심 인프라를 직접 운영합니까?", "yes_no"),
            _q(
                "22301_q4",
                "핵심 공급업체 의존도가 높습니까? (단일 공급 등)",
                "yes_no",
            ),
        ],
    },
}


# ── C. IAF MD11 통합심사 7문항 (표준별 설문과 별도) ─────────────────
INTEGRATED_CHECK_INTRO = (
    "통합심사를 신청하시려면 아래 항목에 대해 예/아니오로 답해 주세요. "
    "각 질문은 경영시스템이 실제로 통합 운영되고 있는지를 확인하기 위한 것입니다."
)

INTEGRATED_CHECK_ITEMS: List[Dict[str, str]] = [
    {
        "key": "intg_1",
        "label": "업무지침·절차서 등이 포함된 통합 문서세트가 적절히 마련되어 있습니까?",
    },
    {
        "key": "intg_2",
        "label": "경영검토 시 전체 사업전략과 계획을 함께 고려하고 있습니까?",
    },
    {
        "key": "intg_3",
        "label": "내부심사를 표준별로 분리하지 않고 통합적으로 접근하고 있습니까?",
    },
    {
        "key": "intg_4",
        "label": "방침과 목표를 표준별로 따로 두지 않고 통합적으로 운영하고 있습니까?",
    },
    {
        "key": "intg_5",
        "label": "시스템 프로세스를 통합된 방식으로 관리하고 있습니까?",
    },
    {
        "key": "intg_6",
        "label": "시정조치·개선 등 개선 메커니즘을 통합적으로 운영하고 있습니까?",
    },
    {
        "key": "intg_7",
        "label": "경영지원과 지침이 통합된 형태로 제공되고 있습니까?",
    },
]

_STANDARD_CODES = [
    "9001",
    "14001",
    "45001",
    "27001",
    "27701",
    "22000",
    "50001",
    "13485",
    "22301",
    "37001",
    "37301",
]

STANDARD_OPTIONS: List[Dict[str, str]] = [
    standard_display_payload(code, mode="enterprise") for code in _STANDARD_CODES
]


def catalog_for_standards(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for code in codes:
        key = (code or "").strip().lower()
        # strip non-digits for keys like "9001"
        digits = "".join(ch for ch in key if ch.isdigit())
        lookup = digits if digits in QUESTIONNAIRE_CATALOG else key
        if lookup in QUESTIONNAIRE_CATALOG:
            block = dict(QUESTIONNAIRE_CATALOG[lookup])
            block["title"] = format_standard_label(lookup, mode="enterprise")
            block["display"] = standard_display_payload(lookup, mode="enterprise")
            out[lookup] = block
    return out


def full_catalog_payload(codes: List[str] | None = None) -> Dict[str, Any]:
    """API /catalog · questionnaire_json 스냅샷용."""
    selected = [c.strip().lower() for c in (codes or []) if c and str(c).strip()]
    return {
        "common_questions": COMMON_QUESTIONS,
        "questionnaire": catalog_for_standards(selected) if selected else {},
        "integrated_check_intro": INTEGRATED_CHECK_INTRO,
        "integrated_check_items": INTEGRATED_CHECK_ITEMS,
        "standards": STANDARD_OPTIONS,
    }
