# app/api/v1/endpoints/mappings.py
"""KSIC/전공 -> IAF 매핑 조회 API.

주의(CB 데이터 격리): 이 라우터가 다루는 KsicCode/IafCode/Major/매핑 테이블은
특정 인증원(CB)에 소속되지 않는 전역 공통 마스터/참조 데이터이다. 따라서 cb_id 기반
격리 필터는 적용하지 않으며, 로그인한 사용자라면 (CB 소속 여부와 무관하게) 조회 가능하다.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user
from app.models.master_data import IafCode, KsicCode, Major

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
def lookup_ksic_mapping(
    ksic_code: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    KSIC 업종 코드를 바탕으로 IAF 코드 및 심사 복잡도를 자동 조회합니다.
    (5자리 -> 4자리 -> 3자리 순으로 Fallback 조회를 수행합니다.)
    """
    clean_code = "".join(filter(str.isdigit, ksic_code))
    if len(clean_code) < 2:
        raise HTTPException(status_code=400, detail="KSIC 코드는 최소 2자리 이상이어야 합니다.")

    ksic_obj = None
    mapping = None
    # 5자리, 4자리, 3자리 순서로 매핑 조회 (기존 client_signup.php 백엔드 로직 충실 계승)
    for length in range(min(5, len(clean_code)), 2, -1):
        sub_code = clean_code[:length]
        ksic_obj = db.query(KsicCode).filter(KsicCode.code == sub_code).first()
        if ksic_obj and ksic_obj.iaf_mappings:
            mapping = ksic_obj.iaf_mappings[0]
            break

    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"KSIC 코드 '{ksic_code}'에 매핑된 IAF 코드를 찾을 수 없습니다.",
        )

    iaf_obj = mapping.iaf
    return KsicIafResponse(
        ok=True,
        ksic_code=ksic_obj.code,
        ksic_name=ksic_obj.name_ko,
        iaf_code=iaf_obj.code,
        iaf_name_ko=iaf_obj.name_ko,
        qms_complexity=mapping.qms_complexity,
        ems_complexity=mapping.ems_complexity,
        ohsms_complexity=mapping.ohsms_complexity,
    )


@router.get("/major/{major_name}", response_model=MajorIafResponse)
def recommend_iaf_by_major(
    major_name: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    심사원의 전공학과명을 검색하여 자격인증기준(부속서 2)에 따라
    부여 가능한 추천 IAF 코드 목록 및 단서조항(추가 경력 필요년수 등)을 반환합니다.
    """
    clean_major = major_name.strip()
    majors = db.query(Major).filter(Major.name.like(f"%{clean_major}%")).all()

    recommendations: List[MajorIafRecommendation] = []
    for major in majors:
        for mapping in major.iaf_mappings:
            recommendations.append(
                MajorIafRecommendation(
                    iaf_code=mapping.iaf.code,
                    degree_level=mapping.degree_level,
                    is_mandatory=mapping.is_mandatory,
                    extra_exp_years=mapping.extra_exp_years,
                    requires_committee=mapping.requires_committee,
                    notes=mapping.notes,
                )
            )

    if not recommendations:
        raise HTTPException(
            status_code=404,
            detail=f"전공명 '{major_name}'에 해당하는 추천 IAF 코드가 없습니다.",
        )

    return MajorIafResponse(ok=True, major_name=clean_major, recommendations=recommendations)
