"""심사 배정(AuditAssignment) CRUD API.

master_data 기반 신규 심사 신청 모델(AuditApplication) 및 심사원(Auditor)에
정규화 연결된 `app.models.contract.AuditAssignment`(audit_application_assignments 테이블)를 다룬다.

CB(인증원) 단위 데이터 격리: AuditAssignment.auditor_id -> AuditorCbMemberships.cb_id 경로로
소속을 판단하여, 로그인한 인증원 소속 심사원의 배정만 접근을 허용한다 (platform_admin 제외).

배정 사전 자격 검증: standard가 지정된 배정 요청은 `_validate_auditor_qualification`으로
해당 CB에서 그 표준에 대해 승인(active)된 자격범위(AuditorScopeGrants)를 보유하는지 확인한다.
"""
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.cb_scope import assert_auditor_in_cb_scope, filter_by_cb_auditor_scope
from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.auditor import AuditApplication, Auditor, AuditorScopeGrants
from app.models.contract import AuditAssignment, Contract
from app.schemas.contract import AuditAssignmentCreate, AuditAssignmentResponse, AuditAssignmentUpdate

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _get_application_or_404(db: Session, application_id: int) -> AuditApplication:
    application = db.get(AuditApplication, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"심사 신청서(application_id={application_id})를 찾을 수 없습니다.",
        )
    return application


def _get_auditor_or_404(db: Session, auditor_id: int) -> int:
    # 주의: 레거시 `Auditor` 모델이 실제 auditors 테이블과 컬럼이 어긋나 있어(cb_id 등 phantom 컬럼)
    # db.get(Auditor, ...)로 전체 컬럼을 SELECT하면 실패한다. id 컬럼만 조회해 존재 여부만 확인한다.
    exists = db.query(Auditor.id).filter(Auditor.id == auditor_id).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"심사원(auditor_id={auditor_id})을 찾을 수 없습니다.")
    return auditor_id


def _get_contract_or_404(db: Session, contract_id: int) -> Contract:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"계약(contract_id={contract_id})을 찾을 수 없습니다.")
    return contract


def _validate_auditor_qualification(db: Session, auditor_id: int, cb_id: int, standard: str) -> None:
    """해당 심사원이 해당 인증원(CB)에서 지정 표준에 대해 승인된(active) 자격범위를 보유하는지 검증한다.

    `AuditorScopeGrants`(auditor_scope_grants) 기준으로 판단하며, `is_active=True`이고
    만료(expires_at)되지 않은 부여 건이 하나라도 있어야 통과한다. 조건을 만족하지 못하면 403.
    """
    today = date.today()
    grant = (
        db.query(AuditorScopeGrants.id)
        .filter(
            AuditorScopeGrants.auditor_id == auditor_id,
            AuditorScopeGrants.cb_id == cb_id,
            AuditorScopeGrants.standard_code == standard,
            AuditorScopeGrants.is_active.is_(True),
            or_(AuditorScopeGrants.expires_at.is_(None), AuditorScopeGrants.expires_at >= today),
        )
        .first()
    )
    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"심사원(auditor_id={auditor_id})은 해당 인증원(cb_id={cb_id})에서 "
                f"'{standard}' 표준에 대해 승인된 자격범위가 없어 배정할 수 없습니다."
            ),
        )


@router.get("", response_model=List[AuditAssignmentResponse])
def list_assignments(
    skip: int = 0,
    limit: int = 100,
    application_id: Optional[int] = None,
    auditor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> List[AuditAssignment]:
    """배정 목록을 조회합니다 (application_id / auditor_id로 필터링 가능).
    로그인한 인증원(CB) 소속 심사원의 배정만 조회됩니다 (platform_admin 제외)."""
    query = db.query(AuditAssignment)
    query = filter_by_cb_auditor_scope(query, db, current_user, AuditAssignment.auditor_id)
    if application_id is not None:
        query = query.filter(AuditAssignment.application_id == application_id)
    if auditor_id is not None:
        query = query.filter(AuditAssignment.auditor_id == auditor_id)
    return query.order_by(AuditAssignment.id.desc()).offset(skip).limit(limit).all()


@router.get("/{assignment_id}", response_model=AuditAssignmentResponse)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> AuditAssignment:
    """단일 배정을 조회합니다. 타 인증원 소속 심사원의 배정은 조회할 수 없습니다."""
    assignment = db.get(AuditAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"배정(id={assignment_id})을 찾을 수 없습니다.")
    assert_auditor_in_cb_scope(db, assignment.auditor_id, current_user)
    return assignment


@router.post("", response_model=AuditAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AuditAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> AuditAssignment:
    """신규 심사원 배정을 생성합니다. 타 인증원 소속 심사원은 배정할 수 없습니다.
    `standard`가 지정되면 로그인한 CB에서 해당 심사원이 그 표준에 대해 승인된 자격범위를
    보유하는지 사전 검증합니다 (platform_admin은 특정 CB 스코프가 없어 검증을 생략합니다)."""
    _get_application_or_404(db, payload.application_id)
    _get_auditor_or_404(db, payload.auditor_id)
    assert_auditor_in_cb_scope(db, payload.auditor_id, current_user)
    if payload.contract_id is not None:
        _get_contract_or_404(db, payload.contract_id)
    if payload.standard and current_user.cb_id is not None:
        _validate_auditor_qualification(db, payload.auditor_id, current_user.cb_id, payload.standard)

    assignment_data = payload.model_dump(exclude={"standard"})
    assignment = AuditAssignment(**assignment_data, created_at=datetime.now())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.patch("/{assignment_id}", response_model=AuditAssignmentResponse)
def update_assignment(
    assignment_id: int,
    payload: AuditAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> AuditAssignment:
    """배정 정보를 부분 수정합니다 (역할/상태 변경, 확정 처리 등).
    타 인증원 소속 심사원의 배정은 수정할 수 없습니다."""
    assignment = db.get(AuditAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"배정(id={assignment_id})을 찾을 수 없습니다.")
    assert_auditor_in_cb_scope(db, assignment.auditor_id, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    standard = update_data.pop("standard", None)

    if "application_id" in update_data:
        _get_application_or_404(db, update_data["application_id"])
    if "auditor_id" in update_data:
        _get_auditor_or_404(db, update_data["auditor_id"])
        assert_auditor_in_cb_scope(db, update_data["auditor_id"], current_user)
    if update_data.get("contract_id") is not None:
        _get_contract_or_404(db, update_data["contract_id"])

    if standard and current_user.cb_id is not None:
        target_auditor_id = update_data.get("auditor_id", assignment.auditor_id)
        _validate_auditor_qualification(db, target_auditor_id, current_user.cb_id, standard)

    for field, value in update_data.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> None:
    """배정을 삭제(취소)합니다. 타 인증원 소속 심사원의 배정은 삭제할 수 없습니다."""
    assignment = db.get(AuditAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"배정(id={assignment_id})을 찾을 수 없습니다.")
    assert_auditor_in_cb_scope(db, assignment.auditor_id, current_user)
    db.delete(assignment)
    db.commit()
