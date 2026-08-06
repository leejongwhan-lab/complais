"""CB Admin Dashboard 전용 DTO.

MD 검토는 `app.schemas.audit_md` 의 MdReviewUpdateRequest / MdReviewResponse 를 사용한다.
여기에는 승인 전용 스키마와, 단건 assignment 스키마를 감싸는 배정 래퍼만 둔다.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.contract import AuditAssignmentCreate


_STATUS_UI = {
    "SUBMITTED": "submitted",
    "REVIEWING": "reviewed",
    "PROPOSED": "approved",
    "CONTRACTED": "assigned",
}


def _standards_as_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    text = str(raw).strip()
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]


class ApplicationResponse(BaseModel):
    """초안 스펙 — 인증신청 조회 (기업명 포함)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    company_name: Optional[str] = None
    standards_json: List[str] = Field(default_factory=list)
    status: str
    created_at: datetime

    @classmethod
    def from_enterprise(
        cls,
        eapp,
        *,
        company_name: Optional[str] = None,
        ui_status: Optional[str] = None,
    ) -> "ApplicationResponse":
        status = ui_status or _STATUS_UI.get(str(getattr(eapp, "status", "") or "").upper(), str(eapp.status or "").lower())
        return cls(
            id=int(eapp.application_id),
            company_id=int(eapp.enterprise_id),
            company_name=company_name,
            standards_json=_standards_as_list(
                getattr(eapp, "standards_json", None) or eapp.applied_standards
            ),
            status=status,
            created_at=eapp.created_at,
        )


class CbAdminApplicationListItem(BaseModel):
    """CB Admin 대시보드 신청 목록 행."""

    id: int
    company_name: Optional[str] = None
    standards_json: Optional[str] = None
    status: str = Field(description="submitted|reviewed|approved|assigned (대시보드용 소문자)")
    created_at: Optional[datetime] = None
    audit_type: Optional[str] = None
    final_md: Optional[float] = None
    cb_id: Optional[int] = None


class ApplicationDetailResponse(BaseModel):
    """CB Admin 신청서 상세 — 검토/승인 화면용."""

    id: int
    company_name: Optional[str] = None
    enterprise_id: Optional[int] = None
    cb_id: Optional[int] = None
    audit_type: Optional[str] = None
    status: str
    applied_standards: Optional[List[str]] = None
    standards_json: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_scope_code: Optional[str] = None
    active_employee_count: Optional[int] = None
    complexity_level: Optional[str] = None
    base_stage1_md: Optional[float] = None
    base_stage2_md: Optional[float] = None
    base_surveillance_md: Optional[float] = None
    base_recertification_md: Optional[float] = None
    base_md: Optional[float] = None
    cb_adjustment_ratio: Optional[float] = None
    cb_adjustment_reason: Optional[str] = None
    final_audit_md: Optional[float] = None
    contract_id: Optional[int] = None
    contract_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorScopeResponse(BaseModel):
    """배정 가능한 심사원 + 서약서/자격 요약."""

    auditor_id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    membership_status: Optional[str] = None
    approved_grade: Optional[str] = None
    grade_at_cb: Optional[str] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None
    conduct_sign_valid: bool = False
    conduct_expires_at: Optional[date] = None
    is_assignable: bool = False


class ContractSummaryResponse(BaseModel):
    """CB Admin 계약 목록 요약 (Draft/확정)."""

    id: int
    contract_no: Optional[str] = None
    application_id: int
    company_name: Optional[str] = None
    audit_type: Optional[str] = None
    standards: Optional[str] = None
    status: str
    total_md: Optional[float] = None
    agreed_amount: Optional[float] = None
    scope_kr: Optional[str] = None
    audit_period_start: Optional[date] = None
    audit_period_end: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ContractCreate(BaseModel):
    """CB Admin UI용 계약 생성/수정 요청 DTO.

    주의: `app.schemas.contract.ContractCreate` (정규화 CRUD) 와 별개이다.
    path `/applications/{app_id}/contract` 사용 시 application_id 는 생략 가능.
    """

    application_id: int = Field(0, description="신청 ID (path 사용 시 생략 가능)")
    total_md: float = Field(..., ge=0.5, description="최종 결정 M/D")
    total_amount: int = Field(..., ge=0, description="총 계약 금액")
    audit_standards: List[str] = Field(default_factory=list, description="대상 ISO 표준 목록")
    contract_date: Optional[datetime] = None
    audit_type: str = Field("INITIAL", description="INITIAL/SURVEILLANCE/RECERT 등")

    def to_entity_kwargs(self) -> dict:
        """audit_contracts 컬럼명으로 변환."""
        standards = ", ".join(str(s).strip() for s in self.audit_standards if str(s).strip())
        return {
            "application_id": self.application_id,
            "audit_type": self.audit_type,
            "standards": standards or None,
            "total_md": float(self.total_md),
            "agreed_amount": self.total_amount,
            "status": "DRAFT",
            "signed_at": self.contract_date,
        }


