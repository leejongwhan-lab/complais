"""CB Admin Dashboard 조회/오케스트레이션 서비스."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.auditor import AuditorConductSigns
from app.models.company import Companies
from app.models.contract import Contract
from app.models.enterprise_audit_application import EnterpriseAuditApplication
from app.schemas.cb_admin import (
    ApplicationDetailResponse,
    AuditorScopeResponse,
    ContractCreate,
    ContractResponse,
    ContractSummaryResponse,
)


_STATUS_UI = {
    "SUBMITTED": "submitted",
    "REVIEWING": "reviewed",
    "PROPOSED": "approved",
    "CONTRACTED": "assigned",
}


def _standards_list(raw) -> Optional[List[str]]:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(x) for x in raw]
    text = str(raw).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            import json

            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            pass
    return [p.strip() for p in text.split(",") if p.strip()]


def _standards_label(raw) -> str:
    items = _standards_list(raw) or []
    return ", ".join(items)


def _base_md_of(eapp: EnterpriseAuditApplication) -> float:
    t = str(eapp.audit_type or "").upper()
    if t.startswith("SURV"):
        return float(eapp.base_surveillance_md or 0)
    if "RECERT" in t or "RENEW" in t:
        return float(eapp.base_recertification_md or 0)
    return float(eapp.base_stage1_md or 0) + float(eapp.base_stage2_md or 0)


def _ui_status(eapp: EnterpriseAuditApplication, contract: Optional[Contract]) -> str:
    if contract is not None and str(contract.status or "").upper() in {"SCHEDULED", "SIGNED", "SENT"}:
        return "assigned"
    return _STATUS_UI.get(str(eapp.status or "").upper(), str(eapp.status or "").lower())


def _latest_contract(db: Session, app_id: int) -> Optional[Contract]:
    return (
        db.query(Contract)
        .filter(Contract.application_id == app_id)
        .order_by(Contract.id.desc())
        .first()
    )


def _conduct_valid(db: Session, auditor_id: int, today: date) -> tuple[bool, Optional[date]]:
    row = (
        db.query(AuditorConductSigns)
        .filter(
            AuditorConductSigns.auditor_id == auditor_id,
            AuditorConductSigns.is_valid.is_(True),
        )
        .order_by(AuditorConductSigns.signed_at.desc())
        .first()
    )
    if row is None:
        return False, None
    expires = row.expires_at
    if expires is not None and expires < today:
        return False, expires
    return True, expires


class CBAdminService:
    """CB Admin 전용 조회 로직."""

    @staticmethod
    def get_application_detail(
        db: Session,
        *,
        app_id: int,
        cb_id: Optional[int],
        is_platform_admin: bool = False,
    ) -> Optional[ApplicationDetailResponse]:
        row = (
            db.query(EnterpriseAuditApplication, Companies.name)
            .outerjoin(Companies, Companies.id == EnterpriseAuditApplication.enterprise_id)
            .filter(EnterpriseAuditApplication.application_id == app_id)
            .first()
        )
        if row is None:
            return None
        eapp, company_name = row
        if not is_platform_admin:
            if cb_id is None or int(eapp.cb_id) != int(cb_id):
                return None

        contract = _latest_contract(db, app_id)
        standards = _standards_list(eapp.applied_standards)
        return ApplicationDetailResponse(
            id=eapp.application_id,
            company_name=company_name,
            enterprise_id=eapp.enterprise_id,
            cb_id=eapp.cb_id,
            audit_type=eapp.audit_type,
            status=_ui_status(eapp, contract),
            applied_standards=standards,
            standards_json=_standards_label(eapp.applied_standards),
            ksic_code=eapp.ksic_code,
            iaf_scope_code=eapp.iaf_scope_code,
            active_employee_count=eapp.active_employee_count,
            complexity_level=eapp.complexity_level,
            base_stage1_md=float(eapp.base_stage1_md) if eapp.base_stage1_md is not None else None,
            base_stage2_md=float(eapp.base_stage2_md) if eapp.base_stage2_md is not None else None,
            base_surveillance_md=(
                float(eapp.base_surveillance_md) if eapp.base_surveillance_md is not None else None
            ),
            base_recertification_md=(
                float(eapp.base_recertification_md)
                if eapp.base_recertification_md is not None
                else None
            ),
            base_md=_base_md_of(eapp),
            cb_adjustment_ratio=(
                float(eapp.cb_adjustment_ratio) if eapp.cb_adjustment_ratio is not None else None
            ),
            cb_adjustment_reason=eapp.cb_adjustment_reason,
            final_audit_md=float(eapp.final_audit_md) if eapp.final_audit_md is not None else None,
            contract_id=contract.id if contract else None,
            contract_status=contract.status if contract else None,
            created_at=eapp.created_at,
            updated_at=eapp.updated_at,
        )

    @staticmethod
    def list_cb_auditors(
        db: Session,
        *,
        cb_id: Optional[int],
        status: Optional[str] = "approved",
    ) -> List[AuditorScopeResponse]:
        if not cb_id:
            return []

        # ORM 전체 로드는 DB 스키마 드리프트(누락 컬럼)에 취약하므로 필요 컬럼만 조회
        from sqlalchemy import text

        params = {"cb_id": int(cb_id)}
        status_sql = ""
        if status:
            st = status.strip().lower()
            if st == "pending":
                status_sql = "AND m.status IN ('requested','under_review','pending')"
            else:
                status_sql = "AND m.status = :status"
                params["status"] = st

        rows = db.execute(
            text(
                f"""
                SELECT
                  a.id AS auditor_id,
                  a.name AS name,
                  a.email AS email,
                  a.phone AS phone,
                  m.status AS membership_status,
                  m.approved_grade AS approved_grade,
                  m.grade_at_cb AS grade_at_cb,
                  m.apply_grade AS apply_grade,
                  m.cert_standards AS cert_standards,
                  m.approved_iaf_codes AS approved_iaf_codes
                FROM auditors a
                INNER JOIN auditor_cb_memberships m
                  ON m.auditor_id = a.id AND m.cb_id = :cb_id
                WHERE 1=1
                  {status_sql}
                ORDER BY m.id DESC
                LIMIT 200
                """
            ),
            params,
        ).mappings().all()

        today = date.today()
        items: List[AuditorScopeResponse] = []
        for row in rows:
            valid, expires = _conduct_valid(db, int(row["auditor_id"]), today)
            grade = row["approved_grade"] or row["grade_at_cb"] or row["apply_grade"]
            membership_status = row["membership_status"]
            items.append(
                AuditorScopeResponse(
                    auditor_id=int(row["auditor_id"]),
                    name=row["name"] or "",
                    email=row["email"],
                    phone=row["phone"],
                    membership_status=membership_status,
                    approved_grade=grade,
                    grade_at_cb=row["grade_at_cb"],
                    cert_standards=row["cert_standards"],
                    approved_iaf_codes=row["approved_iaf_codes"],
                    conduct_sign_valid=valid,
                    conduct_expires_at=expires,
                    is_assignable=(str(membership_status or "").lower() == "approved" and valid),
                )
            )
        return items

    @staticmethod
    def list_contracts(
        db: Session,
        *,
        cb_id: Optional[int],
        is_platform_admin: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ContractResponse]:
        """해당 CB 기업신청에 연결된 audit_contracts → UI ContractResponse."""
        q = (
            db.query(Contract, EnterpriseAuditApplication, Companies.name)
            .outerjoin(
                EnterpriseAuditApplication,
                EnterpriseAuditApplication.application_id == Contract.application_id,
            )
            .outerjoin(Companies, Companies.id == EnterpriseAuditApplication.enterprise_id)
        )
        if not is_platform_admin:
            if not cb_id:
                return []
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)
        elif cb_id:
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)

        rows = (
            q.order_by(Contract.id.desc())
            .offset(max(skip, 0))
            .limit(min(max(limit, 1), 200))
            .all()
        )
        return [
            ContractResponse.from_entity(contract, company_name=company_name)
            for contract, _eapp, company_name in rows
        ]

    @staticmethod
    def list_contract_summaries(
        db: Session,
        *,
        cb_id: Optional[int],
        is_platform_admin: bool = False,
    ) -> List[ContractSummaryResponse]:
        """상세 요약(기간/표준 문자열 포함) — 내부/확장용."""
        q = (
            db.query(Contract, EnterpriseAuditApplication, Companies.name)
            .outerjoin(
                EnterpriseAuditApplication,
                EnterpriseAuditApplication.application_id == Contract.application_id,
            )
            .outerjoin(Companies, Companies.id == EnterpriseAuditApplication.enterprise_id)
        )
        if not is_platform_admin:
            if not cb_id:
                return []
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)
        elif cb_id:
            q = q.filter(EnterpriseAuditApplication.cb_id == cb_id)

        rows = q.order_by(Contract.id.desc()).limit(200).all()
        items: List[ContractSummaryResponse] = []
        for contract, eapp, company_name in rows:
            items.append(
                ContractSummaryResponse(
                    id=contract.id,
                    contract_no=contract.contract_no,
                    application_id=contract.application_id,
                    company_name=company_name,
                    audit_type=contract.audit_type or (eapp.audit_type if eapp else None),
                    standards=contract.standards
                    or (_standards_label(eapp.applied_standards) if eapp else None),
                    status=str(contract.status or "DRAFT"),
                    total_md=float(contract.total_md) if contract.total_md is not None else None,
                    agreed_amount=(
                        float(contract.agreed_amount) if contract.agreed_amount is not None else None
                    ),
                    scope_kr=contract.scope_kr,
                    audit_period_start=contract.audit_period_start,
                    audit_period_end=contract.audit_period_end,
                    created_at=contract.created_at,
                    updated_at=contract.updated_at,
                )
            )
        return items

    @staticmethod
    def create_contract(
        db: Session,
        *,
        payload: ContractCreate,
        cb_id: Optional[int],
        is_platform_admin: bool = False,
        app_id: Optional[int] = None,
    ) -> ContractResponse:
        """UI ContractCreate → audit_contracts Draft 생성.

        app_id 가 주어지면 path 의 신청 ID를 우선한다.
        """
        application_id = int(app_id if app_id is not None else payload.application_id)
        eapp = (
            db.query(EnterpriseAuditApplication)
            .filter(EnterpriseAuditApplication.application_id == application_id)
            .first()
        )
        if eapp is None:
            raise ValueError("Application not found")
        if not is_platform_admin and (not cb_id or int(eapp.cb_id) != int(cb_id)):
            raise PermissionError("해당 CB 신청건에 접근할 수 없습니다.")

        # body application_id 와 path 불일치 방지
        payload = payload.model_copy(update={"application_id": application_id})

        now = datetime.utcnow()
        kwargs = payload.to_entity_kwargs()
        kwargs["application_id"] = application_id
        kwargs["status"] = "DRAFT"
        if not kwargs.get("audit_type") and eapp.audit_type:
            kwargs["audit_type"] = eapp.audit_type
        if not kwargs.get("standards") and eapp.applied_standards:
            standards = eapp.applied_standards
            kwargs["standards"] = (
                ", ".join(standards) if isinstance(standards, list) else str(standards)
            )
        if not kwargs.get("audit_type"):
            kwargs["audit_type"] = "INITIAL"

        contract = Contract(
            **kwargs,
            created_at=now,
            updated_at=now,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        company_name = (
            db.query(Companies.name)
            .filter(Companies.id == eapp.enterprise_id)
            .scalar()
        )
        return ContractResponse.from_entity(contract, company_name=company_name)
