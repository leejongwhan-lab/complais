"""면담(interview) 템플릿 — audit_v15_final_1.html INTERVIEWS 이식.

키는 platform family_code (QMS/EMS/OHSMS…) + COMMON.
세션 표준(QMS_2015 등) → family로 매핑해 필수 면담 목록을 만든다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


# family_code → interview role templates (from v15)
INTERVIEW_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "COMMON": [
        {
            "role": "최고경영자 면담",
            "icon": "👔",
            "mandatory": True,
            "questions": [
                "경영시스템에 대한 귀하의 리더십과 의지를 어떻게 표현하고 있습니까?",
                "조직의 전략적 방향과 경영시스템 목표가 어떻게 연계됩니까?",
                "경영시스템 목표 달성을 위해 어떤 자원을 배분하고 있습니까?",
                "ESG 및 지속가능경영에 대한 경영 의지와 구체적 계획은 무엇입니까?",
                "최근 경영검토에서 논의된 주요 의사결정 내용은 무엇입니까?",
            ],
        },
        {
            "role": "경영대리인/관리책임자 면담",
            "icon": "🗂",
            "mandatory": False,
            "questions": [
                "경영시스템의 수립·유지·개선을 위한 주요 활동을 설명해 주십시오.",
                "내외부 이슈 파악 및 이해관계자 요구사항 관리 방법은?",
                "부적합 발생 시 처리 절차와 최근 주요 부적합 사례를 설명해 주십시오.",
                "내부심사 결과 및 경영검토 후속 조치 이행 현황은?",
                "문서화된 정보 관리 및 기록 보존 체계를 설명해 주십시오.",
            ],
        },
        {
            "role": "기후변화 담당 임원/ESG팀장 면담",
            "icon": "🌍",
            "mandatory": False,
            "questions": [
                "기후변화 리스크(물리적·전환) 파악 방법과 주요 결과는?",
                "1.5℃/2℃ 시나리오 분석을 실시하였습니까? 재무 영향은 어떻게 정량화합니까?",
                "Net-Zero 목표와 SBTi 승인 현황을 설명해 주십시오.",
                "TCFD·CSRD·CDP 등 기후 공시 이행 현황은?",
                "탄소중립 이행을 위한 재원 조달 계획(녹색채권, 탄소크레딧 등)은?",
            ],
        },
    ],
    "QMS": [
        {
            "role": "품질관리 책임자 면담",
            "icon": "✅",
            "mandatory": False,
            "questions": [
                "고객 요구사항 파악 및 계약 검토 프로세스를 설명해 주십시오.",
                "제품/서비스 품질 기획 및 공정 관리 기준은 무엇입니까?",
                "고객 불만 처리 절차 및 최근 주요 불만 사례 대응 내용은?",
                "공급자 평가 기준 및 ESG 평가 항목 적용 현황을 설명해 주십시오.",
                "고객만족도 측정 방법 및 최근 결과를 공유해 주십시오.",
            ],
        },
        {
            "role": "현장 작업자 면담 (품질)",
            "icon": "🔧",
            "mandatory": False,
            "questions": [
                "작업 표준서/절차서를 인지하고 있습니까? 언제 마지막으로 교육받았습니까?",
                "불량 발생 시 어떻게 처리합니까? (보고 절차)",
                "품질 목표를 알고 있습니까?",
            ],
        },
    ],
    "EMS": [
        {
            "role": "환경경영 책임자 면담",
            "icon": "🌿",
            "mandatory": False,
            "questions": [
                "유의한 환경측면 파악 및 통제 방법을 설명해 주십시오.",
                "온실가스 배출량 측정·기록·검증 절차는 어떻게 됩니까?",
                "환경 법규 목록 관리 및 준수 평가 실시 현황은?",
                "탄소감축 목표 및 재생에너지 사용 계획을 설명해 주십시오.",
                "환경 비상사태 대응 계획 및 최근 훈련 실시 현황은?",
            ],
        },
        {
            "role": "현장 작업자 면담 (환경)",
            "icon": "♻️",
            "mandatory": False,
            "questions": [
                "본인 업무에서 발생하는 환경측면(폐기물·배출·용수 등)을 알고 있습니까?",
                "폐기물 분리배출 절차를 설명해 주십시오.",
                "환경 비상사태 발생 시 대응 절차를 알고 있습니까?",
                "환경 목표를 알고 있습니까?",
            ],
        },
    ],
    "OHSMS": [
        {
            "role": "안전보건 책임자(관리자) 면담",
            "icon": "🦺",
            "mandatory": False,
            "questions": [
                "위험성 평가 절차 및 최근 실시 현황을 설명해 주십시오.",
                "고위험 작업 통제 방법 및 PPE 관리 현황은?",
                "협력사 안전보건 관리 절차 및 합동 점검 실시 현황은?",
                "중대재해처벌법 준수를 위한 이행 현황을 설명해 주십시오.",
                "아차사고 신고 활성화를 위한 제도/문화 현황은?",
            ],
        },
        {
            "role": "근로자 대표/안전보건위원회 위원 면담",
            "icon": "👥",
            "mandatory": True,
            "questions": [
                "안전보건위원회 운영 현황(개최 주기, 주요 안건)을 설명해 주십시오.",
                "근로자의 안전보건 의견이 경영시스템에 반영되는 절차는?",
                "위험 작업 거부권을 알고 있습니까? 실제 행사 사례가 있습니까?",
                "내부 안전신고 채널을 알고 있습니까? 신고 후 처리 절차는?",
                "최근 1년간 산업재해 및 아차사고 발생 현황과 재발 방지 조치는?",
            ],
        },
        {
            "role": "현장 근로자 면담 (안전)",
            "icon": "⛑️",
            "mandatory": False,
            "questions": [
                "본인 업무의 주요 위험요인을 알고 있습니까?",
                "PPE 지급 현황 및 착용 의무화 여부를 설명해 주십시오.",
                "작업 중 위험 발견 시 어떻게 조치합니까?",
                "안전교육을 언제 마지막으로 받았습니까?",
            ],
        },
    ],
    "MDQMS": [
        {
            "role": "품질보증/규제업무 책임자 면담",
            "icon": "🏥",
            "mandatory": False,
            "questions": [
                "의료기기 규제 요구사항(FDA/MDR/의기법) 파악 및 준수 현황은?",
                "설계·개발 및 밸리데이션 프로세스를 설명해 주십시오.",
                "이상사례 모니터링 및 규제기관 보고 절차는?",
                "공급자 관리 및 위탁 제조(OEM) 통제 방법은?",
                "UDI 부여 및 추적성 확보 현황을 설명해 주십시오.",
            ],
        },
    ],
    "FSMS": [
        {
            "role": "식품안전팀장 면담",
            "icon": "🍽️",
            "mandatory": False,
            "questions": [
                "HACCP 플랜 수립 및 CCP 관리 현황을 설명해 주십시오.",
                "알레르기 물질 관리 및 교차오염 방지 절차는?",
                "선행요건 프로그램(PRP) 이행 현황은?",
                "식품안전사고 발생 시 회수 절차를 설명해 주십시오.",
                "공급 원료의 식품안전 리스크 관리 방법은?",
            ],
        },
        {
            "role": "현장 작업자 면담 (식품안전)",
            "icon": "🧑‍🍳",
            "mandatory": False,
            "questions": [
                "CCP 모니터링 방법 및 이탈 발생 시 처리 절차를 알고 있습니까?",
                "개인위생 기준(손세척, 위생복 착용 등)을 설명해 주십시오.",
                "이물질 발견 시 어떻게 처리합니까?",
            ],
        },
    ],
    "ISMS": [
        {
            "role": "CISO/정보보안 책임자 면담",
            "icon": "🔐",
            "mandatory": False,
            "questions": [
                "정보자산 분류 및 위험 평가 프로세스를 설명해 주십시오.",
                "접근통제 정책 및 특권 계정 관리 현황은?",
                "보안 사고 대응 절차 및 최근 사고 사례는?",
                "제3자(공급자) 정보보안 관리 방법은?",
                "취약점 관리 및 패치 적용 주기를 설명해 주십시오.",
            ],
        },
        {
            "role": "일반 직원 면담 (정보보안 인식)",
            "icon": "💻",
            "mandatory": False,
            "questions": [
                "정보보안 방침을 알고 있습니까?",
                "피싱 이메일 식별 방법을 알고 있습니까?",
                "보안 사고 발생 시 신고 절차는?",
            ],
        },
    ],
    "EnMS": [
        {
            "role": "에너지 관리자 면담",
            "icon": "⚡",
            "mandatory": False,
            "questions": [
                "에너지 기준선(EnB) 및 에너지 성과지표(EnPI) 설정 근거는?",
                "유의한 에너지 사용처(SEU) 식별 및 관리 현황은?",
                "에너지 절감 목표 달성을 위한 주요 개선 활동은?",
                "에너지 설계 검토 프로세스를 설명해 주십시오.",
                "에너지 측정 장비 교정 및 데이터 품질 관리 현황은?",
            ],
        },
    ],
    "ABMS": [
        {
            "role": "준법/반부패 책임자 면담",
            "icon": "⚖",
            "mandatory": False,
            "questions": [
                "부패방지 방침과 뇌물·이해충돌 관리 절차를 설명해 주십시오.",
                "고위험 거래·선물접대 통제 현황은?",
                "내부신고(Whistleblowing) 채널 운영 및 최근 처리 사례는?",
                "협력사 실사(Due Diligence) 절차는?",
                "최근 컴플라이언스 교육 실시 현황은?",
            ],
        },
    ],
    "CMS": [
        {
            "role": "준법경영 책임자 면담",
            "icon": "📋",
            "mandatory": False,
            "questions": [
                "준법경영시스템 범위와 의무 파악 절차를 설명해 주십시오.",
                "법규 변경 모니터링 및 준수 평가 현황은?",
                "준법 리스크 평가 및 통제 활동은?",
                "내부고발·조사 절차와 최근 사례는?",
                "경영진 보고 및 개선 조치 이행 현황은?",
            ],
        },
    ],
    "PIMS": [
        {
            "role": "개인정보보호 책임자(CPO) 면담",
            "icon": "🔏",
            "mandatory": False,
            "questions": [
                "개인정보 처리 목적·항목·보존기간 관리 현황은?",
                "DPIA(개인정보 영향평가) 수행 절차 및 최근 결과는?",
                "정보주체 권리(열람·삭제·이동) 처리 절차는?",
                "개인정보 처리위탁 관리 및 국외이전 통제 방법은?",
                "개인정보 침해 사고 대응 절차 및 최근 사례는?",
            ],
        },
    ],
    "AIMS": [
        {
            "role": "AI 거버넌스 책임자 면담",
            "icon": "🤖",
            "mandatory": False,
            "questions": [
                "AI 시스템 목록·용도·리스크 등급 관리 현황은?",
                "AI 개발·배포 시 인간 감독 및 투명성 확보 방법은?",
                "편향·차별·안전성 평가 절차는?",
                "AI 관련 사고·민원 대응 절차는?",
                "공급망 AI 구성요소 통제 방법은?",
            ],
        },
    ],
    "NSMS": [
        {
            "role": "원자력 품질/안전 책임자 면담",
            "icon": "☢",
            "mandatory": False,
            "questions": [
                "원자력 공급망 품질 요구사항 파악 및 적용 현황은?",
                "위조·부정품(CFSI) 방지 절차는?",
                "특별공정·검사·시험 통제 현황은?",
                "부적합·시정조치 및 규제 보고 절차는?",
                "교육·자격 관리 현황을 설명해 주십시오.",
            ],
        },
    ],
}


def family_from_standard_key(standard_key: Optional[str]) -> Optional[str]:
    if not standard_key:
        return None
    s = str(standard_key).strip()
    if not s:
        return None
    return s.split("_")[0].upper() if "_" in s else s.upper()


def list_interviews_for_standards(
    standard_keys: Sequence[str],
) -> List[Dict[str, Any]]:
    """Deduped interview roles for COMMON + selected standard families (v15 order)."""
    families: List[str] = ["COMMON"]
    seen_fam = {"COMMON"}
    for sk in standard_keys or []:
        fam = family_from_standard_key(sk)
        if fam and fam not in seen_fam and fam != "COMMON":
            seen_fam.add(fam)
            families.append(fam)

    out: List[Dict[str, Any]] = []
    seen_roles: set = set()
    for fam in families:
        for iv in INTERVIEW_TEMPLATES.get(fam, []):
            role = iv["role"]
            if role in seen_roles:
                continue
            seen_roles.add(role)
            out.append(
                {
                    "role_key": f"{fam}::{role}",
                    "role": role,
                    "icon": "",  # text-only UI — no decorative icons
                    "mandatory": bool(iv.get("mandatory")),
                    "family_code": fam,
                    "questions": list(iv.get("questions") or []),
                }
            )
    return out
