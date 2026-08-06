"""인증 심사 계약(CertContract) API.

`app.models.cert_application.CertApplication`(기업의 인증 신청서)에 연결된
`CertContract`(계약서)를 다룬다. `Contract`/`AuditApplication`(심사원의 IAF 자격 신청 체인,
app.models.contract / app.models.auditor)과는 별개의 도메인이다.

CB(인증원) 단위 데이터 격리: cb_id가 CertApplication/CertContract에 직접 컬럼으로 존재하므로
current_user.cb_id로 직접 필터링한다 (platform_admin 제외).
"""
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.cert_application import CertApplication, CertContract, ContractStatus
from app.schemas.cert_application import CertContractCreate, CertContractResponse

router = APIRouter(prefix="/cert-contracts", tags=["Cert Contracts"])


def _require_cb_id(current_user: CurrentUser) -> int:
    """cb_id가 직접 컬럼인 리소스는 platform_admin이라도 소속 CB 없이는 생성/조회 기준을 정할 수 없다."""
    if current_user.cb_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="플랫폼 관리자는 특정 인증원(CB) 컨텍스트 없이는 이 리소스를 생성/조회할 수 없습니다.",
        )
    return current_user.cb_id


def _get_cert_application_or_404(db: Session, application_id: int, cb_id: int) -> CertApplication:
    application = (
        db.query(CertApplication)
        .filter(CertApplication.id == application_id, CertApplication.cb_id == cb_id)
        .first()
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"인증 신청서(application_id={application_id})를 찾을 수 없습니다.",
        )
    return application


def _get_cert_contract_or_404(db: Session, contract_id: int, cb_id: int) -> CertContract:
    contract = (
        db.query(CertContract)
        .filter(CertContract.id == contract_id, CertContract.cb_id == cb_id)
        .first()
    )
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"계약서(id={contract_id})를 찾을 수 없습니다.")
    return contract


@router.get("", response_model=List[CertContractResponse])
def list_contracts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> List[CertContract]:
    """계약서 목록을 조회합니다. 로그인한 인증원(CB) 소속 계약만 조회됩니다."""
    cb_id = _require_cb_id(current_user)
    return (
        db.query(CertContract)
        .filter(CertContract.cb_id == cb_id)
        .order_by(CertContract.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("", response_model=CertContractResponse, status_code=status.HTTP_201_CREATED)
def create_contract(
    contract_in: CertContractCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),  # CB 멀티테넌시 데이터 격리
) -> CertContract:
    """인증 심사 계약서 등록"""
    cb_id = _require_cb_id(current_user)

    # 신청서가 로그인한 인증원 소속인지 확인
    _get_cert_application_or_404(db, contract_in.application_id, cb_id)

    # 계약번호 중복 확인
    existing = (
        db.query(CertContract)
        .filter(CertContract.contract_no == contract_in.contract_no, CertContract.cb_id == cb_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 존재하는 계약번호입니다.")

    now = datetime.now()
    new_contract = CertContract(**contract_in.model_dump(), cb_id=cb_id, created_at=now, updated_at=now)
    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)
    return new_contract


@router.patch("/{contract_id}/sign", response_model=CertContractResponse)
def sign_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> CertContract:
    """계약 체결 확정 -> 심사원 배정 및 심사노트 생성 가능 상태 전환"""
    cb_id = _require_cb_id(current_user)
    contract = _get_cert_contract_or_404(db, contract_id, cb_id)

    contract.status = ContractStatus.SIGNED
    contract.updated_at = datetime.now()
    db.commit()
    db.refresh(contract)
    return contract
