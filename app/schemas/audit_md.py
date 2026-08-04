"""심사 신청건 MD(Man-Day) 산출 및 행정 가감 검토 API DTO."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseMdSaveRequest(BaseModel):
    """MD 계산기 결과 저장 요청 (md_save_base.php 대체)."""
    application_id: int
    base_md: float = Field(..., ge=0, description="계산기로 산출된 기본 MD")
    base_md_detail_json: Optional[Dict[str, Any]] = Field(default={}, description="산출 로직 JSON 스냅샷")


class MdReviewUpdateRequest(BaseModel):
    """행정 가감 검토 저장/승인 요청 (cb_application_review.php POST 대체)."""
    action: str = Field(..., description="save_md, under_review, approved, need_fix, rejected")
    add_pct: int = Field(default=0, ge=0, le=30)
    subtract_pct: int = Field(default=0, ge=0, le=30)
    calculation_note: Optional[str] = None
    memo: Optional[str] = None


class MdReviewResponse(BaseModel):
    id: int
    application_id: int
    base_md: float
    add_pct: int
    subtract_pct: int
    add_md: float
    subtract_md: float
    final_md: float
    calculation_note: Optional[str]
    base_md_detail_json: Optional[Dict[str, Any]]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
