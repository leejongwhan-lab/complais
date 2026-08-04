"""임시 인증 스텁 (Auth Stub).

실제 로그인(JWT 발급/검증)이 아직 구현되지 않았다. 우선 `X-User-Id` 헤더로 로그인 사용자를
지정하는 임시 방식을 사용하고, 모든 엔드포인트는 `Depends(get_current_user)` 형태로만 의존하도록
작성한다. 추후 실제 JWT 인증이 도입되면 이 파일의 `get_current_user` 내부 구현만 교체하면 되고,
엔드포인트 코드는 변경할 필요가 없다.

TODO(auth): 실제 로그인 붙이면 Authorization: Bearer <JWT> 헤더를 디코딩해
sub(user_id)를 추출하는 방식으로 교체.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.auth import Users


class CurrentUser(BaseModel):
    """인증된 사용자 컨텍스트. 실제 로그인 도입 후에도 동일한 필드로 유지한다."""

    id: int
    role: str
    cb_id: Optional[int] = None
    company_id: Optional[int] = None


def get_current_user(
    x_user_id: Optional[int] = Header(
        default=None,
        alias="X-User-Id",
        description="[임시 인증 스텁] 실제 로그인 붙이기 전까지 사용하는 로그인 사용자 ID 헤더",
    ),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다. (임시 인증 스텁: X-User-Id 헤더를 전달하세요)",
        )

    # users 테이블 스키마 드리프트 방지를 위해 필요한 컬럼만 명시적으로 조회한다.
    row = (
        db.query(Users.id, Users.role, Users.cb_id, Users.company_id, Users.is_active)
        .filter(Users.id == x_user_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"사용자(id={x_user_id})를 찾을 수 없습니다.")
    if not row.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다.")

    return CurrentUser(id=row.id, role=row.role, cb_id=row.cb_id, company_id=row.company_id)


def require_cb_scope(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """PLATFORM_ADMIN을 제외한 사용자는 소속 인증원(cb_id)이 있어야 CB 스코프 리소스에 접근할 수 있다."""
    if current_user.role == "platform_admin":
        return current_user
    if current_user.cb_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 인증원(CB) 정보가 없어 이 리소스에 접근할 수 없습니다.",
        )
    return current_user
