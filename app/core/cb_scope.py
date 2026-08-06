"""CB(인증원) 단위 데이터 격리 유틸리티.

주의: 레거시 `Auditor.cb_id`는 실제 `auditors` 테이블에 존재하지 않는 phantom 컬럼이다
(실 컬럼명은 `primary_cb_id`). 따라서 심사원의 CB 소속 여부는 반드시
`AuditorCbMemberships.cb_id`(auditor_cb_memberships 테이블)를 기준으로 판단해야 한다.

이 모듈의 함수들은 `current_user.role == "platform_admin"`인 경우 격리를 적용하지 않는다
(플랫폼 관리자는 모든 CB 데이터에 접근 가능).
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Query, Session

from app.core.security import CurrentUser
from app.models.auditor import AuditorCbMemberships


def is_platform_admin(current_user: CurrentUser) -> bool:
    return current_user.role == "platform_admin"


def assert_auditor_in_cb_scope(db: Session, auditor_id: int, current_user: CurrentUser) -> None:
    """`auditor_id`가 `current_user.cb_id` 소속(재직/의뢰 중인 CB)인지 검증한다.

    타 인증원 소속 심사원의 데이터에는 접근할 수 없도록 차단한다 (platform_admin 예외).
    """
    if is_platform_admin(current_user):
        return

    exists = (
        db.query(AuditorCbMemberships.id)
        .filter(
            AuditorCbMemberships.auditor_id == auditor_id,
            AuditorCbMemberships.cb_id == current_user.cb_id,
        )
        .first()
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 심사원은 소속 인증원(CB)에 속하지 않아 접근할 수 없습니다.",
        )


def filter_by_cb_auditor_scope(query: Query, db: Session, current_user: CurrentUser, auditor_id_column) -> Query:
    """목록 조회 쿼리에 `auditor_id_column IN (현재 CB 소속 auditor_id 목록)` 필터를 추가한다.

    platform_admin이면 필터를 적용하지 않고 그대로 반환한다.
    """
    if is_platform_admin(current_user):
        return query

    cb_auditor_ids = db.query(AuditorCbMemberships.auditor_id).filter(
        AuditorCbMemberships.cb_id == current_user.cb_id
    )
    return query.filter(auditor_id_column.in_(cb_auditor_ids))
