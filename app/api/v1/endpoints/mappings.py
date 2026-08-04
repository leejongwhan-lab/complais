# app/api/v1/endpoints/mappings.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.mapping import KsicIafMapping, MajorIafMapping

router = APIRouter(prefix="/mappings", tags=["Mappings"])


# --- Response Schemas ---
class KsicIafResponse(BaseModel):
    ok: bool = True
    ksic_code: str
    ksic_name: Optional[str]
    iaf_code: str
    iaf_name_ko: str
    qms_complexity: Optional[str]
    ems_complexity: Optional[str]
    ohsms_complexity: Optional[str]

    class Config:
        from_attributes = True


class MajorIafRecommendation(BaseModel):
    iaf_code: str
    degree_level: str
    is_mandatory: bool
    extra_exp_years: int
    requires_committee: bool
    notes: Optional[str]

    class Config:
        from_attributes = True


class MajorIafResponse(BaseModel):
    ok: bool = True
    major_name: str
    recommendations: List[MajorIafRecommendation]


# --- Endpoints ---

@router.get("/ksic/{ksic_code}", response_model=KsicIafResponse)
def lookup_ksic_mapping(ksic_code: str, db: Session = Depends(get_db)):
    """
    KSIC 업종 코드를 바탕으로 IAF 코드 및 심사 복잡도를 자동 조회합니다.
    (5자리 -> 4자리 -> 3자리 순으로 Fallback 조회를 수행합니다.)
    """
    clean_code = "".join(filter(str.isdigit, ksic_code))
    if len(clean_code) < 2:
        raise HTTPException(status_code=400, detail="KSIC 코드는 최소 2자리 이상이어야 합니다.")

    row = None
    # 5자리, 4자리, 3자리 순서로 매핑 조회 (기존 client_signup.php 백엔드 로직 충실 계승)
    for length in range(min(5, len(clean_code)), 2, -1):
        sub_code = clean_code[:length]
        row = db.query(KsicIafMapping).filter(KsicIafMapping.ksic_code == sub_code).first()
        if row:
            break

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"KSIC 코드 '{ksic_code}'에 매핑된 IAF 코드를 찾을 수 없습니다.",
        )

    # ORM의 description 컬럼을 API 응답의 ksic_name으로 매핑
    return KsicIafResponse(
        ok=True,
        ksic_code=row.ksic_code,
        ksic_name=row.description,
        iaf_code=row.iaf_code,
        iaf_name_ko=row.iaf_name_ko,
        qms_complexity=row.qms_complexity,
        ems_complexity=row.ems_complexity,
        ohsms_complexity=row.ohsms_complexity,
    )


@router.get("/major/{major_name}", response_model=MajorIafResponse)
def recommend_iaf_by_major(major_name: str, db: Session = Depends(get_db)):
    """
    심사원의 전공학과명을 검색하여 자격인증기준(부속서 2)에 따라
    부여 가능한 추천 IAF 코드 목록 및 단서조항(추가 경력 필요년수 등)을 반환합니다.
    """
    clean_major = major_name.strip()
    results = (
        db.query(MajorIafMapping)
        .filter(MajorIafMapping.major_name.like(f"%{clean_major}%"))
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"전공명 '{major_name}'에 해당하는 추천 IAF 코드가 없습니다.",
        )

    return {
        "ok": True,
        "major_name": clean_major,
        "recommendations": results,
    }
