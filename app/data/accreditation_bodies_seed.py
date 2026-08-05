"""인정기관(AB) 마스터 시드 데이터 — 대륙/국가코드/이니셜/영문풀네임."""
from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.models.master import AccreditationBodies

# (continent, country_code, code, name_en)
ACCREDITATION_BODY_SEED: List[Tuple[str, str, str, str]] = [
    # Asia
    ("Asia", "KR", "KAB", "Korea Accreditation Board"),
    ("Asia", "JP", "JAB", "Japan Accreditation Board"),
    ("Asia", "CN", "CNAS", "China National Accreditation Service for Conformity Assessment"),
    ("Asia", "TW", "TAF", "Taiwan Accreditation Foundation"),
    ("Asia", "IN", "NABCB", "National Accreditation Board for Certification Bodies"),
    ("Asia", "SG", "SAC", "Singapore Accreditation Council"),
    ("Asia", "VN", "BoA", "Bureau of Accreditation"),
    ("Asia", "TH", "NSC", "National Standardization Council of Thailand"),
    ("Asia", "MY", "DSM", "Department of Standards Malaysia"),
    ("Asia", "ID", "KAN", "Komite Akreditasi Nasional"),
    ("Asia", "PH", "PAB", "Philippine Accreditation Bureau"),
    ("Asia", "HK", "HKAS", "Hong Kong Accreditation Service"),
    ("Asia", "MN", "MNAS", "Mongolian Agency for Standard and Metrology"),
    ("Asia", "KZ", "NCA", "National Center of Accreditation"),
    ("Asia", "UZ", "O'ZAKK", "Uzbek Center for Accreditation"),
    ("Asia", "PK", "PNAC", "Pakistan National Accreditation Council"),
    ("Asia", "LK", "SLAB", "Sri Lanka Accreditation Board"),
    ("Asia", "BD", "BAB", "Bangladesh Accreditation Board"),
    # Oceania
    ("Oceania", "AU/NZ", "JAS-ANZ", "Joint Accreditation System of Australia and New Zealand"),
    # Europe
    ("Europe", "GB", "UKAS", "United Kingdom Accreditation Service"),
    ("Europe", "DE", "DAkkS", "Deutsche Akkreditierungsstelle"),
    ("Europe", "FR", "COFRAC", "Comité Français d'Accréditation"),
    ("Europe", "IT", "ACCREDIA", "Ente Italiano di Accreditamento"),
    ("Europe", "NL", "RvA", "Raad voor Accreditatie"),
    ("Europe", "ES", "ENAC", "Entidad Nacional de Acreditación"),
    ("Europe", "CH", "SAS", "Swiss Accreditation Service"),
    ("Europe", "SE", "SWEDAC", "Swedish Board for Accreditation and Conformity Assessment"),
    ("Europe", "BE", "BELAC", "Belgian Accreditation Structure"),
    ("Europe", "PL", "PCA", "Polskie Centrum Akredytacji"),
    ("Europe", "AT", "AA", "Akkreditierung Austria"),
    ("Europe", "DK", "DANAK", "Danish Accreditation Fund"),
    ("Europe", "NO", "NA", "Norsk Akkreditering"),
    ("Europe", "FI", "FINAS", "Finnish Accreditation Service"),
    ("Europe", "CZ", "CAI", "Czech Accreditation Institute"),
    ("Europe", "HU", "NAH", "National Accreditation Authority"),
    ("Europe", "PT", "IPAC", "Instituto Português de Acreditação"),
    ("Europe", "IE", "INAB", "Irish National Accreditation Board"),
    ("Europe", "GR", "ESYD", "Hellenic Accreditation System"),
    ("Europe", "TR", "TURKAK", "Turkish Accreditation Agency"),
    ("Europe", "RO", "RENAR", "Romanian Accreditation Association"),
    # North America
    ("North America", "US", "ANAB", "ANSI National Accreditation Board"),
    ("North America", "US", "IAS", "International Accreditation Service"),
    ("North America", "US", "A2LA", "American Association for Laboratory Accreditation"),
    ("North America", "US", "UAF", "United Accreditation Foundation"),
    ("North America", "CA", "SCC", "Standards Council of Canada"),
    ("North America", "MX", "EMA", "Entidad Mexicana de Acreditación"),
    # South America
    ("South America", "BR", "CGCRE", "General Coordination for Accreditation (INMETRO)"),
    ("South America", "AR", "OAA", "Organismo Argentino de Acreditación"),
    ("South America", "CL", "INAC", "Instituto Nacional de Normalización"),
    ("South America", "CO", "ONAC", "Organismo Nacional de Acreditación de Colombia"),
    ("South America", "PE", "INACAL", "Instituto Nacional de Calidad - DA"),
    # Middle East
    ("Middle East", "AE", "EIAC", "Emirates International Accreditation Centre"),
    ("Middle East", "SA", "SAAC", "Saudi Accreditation Center"),
    ("Middle East", "IL", "ISRAC", "Israel Laboratory Accreditation Authority"),
    # Africa
    ("Africa", "EG", "EGAC", "Egyptian Accreditation Council"),
    ("Africa", "ZA", "SANAS", "South African National Accreditation System"),
    ("Africa", "TN", "TUNAC", "Tunisian Accreditation Council"),
    ("Africa", "MA", "SEMAC", "Moroccan Accreditation Service"),
    ("Africa", "ZA", "SADCAS", "Southern African Development Community Accreditation Services"),
]

