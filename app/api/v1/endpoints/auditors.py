"""심사원(Auditor) 소속 CB 기준 조회 API.

사용자가 제시한 권한 격리 예시를 그대로 구현한다:

    def get_cb_auditors(db: Session, current_user: User):
        # 로그인한 인증원의 ID로만 엄격하게 조회 (타 인증원 데이터 접근 차단)
        return db.query(AuditorCBMembership)\\
                 .filter(AuditorCBMembership.cb_id == current_user.cb_id)\\
                 .all()

주의: 레거시 `Auditor.cb_id`는 실제 `auditors` 테이블에 없는 phantom 컬럼이므로
(app/core/cb_scope.py 주석 참고), CB 소속 판단은 반드시 `AuditorCbMemberships.cb_id`로 한다.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.cb_scope import is_platform_admin
from app.core.database import get_db
from app.core.security import CurrentUser, require_cb_scope
from app.models.auditor import AuditorCbMemberships
from app.schemas.auditor import AuditorCbMembershipsResponse

router = APIRouter(prefix="/auditors", tags=["Auditors"])


@router.get("/cb-memberships", response_model=List[AuditorCbMembershipsResponse])
def get_cb_auditors(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> List[AuditorCbMemberships]:
    """로그인한 인증원(CB) 소속 심사원 목록을 조회합니다.

    로그인한 인증원의 cb_id로만 엄격하게 조회하며, 타 인증원 데이터 접근은 차단됩니다.
    (platform_admin은 예외적으로 전체 조회 가능)
    """
    query = db.query(AuditorCbMemberships)
    if not is_platform_admin(current_user):
        query = query.filter(AuditorCbMemberships.cb_id == current_user.cb_id)
    return query.order_by(AuditorCbMemberships.id.desc()).all()
