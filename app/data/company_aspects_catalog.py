"""EMS / OHS / EnMS characteristic field catalog for company_aspects JSON."""
from __future__ import annotations

from typing import Any, Dict, List

EMS_LOCATION_OPTIONS = [
    "특별대책지역",
    "상수원보호구역",
    "공업단지",
    "도시",
    "농촌",
    "기타",
    "국외인경우",
]

EMS_PERMIT_CLASSES = ["1종", "2종", "3종", "4종", "5종"]

EMS_ASPECT_OPTIONS = [
    "대기방출",
    "미립자",
    "가스",
    "소음",
    "악취",
    "토양오염",
    "지하매립",
    "토양침식",
    "고체폐기물",
    "화학폐기물",
    "수질",
    "폐수방출",
    "지하수",
    "지표수",
    "빗물",
    "천연자원",
    "화석",
    "물",
    "석면",
    "광물",
    "에너지",
    "열발산",
    "방사선",
    "진동",
    "전자파",
    "폐기물",
    "재활용",
    "비부패물",
    "부패물",
    "기타",
]

OHS_HAZARD_OPTIONS = [
    "유해화학물질노출",
    "방사선/방사능",
    "전기자기장노출",
    "가스누출",
    "고온/저온물질취급",
    "독성물질취급",
    "도로 및 도장",
    "레지오넬라균",
    "근골격계질환",
    "폐기물",
    "VDT증후군",
    "고소작업",
    "분진",
    "압력장비",
    "추락 및 낙하",
    "기계 및 장비",
    "소음 및 진동",
    "절단",
    "충돌",
    "감전",
    "기타",
]

ENMS_SOURCE_OPTIONS = [
    "휘발유",
    "등유",
    "경유",
    "아스팔트",
    "연료용 수입무연탄",
    "천연가스(LNG)",
    "도시가스(LPG)",
    "국내무연탄",
    "윤활유",
    "원료용 수입무연탄",
    "연탄(무연탄)",
    "연료용 유연탄(역청탄)",
    "전기",
    "기타",
]

# Updated MD11 intro for integrated applications
INTEGRATED_MD11_INTRO = (
    "여러 ISO 인증을 동시에 신청하시는 경우, 사내 경영시스템이 하나의 체계로 통합 운영되고 있어야 "
    "통합심사(심사일수 감축 혜택) 적용이 가능합니다. 아래 자체 진단 결과에 따라 통합심사 적격 여부가 "
    "확인됩니다. (※ 불충족 항목이 많을 경우 통합심사가 제한되거나 개별 심사로 변경될 수 있습니다.)"
)


def empty_ems() -> Dict[str, Any]:
    return {
        "location": [],
        "permits": {"air": [], "water": [], "noise_vibration": False},
        "hazardous": {"materials": "", "facilities": ""},
        "eia": {
            "done": "",
            "date": "",
            "procedure": "",
            "accident_3y": "",
            "accident_detail": "",
        },
        "aspects": [],
        "records": {
            "compliance_date": "",
            "compliance_procedure": "",
            "emergency_date": "",
            "emergency_procedure": "",
        },
    }


def empty_ohs() -> Dict[str, Any]:
    return {
        "risk": {
            "client_profile": "",
            "assessment_done": "",
            "assessment_date": "",
            "assessment_procedure": "",
            "facilities": "",
            "accident_recent": "",
            "accident_detail": "",
        },
        "hazards": [],
        "records": {
            "compliance_date": "",
            "compliance_procedure": "",
            "emergency_date": "",
            "emergency_procedure": "",
        },
    }


def empty_enms() -> Dict[str, Any]:
    return {
        "energy": {
            "questionnaire_done": "",
            "review_done": "",
            "review_date": "",
            "review_procedure": "",
            "facilities": "",
        },
        "sources": [],
        "records": {
            "baseline_date": "",
            "baseline_procedure": "",
            "performance_date": "",
            "performance_procedure": "",
        },
    }


def aspects_catalog_payload() -> Dict[str, Any]:
    return {
        "ems": {
            "location_options": EMS_LOCATION_OPTIONS,
            "permit_classes": EMS_PERMIT_CLASSES,
            "aspect_options": EMS_ASPECT_OPTIONS,
            "empty": empty_ems(),
        },
        "ohs": {
            "hazard_options": OHS_HAZARD_OPTIONS,
            "empty": empty_ohs(),
        },
        "enms": {
            "source_options": ENMS_SOURCE_OPTIONS,
            "empty": empty_enms(),
        },
        "integrated_md11_intro": INTEGRATED_MD11_INTRO,
    }