# 플랫폼 취급 15개 ISO 표준 (standard_masters와 동기)
ENTERPRISE_ISO_STANDARDS: List[Tuple[str, str]] = [
    ("ISO 9001:2015", "품질경영시스템"),
    ("ISO 9001:2026", "품질경영시스템"),
    ("ISO 14001:2015", "환경경영시스템"),
    ("ISO 14001:2026", "환경경영시스템"),
    ("ISO 45001:2018", "안전보건경영시스템"),
    ("ISO 50001:2018", "에너지경영시스템"),
    ("ISO/IEC 27001:2022", "정보보안경영시스템"),
    ("ISO/IEC 27701:2019", "개인정보보호경영시스템"),
    ("ISO 37001:2016", "부패방지경영시스템"),
    ("ISO 37301:2021", "준법경영시스템"),
    ("ISO 22301:2019", "사업연속성경영시스템"),
    ("ISO 22000:2018", "식품안전경영시스템"),
    ("ISO 13485:2016", "의료기기 품질경영시스템"),
    ("ISO/IEC 42001:2023", "인공지능경영시스템"),
    ("ISO 19443:2018", "원자력공급망 품질경영시스템"),
]


def ensure_accreditation_bodies(db: Session) -> int:
    """비어 있거나 누락된 AB를 UPSERT. 반환: 신규 생성 건수."""
    now = datetime.utcnow()
    created = 0
    for continent, country_code, code, name_en in ACCREDITATION_BODY_SEED:
        row = db.query(AccreditationBodies).filter(AccreditationBodies.code == code).first()
        if row:
            row.name = code
            row.name_en = name_en
            row.continent = continent
            row.country_code = country_code
            row.country = country_code
            row.is_active = True
            continue
        # code 컬럼이 아직 없거나 레거시 name만 있는 경우 name 매칭
        by_name = (
            db.query(AccreditationBodies)
            .filter(AccreditationBodies.name.in_([code, name_en]))
            .first()
        )
        if by_name:
            by_name.code = code
            by_name.name = code
            by_name.name_en = name_en
            by_name.continent = continent
            by_name.country_code = country_code
            by_name.country = country_code
            by_name.is_active = True
            continue
        db.add(
            AccreditationBodies(
                code=code,
                name=code,
                name_en=name_en,
                continent=continent,
                country_code=country_code,
                country=country_code,
                is_active=True,
                created_at=now,
            )
        )
        created += 1
    db.flush()
    return created
