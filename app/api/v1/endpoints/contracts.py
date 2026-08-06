"""심사 계약(Contract) CRUD API.

master_data 기반 신규 심사 신청 모델(AuditApplication)에 정규화 연결된
`app.models.contract.Contract`(audit_contracts 테이블)를 다룬다.

CB(인증원) 단위 데이터 격리: Contract -> AuditApplication.auditor_id -> AuditorCbMemberships.cb_id
경로로 소속을 판단하여, 로그인한 인증원 소속 심사원의 신청건에 딸린 계약만 접근을 허용한다
(platform_admin 제외).
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.cb_scope import assert_auditor_in_cb_scope, filter_by_cb_auditor_scope
from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.auditor import AuditApplication
from app.models.contract import Contract
from app.schemas.contract import (
    ContractCreate,
    ContractResponse,
    ContractSettlementRequest,
    ContractSettlementResult,
    ContractUpdate,
)
from app.services.settlement_calculator import calculate_contract_settlement

router = APIRouter(prefix="/contracts", tags=["Contracts"])


def _get_application_or_404(db: Session, application_id: int) -> AuditApplication:
    application = db.get(AuditApplication, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"심사 신청서(application_id={application_id})를 찾을 수 없습니다.",
        )
    return application


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"계약(id={contract_id})을 찾을 수 없습니다.")
    return contract


def _assert_contract_in_cb_scope(db: Session, contract: Contract, current_user: CurrentUser) -> None:
    """계약이 연결된 신청건의 심사원이 current_user 소속 CB에 속하는지 검증한다."""
    application = contract.application or _get_application_or_404(db, contract.application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)


def _simulate_contract_settlement(contract: Optional[Contract]) -> Optional[ContractSettlementResult]:
    """계약의 agreed_amount / high_value_threshold / high_value_deduction_rate를 이용해
    정산 시뮬레이션을 수행한다. agreed_amount가 없으면 계산하지 않는다."""
    if contract is None or contract.agreed_amount is None:
        return None
    result = calculate_contract_settlement(
        fee_calculation_type="PERCENTAGE",
        agreed_amount=float(contract.agreed_amount),
        high_value_threshold=float(contract.high_value_threshold or 0.0),
        high_value_deduction_rate=float(contract.high_value_deduction_rate or 0.0),
    )
    return ContractSettlementResult(**result)


@router.post("/calculate", response_model=ContractSettlementResult)
def calculate_settlement(
    payload: ContractSettlementRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> ContractSettlementResult:
    """계약금/심사원 정산액 시뮬레이션.

    `contract_id`를 지정하면 해당 계약에 저장된 agreed_amount / high_value_threshold /
    high_value_deduction_rate를 기본값으로 사용하고, 요청 본문에 명시된 값이 있으면 그 값으로 덮어써서 계산한다.
    `contract_id` 없이 순수 입력값만으로도(What-if) 시뮬레이션할 수 있다.
    `contract_id`로 기존 계약을 참조하는 경우, 타 인증원 소속 계약은 조회할 수 없다.
    """
    base_contract: Optional[Contract] = None
    if payload.contract_id is not None:
        base_contract = _get_contract_or_404(db, payload.contract_id)
        _assert_contract_in_cb_scope(db, base_contract, current_user)

    agreed_amount = payload.agreed_amount
    if agreed_amount is None:
        agreed_amount = float(base_contract.agreed_amount) if base_contract and base_contract.agreed_amount is not None else None
    if agreed_amount is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agreed_amount를 입력하거나 조회 가능한 contract_id를 지정해야 합니다.")

    high_value_threshold = payload.high_value_threshold
    if high_value_threshold is None:
        high_value_threshold = float(base_contract.high_value_threshold or 0.0) if base_contract else 0.0

    high_value_deduction_rate = payload.high_value_deduction_rate
    if high_value_deduction_rate is None:
        high_value_deduction_rate = float(base_contract.high_value_deduction_rate or 0.0) if base_contract else 0.0

    result = calculate_contract_settlement(
        fee_calculation_type=payload.fee_calculation_type,
        agreed_amount=agreed_amount,
        travel_expense=payload.travel_expense,
        fee_ratio=payload.fee_ratio,
        flat_fee=payload.flat_fee,
        high_value_threshold=high_value_threshold,
        high_value_deduction_rate=high_value_deduction_rate,
    )
    return ContractSettlementResult(**result)


@router.get("", response_model=List[ContractResponse])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    application_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> List[Contract]:
    """계약 목록을 조회합니다 (application_id로 필터링 가능).
    로그인한 인증원(CB) 소속 심사원의 신청건에 딸린 계약만 조회됩니다 (platform_admin 제외)."""
    query = db.query(Contract).join(AuditApplication, Contract.application_id == AuditApplication.id)
    query = filter_by_cb_auditor_scope(query, db, current_user, AuditApplication.auditor_id)
    if application_id is not None:
        query = query.filter(Contract.application_id == application_id)
    return query.order_by(Contract.id.desc()).offset(skip).limit(limit).all()


@router.get("/{contract_id}", response_model=ContractResponse)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> Contract:
    """단일 계약을 조회합니다. 타 인증원 소속 계약은 조회할 수 없습니다."""
    contract = _get_contract_or_404(db, contract_id)
    _assert_contract_in_cb_scope(db, contract, current_user)
    return contract


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract(
    payload: ContractCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> ContractResponse:
    """신규 계약을 생성합니다. agreed_amount가 있으면 정산 시뮬레이션 결과를 함께 반환합니다.
    application_id가 가리키는 신청건의 심사원이 타 인증원 소속이면 생성할 수 없습니다."""
    application = _get_application_or_404(db, payload.application_id)
    assert_auditor_in_cb_scope(db, application.auditor_id, current_user)

    now = datetime.now()
    contract = Contract(**payload.model_dump(), created_at=now, updated_at=now)
    db.add(contract)
    db.commit()
    db.refresh(contract)

    response = ContractResponse.model_validate(contract)
    response.settlement = _simulate_contract_settlement(contract)
    return response


@router.patch("/{contract_id}", response_model=ContractResponse)
def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> ContractResponse:
    """계약 정보를 부분 수정합니다. agreed_amount가 있으면 정산 시뮬레이션 결과를 함께 반환합니다.
    타 인증원 소속 계약은 수정할 수 없습니다."""
    contract = _get_contract_or_404(db, contract_id)
    _assert_contract_in_cb_scope(db, contract, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "application_id" in update_data:
        new_application = _get_application_or_404(db, update_data["application_id"])
        assert_auditor_in_cb_scope(db, new_application.auditor_id, current_user)

    for field, value in update_data.items():
        setattr(contract, field, value)
    contract.updated_at = datetime.now()

    db.commit()
    db.refresh(contract)

    response = ContractResponse.model_validate(contract)
    response.settlement = _simulate_contract_settlement(contract)
    return response


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> None:
    """계약을 삭제합니다. (연결된 배정 레코드는 contract_id가 NULL로 설정됩니다.)
    타 인증원 소속 계약은 삭제할 수 없습니다."""
    contract = _get_contract_or_404(db, contract_id)
    _assert_contract_in_cb_scope(db, contract, current_user)
    db.delete(contract)
    db.commit()
