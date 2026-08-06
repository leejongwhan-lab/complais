"""스토리보드 기반 인증수행범위(Scope) 택소노미.

용어 시트 '코드 필요유무' + 전용 코드마스터 시트:
- IAF 1–39: ISO 9001 / 14001 / 45001 전용
- MDQMS: ISO 13485 계층코드 A~G
- FSMS: ISO 22000 식품 카테고리
- NQMS: ISO 19443 원자력 공급망 A~G
- BCMS: ISO 22301 섹터 A~F (전용 시트 존재)
- none: EnMS/ISMS/PIMS/ABMS/CMS/AIMS — 수행범위 코드 없음
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TAXONOMY_LABELS: Dict[str, str] = {
    'iaf39': 'IAF 코드 01–39 (QMS/EMS/OHSMS)',
    'mdqms': '의료기기 기술분야 코드 (ISO 13485)',
    'fsms': '식품안전 카테고리 (ISO 22000)',
    'nqms': '원자력 공급망 분류 (ISO 19443)',
    'bcms': '사업연속성 섹터 (ISO 22301)',
    'none': '인증수행범위 코드 없음',
}

STANDARD_SCOPE_TAXONOMY: Dict[str, str] = {
    'ISO 9001:2015': 'iaf39',
    'ISO 9001:2026': 'iaf39',
    'ISO 14001:2015': 'iaf39',
    'ISO 14001:2026': 'iaf39',
    'ISO 45001:2018': 'iaf39',
    'ISO 50001:2018': 'none',
    'ISO/IEC 27001:2022': 'none',
    'ISO/IEC 27701:2019': 'none',
    'ISO 37001:2016': 'none',
    'ISO 37301:2021': 'none',
    'ISO 22301:2019': 'bcms',
    'ISO 22000:2018': 'fsms',
    'ISO 13485:2016': 'mdqms',
    'ISO/IEC 42001:2023': 'none',
    'ISO 19443:2018': 'nqms',
}

IAF39_STANDARDS = {c for c, t in STANDARD_SCOPE_TAXONOMY.items() if t == "iaf39"}

SCOPE_CODE_SEED: List[Tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str], int, Dict[str, Any]]] = [
    ('iaf39', '01', '농업, 임업 및 어업', 'Agriculture, forestry and fishing', None, None, 1, {}),
    ('iaf39', '02', '광업 채석업', 'Mining and quarrying', None, None, 2, {}),
    ('iaf39', '03', '음식료 및 담배', 'Food products, beverages and tobacco', None, None, 3, {}),
    ('iaf39', '04', '섬유 및 섬유제품', 'Textiles and textile products', None, None, 4, {}),
    ('iaf39', '05', '가죽 및 가죽제품', 'Leather and leather products', None, None, 5, {}),
    ('iaf39', '06', '목재 및 목재제품', 'Wood and wood products', None, None, 6, {}),
    ('iaf39', '07', '펄프, 종이, 종이제품', 'Pulp, paper and paper products', None, None, 7, {}),
    ('iaf39', '08', '출판업', 'Publishing companies', None, None, 8, {}),
    ('iaf39', '09', '인쇄업', 'Printing companies', None, None, 9, {}),
    ('iaf39', '10', '코르스 제조 및 석유 정제품', 'Manufacture of coke and refined petroleum products', None, None, 10, {}),
    ('iaf39', '11', '핵연료', 'Nuclear fuel', None, None, 11, {}),
    ('iaf39', '12', '화학약품, 화학제품, 섬유류', 'Chemicals, chemical products and fibres', None, None, 12, {}),
    ('iaf39', '13', '의료용 물질 및 의약품', 'Pharmaceuticals', None, None, 13, {}),
    ('iaf39', '14', '고무 및 플라스틱제품', 'Rubber and plastic products', None, None, 14, {}),
    ('iaf39', '15', '비금속 광물제품', 'Non-metallic mineral products', None, None, 15, {}),
    ('iaf39', '16', '콘크리트, 시멘트, 석회 및 플라스터 등', 'Concrete, cement, lime, plaster etc.', None, None, 16, {}),
    ('iaf39', '17', '1차 금속 및 금속가공제품', 'Basic metals and fabricated metal products', None, None, 17, {}),
    ('iaf39', '18', '기계 및 장비', 'Machinery and equipment', None, None, 18, {}),
    ('iaf39', '19', '전기 및 광학기기', 'Electrical and optical equipment', None, None, 19, {}),
    ('iaf39', '20', '조선업', 'Shipbuilding', None, None, 20, {}),
    ('iaf39', '21', '항공기', 'Aerospace', None, None, 21, {}),
    ('iaf39', '22', '기타 수송장비', 'Other transport equipment', None, None, 22, {}),
    ('iaf39', '23', '기타 제조업', 'Manufacturingnotelsewhereclassified', None, None, 23, {}),
    ('iaf39', '24', '재생', 'Recycling', None, None, 24, {}),
    ('iaf39', '25', '전기공급', 'Electricity supply', None, None, 25, {}),
    ('iaf39', '26', '연료용 가스공급', 'Gas supply', None, None, 26, {}),
    ('iaf39', '27', '수도및 증기 공급', 'Water supply', None, None, 27, {}),
    ('iaf39', '28', '건설', 'Construction', None, None, 28, {}),
    ('iaf39', '29', '도소매업, 자동차 및 모터사이클 수리, 개인 및 가정용품 수리', 'Wholesale and retail trade; repair of motor vehicles, motorcycles and personal and household goods', None, None, 29, {}),
    ('iaf39', '30', '숙박업, 음식점업 및 주점', 'Hotels and restaurants', None, None, 30, {}),
    ('iaf39', '31', '운송업, 창고업 및 통신', 'Transport, storage and communication', None, None, 31, {}),
    ('iaf39', '32', '금융업, 보험업, 부동산업 및 임대', 'Financial intermediation; real estate; renting', None, None, 32, {}),
    ('iaf39', '33', '정보기술', 'Information technology', None, None, 33, {}),
    ('iaf39', '34', '전문, 과학 및 기술서비스', 'Engineering services', None, None, 34, {}),
    ('iaf39', '35', '기타 서비스', 'Other services', None, None, 35, {}),
    ('iaf39', '36', '공공행정', 'Public administration', None, None, 36, {}),
    ('iaf39', '37', '교육 서비스', 'Education', None, None, 37, {}),
    ('iaf39', '38', '보건업 및 사회복지 서비스', 'Health and social work', None, None, 38, {}),
    ('iaf39', '39', '기타 사회 서비스', 'Other social services', None, None, 39, {}),
    ('mdqms', 'AI', '비능동 일반 의료기기', 'General non-active medical devices', 'A', 'A', 1, {'group': 'A'}),
    ('mdqms', 'AII', '비능동 임플란트', 'Non-active implants', 'A', 'A', 2, {'group': 'A'}),
    ('mdqms', 'AIII', '창상처치용 의료기기', 'Devices for wound care', 'A', 'A', 3, {'group': 'A'}),
    ('mdqms', 'AIV', '비능동 치과용 기기 및 장비', 'Non-active dental devices and equipment', 'A', 'A', 4, {'group': 'A'}),
    ('mdqms', 'AV', '기타 비능동 의료기기', 'Non-active medical devices other than specified above', 'A', 'A', 5, {'group': 'A'}),
    ('mdqms', 'BI', '능동 일반 의료기기', 'General active medical devices', 'B', 'B', 6, {'group': 'B'}),
    ('mdqms', 'BII', '영상 진단용 기기', 'Devices for imaging', 'B', 'B', 7, {'group': 'B'}),
    ('mdqms', 'BIII', '환자 감시용 기기', 'Monitoring devices', 'B', 'B', 8, {'group': 'B'}),
    ('mdqms', 'BIV', '방사선 및 열 치료용 기기', 'Devices for radiation therapy and thermo therapy', 'B', 'B', 9, {'group': 'B'}),
    ('mdqms', 'BV', '기타 능동 의료기기', 'Active medical devices other than specified above', 'B', 'B', 10, {'group': 'B'}),
    ('mdqms', 'CI', '능동 이식형 일반 의료기기', 'General active implantable medical devices', 'C', 'C', 11, {'group': 'C'}),
    ('mdqms', 'CII', '기타 능동 이식형 의료기기', 'Active implantable medical devices other than specified above', 'C', 'C', 12, {'group': 'C'}),
    ('mdqms', 'DI', '진단시약, 교정물질 및 대조물질', 'Reagents and reagent products, calibrators and control materials', 'D', 'D', 13, {'group': 'D'}),
    ('mdqms', 'DII', '체외진단용 기기 및 소프트웨어', 'In vitro diagnostic instruments and software', 'D', 'D', 14, {'group': 'D'}),
    ('mdqms', 'DIII', '기타 체외진단용 의료기기', 'In vitro diagnostic medical devices other than specified above', 'D', 'D', 15, {'group': 'D'}),
    ('mdqms', 'EI', '에틸렌옥사이드(EO) 가스 멸균', 'Ethylene oxide gas sterilization (EO)', 'E', 'E', 16, {'group': 'E'}),
    ('mdqms', 'EII', '습열 멸균', 'Moist heat sterilization', 'E', 'E', 17, {'group': 'E'}),
    ('mdqms', 'EIII', '무균 공정', 'Aseptic processing', 'E', 'E', 18, {'group': 'E'}),
    ('mdqms', 'EIV', '방사선 멸균', 'Radiation sterilization', 'E', 'E', 19, {'group': 'E'}),
    ('mdqms', 'EV', '기타 멸균 방식', 'Sterilization methods other than specified above', 'E', 'E', 20, {'group': 'E'}),
    ('mdqms', 'FI', '의약품 조합 의료기기', 'Medical devices incorporating medicinal substances', 'F', 'F', 21, {'group': 'F'}),
    ('mdqms', 'FII', '동물유래 조직 활용 의료기기', 'Medical devices utilizing tissues of animal origin', 'F', 'F', 22, {'group': 'F'}),
    ('mdqms', 'FIII', '인간혈액 유도체 조합 의료기기', 'Medical devices incorporating derivatives of human blood', 'F', 'F', 23, {'group': 'F'}),
    ('mdqms', 'FIV', '마이크로메카닉스 활용 의료기기', 'Medical devices utilizing micromechanics', 'F', 'F', 24, {'group': 'F'}),
    ('mdqms', 'FV', '나노물질 활용 의료기기', 'Medical devices utilizing nanomaterials', 'F', 'F', 25, {'group': 'F'}),
    ('mdqms', 'FVI', '생물학적 활성 코팅 또는 체내 흡수성 의료기기', 'Medical devices with biological active coating/materials or absorbed entirely/mainly', 'F', 'F', 26, {'group': 'F'}),
    ('mdqms', 'FVII', '기타 특수 기술·물질 활용 의료기기', 'Medical devices incorporating/utilizing other specific substances, technologies', 'F', 'F', 27, {'group': 'F'}),
    ('mdqms', 'GI', '원자재 공급', 'Raw materials', 'G', 'G', 28, {'group': 'G'}),
    ('mdqms', 'GII', '구성품 및 부품 공급', 'Components', 'G', 'G', 29, {'group': 'G'}),
    ('mdqms', 'GIII', '부분조립품 공급', 'Sub-assemblies', 'G', 'G', 30, {'group': 'G'}),
    ('mdqms', 'GIV', '교정 서비스', 'Calibration services', 'G', 'G', 31, {'group': 'G'}),
    ('mdqms', 'GV', '유통 서비스', 'Distribution services', 'G', 'G', 32, {'group': 'G'}),
    ('mdqms', 'GVI', '유지보수 서비스', 'Maintenance services', 'G', 'G', 33, {'group': 'G'}),
    ('mdqms', 'GVII', '운송 서비스', 'Transportation services', 'G', 'G', 34, {'group': 'G'}),
    ('mdqms', 'GVIII', '기타 서비스', 'Other services', 'G', 'G', 35, {'group': 'G'}),
    ('fsms', 'AI', '정육/우유/계란/꿀 생산을 위한 동물사육', '(Farming of animals for meat/milk/eggs/honey)', 'A', '1차 생산', 1, {'mid_code': 'A', 'mid_name_ko': '축산업/수산업'}),
    ('fsms', 'AII', '생선과 수산물의 양식', '(Farming of fish and seafood)', 'A', '1차 생산', 2, {'mid_code': 'A', 'mid_name_ko': '축산업/수산업'}),
    ('fsms', 'BI', '재배 - 식물 (곡류와 두류 제외)', '(Farming – Handling of plants (other than grains and pulses))', 'B', '1차 생산', 3, {'mid_code': 'B', 'mid_name_ko': '농업'}),
    ('fsms', 'BII', '재배 - 곡류 및 두류', '(Farming – Handling of grains and pulses)', 'B', '1차 생산', 4, {'mid_code': 'B', 'mid_name_ko': '농업'}),
    ('fsms', 'BIII', '식물의 가공 전 처리', '(Pre-process handling of plant products)', 'B', '1차 생산', 5, {'mid_code': 'B', 'mid_name_ko': '농업'}),
    ('fsms', 'C0', '동물 - 1차 변환', '(Animal – Primary conversion)', 'C', '사람 및 동물용 식품 가공', 6, {'mid_code': 'C', 'mid_name_ko': '식품, 성분재료 및 반려동물 먹이 가공'}),
    ('fsms', 'CI', '부패하기 쉬운 동물성 제품의 가공', '(Processing of perishable animal products)', 'C', '사람 및 동물용 식품 가공', 7, {'mid_code': 'C', 'mid_name_ko': '식품, 성분재료 및 반려동물 먹이 가공'}),
    ('fsms', 'CII', '부패하기 쉬운 식물성 제품의 가공', '(Processing of perishable plant-based products)', 'C', '사람 및 동물용 식품 가공', 8, {'mid_code': 'C', 'mid_name_ko': '식품, 성분재료 및 반려동물 먹이 가공'}),
    ('fsms', 'CIII', '부패하기 쉬운 동물성 및 식물성 제품의 가공(혼합 식품)', '(Processing of perishable animal and plant products (mixed products))', 'C', '사람 및 동물용 식품 가공', 9, {'mid_code': 'C', 'mid_name_ko': '식품, 성분재료 및 반려동물 먹이 가공'}),
    ('fsms', 'CIV', '상온에서 유통되는 제품의 가공', '(Processing of ambient stable products)', 'C', '사람 및 동물용 식품 가공', 10, {'mid_code': 'C', 'mid_name_ko': '식품, 성분재료 및 반려동물 먹이 가공'}),
    ('fsms', 'D', '사료 및 동물용 먹이 가공', '(Feed and animal food production)', 'D', '사람 및 동물용 식품 가공', 11, {'mid_code': 'D', 'mid_name_ko': '사료 및 동물용 먹이 가공'}),
    ('fsms', 'E', '케이터링/음식 서비스', '(Catering/food service)', 'E', '케이터링/음식 서비스', 12, {'mid_code': 'E', 'mid_name_ko': '케이터링/음식 서비스'}),
    ('fsms', 'FI', '소매/도매', '(Retail/wholesale)', 'F', '소매, 운송 및 보관', 13, {'mid_code': 'F', 'mid_name_ko': '거래, 소매 및 전자상거래'}),
    ('fsms', 'FII', '식품 중개/거래', '(Brokering/trading)', 'F', '소매, 운송 및 보관', 14, {'mid_code': 'F', 'mid_name_ko': '거래, 소매 및 전자상거래'}),
    ('fsms', 'G', '운송 및 보관 서비스', '(Transport and storage services)', 'G', '소매, 운송 및 보관', 15, {'mid_code': 'G', 'mid_name_ko': '운송 및 보관 서비스'}),
    ('fsms', 'H', '서비스', '(Services)', 'H', '보조서비스', 16, {'mid_code': 'H', 'mid_name_ko': '서비스'}),
    ('fsms', 'I', '포장재 생산', '(Production of packaging material)', 'I', '포장재', 17, {'mid_code': 'I', 'mid_name_ko': '포장재 생산'}),
    ('fsms', 'J', '장비', '(Equipment)', 'J', '보조 장비', 18, {'mid_code': 'J', 'mid_name_ko': '장비'}),
    ('fsms', 'K', '화학제품 및 생화학제품', '(Chemical and bio-chemical)', 'K', '화학/생물학', 19, {'mid_code': 'K', 'mid_name_ko': '화학제품 및 생화학제품'}),
    ('nqms', 'A', '기계 및 구조물', 'Mechanical and structures', None, None, 1, {'related_iaf': '16, 17, 18'}),
    ('nqms', 'B', '전기기기 및 계측제어', 'Electrical equipment', None, None, 2, {'related_iaf': '19'}),
    ('nqms', 'C', '핵연료', 'Nuclear fuel', None, None, 3, {'related_iaf': '11'}),
    ('nqms', 'D', '발전 및 송전', 'Electricity generation and supply', None, None, 4, {'related_iaf': '25'}),
    ('nqms', 'E', '건설', 'Construction', None, None, 5, {'related_iaf': '28, 34'}),
    ('nqms', 'F', '운송 및 폐기물 처리', 'Transportation and waste treatment', None, None, 6, {'related_iaf': '39'}),
    ('nqms', 'G', '정보기술', 'Information technology', None, None, 7, {'related_iaf': '33'}),
    ('bcms', 'A', '화학', 'Chemicals', None, 'BCMS', 1, {}),
    ('bcms', 'B', '1차 산업', 'Agriculture, forestry and fishing', None, 'BCMS', 2, {}),
    ('bcms', 'C', '광업 및 건설', 'Mining and construction', None, 'BCMS', 3, {}),
    ('bcms', 'D', '공급', 'Electronics and mechanics', None, 'BCMS', 4, {}),
    ('bcms', 'E', '제조', 'Manufacturing', None, 'BCMS', 5, {}),
    ('bcms', 'F', '서비스', 'Services', None, 'BCMS', 6, {}),
]


def taxonomy_for_standard(standard_code: str) -> str:
    code = (standard_code or "").strip()
    if code in STANDARD_SCOPE_TAXONOMY:
        return STANDARD_SCOPE_TAXONOMY[code]
    upper = code.upper().replace(" ", "")
    if "9001" in upper or "14001" in upper or "45001" in upper:
        return "iaf39"
    if "13485" in upper:
        return "mdqms"
    if "22000" in upper:
        return "fsms"
    if "19443" in upper:
        return "nqms"
    if "22301" in upper:
        return "bcms"
    return "none"


def uses_iaf39(standard_code: str) -> bool:
    return taxonomy_for_standard(standard_code) == "iaf39"


def codes_for_taxonomy(taxonomy: str) -> List[Dict[str, Any]]:
    items = []
    for tax, code, ko, en, parent, group, sort_order, meta in SCOPE_CODE_SEED:
        if tax != taxonomy:
            continue
        items.append({
            "code": code,
            "name_ko": ko,
            "name_en": en,
            "parent_code": parent,
            "group_label": group,
            "sort_order": sort_order,
            "meta": meta or {},
        })
    return items


def normalize_scope_code(taxonomy: str, raw: str) -> str:
    t = (raw or "").strip()
    if not t:
        return ""
    if taxonomy == "iaf39":
        return t.zfill(2) if t.isdigit() else t
    if taxonomy == "fsms":
        return "".join(t.split())
    return t


def standard_scope_meta(standard_code: str) -> Dict[str, Any]:
    tax = taxonomy_for_standard(standard_code)
    return {
        "standard_code": standard_code,
        "taxonomy": tax,
        "taxonomy_label": TAXONOMY_LABELS.get(tax, tax),
        "has_scope_codes": tax != "none",
        "codes": codes_for_taxonomy(tax) if tax != "none" else [],
    }