class ContractResponse(BaseModel):
    """CB Admin UI 매핑용 계약 응답 DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    company_name: str = ""
    total_md: float = 0.0
    total_amount: int = 0
    status: str = "draft"
    contract_date: Optional[datetime] = None
    created_at: datetime
    audit_standards: List[str] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, contract_entity, company_name: Optional[str] = None) -> "ContractResponse":
        """기존 DB 모델(Contract)을 UI용 ContractResponse로 매핑."""
        standards_raw = getattr(contract_entity, "standards", None) or ""
        if isinstance(standards_raw, list):
            standards = [str(x) for x in standards_raw]
        else:
            standards = [p.strip() for p in str(standards_raw).split(",") if p.strip()]

        amount = getattr(contract_entity, "agreed_amount", None)
        total_amount = int(amount) if amount is not None else 0
        md = getattr(contract_entity, "total_md", None)
        name = company_name
        if not name:
            app = getattr(contract_entity, "application", None)
            name = getattr(app, "company_name", None) if app is not None else None

        return cls(
            id=int(contract_entity.id),
            application_id=int(contract_entity.application_id),
            company_name=name or "",
            total_md=float(md or 0),
            total_amount=total_amount,
            status=cls._map_status(str(getattr(contract_entity, "status", "") or "")),
            contract_date=getattr(contract_entity, "signed_at", None)
            or getattr(contract_entity, "contract_date", None),
            created_at=contract_entity.created_at,
            audit_standards=standards,
        )

    @staticmethod
    def _map_status(db_status: str) -> str:
        mapping = {
            "DRAFT": "draft",
            "PROPOSED": "review",
            "SENT": "review",
            "APPROVED": "approved",
            "SCHEDULED": "approved",
            "SIGNED": "signed",
            "CONTRACTED": "signed",
            "CANCELLED": "cancelled",
        }
        return mapping.get(db_status.upper(), (db_status or "draft").lower())


class ApplicationApproveRequest(BaseModel):
    """신청 승인 전용 — 메모 / CB 범위 검증 옵션 분리."""

    memo: Optional[str] = Field(None, description="승인 처리 메모")
    skip_scope_check: bool = Field(
        False,
        description="True 이면 CB 인정범위(표준) 검증을 건너뜀 (관리자/테스트용)",
    )
    force_new_contract: bool = Field(
        False,
        description="True 이면 기존 DRAFT 계약이 있어도 새 DRAFT 계약을 생성",
    )


class AuditorAssignmentRequest(BaseModel):
    """레거시형 CB 배정 래퍼 — 팀장 1 + 팀원 N + 기간/공수를 한 번에 처리.

    단건 CRUD는 `AuditAssignmentCreate` / `AuditAssignmentResponse` 를 그대로 유지하고,
    본 스키마는 배치 배정 API(`/cb-admin/.../assign-auditors`) 입력용이다.
    """

    lead_auditor_id: int = Field(..., description="심사팀장 Auditor ID")
    member_auditor_ids: List[int] = Field(default_factory=list, description="팀원 Auditor ID 목록")
    audit_start: date = Field(..., description="심사 시작일")
    audit_end: date = Field(..., description="심사 종료일")
    audit_type: str = Field("initial", description="initial, surveillance, recertification 등")
    stage: str = Field("combined", description="stage1, stage2, combined")
    total_md: float = Field(2.0, ge=0.5)
    surveillance_cycle: int = Field(12, description="6 또는 12개월")
    scope_kr: Optional[str] = Field(None, description="국문 인증범위")
    standard: Optional[str] = Field(
        None,
        description="배정 사전 자격 검증용 표준 코드 (지정 시 각 심사원에 동일 적용)",
    )

    def to_assignment_creates(
        self,
        application_id: int,
        contract_id: Optional[int] = None,
    ) -> List[AuditAssignmentCreate]:
        """단건 `AuditAssignmentCreate` 목록으로 펼친다 (기존 assignments API 스키마 재사용)."""
        note = f"stage={self.stage}; cycle={self.surveillance_cycle}; type={self.audit_type}"
        rows: List[AuditAssignmentCreate] = [
            AuditAssignmentCreate(
                application_id=application_id,
                auditor_id=self.lead_auditor_id,
                contract_id=contract_id,
                role="LEAD",
                status="ASSIGNED",
                note=note,
                standard=self.standard,
            )
        ]
        for member_id in self.member_auditor_ids:
            rows.append(
                AuditAssignmentCreate(
                    application_id=application_id,
                    auditor_id=member_id,
                    contract_id=contract_id,
                    role="MEMBER",
                    status="ASSIGNED",
                    note=note,
                    standard=self.standard,
                )
            )
        return rows
