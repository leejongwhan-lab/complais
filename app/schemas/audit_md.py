"""심사 신청건 MD(Man-Day) 산출 및 행정 가감 검토 API DTO."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class BaseMdSaveRequest(BaseModel):
    """MD 계산기 결과 저장 요청 (md_save_base.php 대체)."""

    application_id: int
    base_md: float = Field(..., ge=0, description="계산기로 산출된 기본 MD")
    base_md_detail_json: Optional[Dict[str, Any]] = Field(default={}, description="산출 로직 JSON 스냅샷")


class MdReviewUpdateRequest(BaseModel):
    """행정 가감 검토 저장/승인 요청 (cb_application_review.php POST 대체).

    레거시/프론트 호환:
    - plus_pct → add_pct
    - minus_pct → subtract_pct
    """

    model_config = ConfigDict(populate_by_name=True)

    action: str = Field(
        default="save_md",
        description="save_md, under_review, approved, need_fix, rejected",
    )
    add_pct: int = Field(
        default=0,
        ge=0,
        le=30,
        validation_alias=AliasChoices("add_pct", "plus_pct"),
        description="가산 비율 (%) — alias: plus_pct",
    )
    subtract_pct: int = Field(
        default=0,
        ge=0,
        le=30,
        validation_alias=AliasChoices("subtract_pct", "minus_pct"),
        description="감산 비율 (%) — alias: minus_pct",
    )
    calculation_note: Optional[str] = Field(None, description="가감 사유 및 인용 문구")
    memo: Optional[str] = Field(None, description="검토/승인 메모")


class MdReviewResponse(BaseModel):
    """MD 검토 응답. 필드명(add_pct, subtract_pct, updated_at) 유지 + reviewed_at 노출."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    application_id: int
    base_md: float
    add_pct: int
    subtract_pct: int
    add_md: float
    subtract_md: float
    final_md: float
    calculation_note: Optional[str] = None
    base_md_detail_json: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="최종 검토 시각 (레거시 reviewed_at 호환)",
    )
