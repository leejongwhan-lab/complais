"""기업(User) 공통 헬퍼 — 역할/소속 기업 해석."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status

from app.core.security import CurrentUser
from app.models.enums import UsersRole

_CLIENT_ROLES = {
    UsersRole.CLIENT_ADMIN.value,
    UsersRole.CLIENT_STAFF.value,
    "client_admin",
    "client_staff",
}


def require_enterprise_user(current_user: CurrentUser) -> CurrentUser:
    if current_user.role in _CLIENT_ROLES or current_user.role == UsersRole.PLATFORM_ADMIN.value:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="기업 계정만 접근할 수 있습니다.",
    )


def resolve_company_id(current_user: CurrentUser, company_id: Optional[int] = None) -> int:
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        if not company_id:
            raise HTTPException(status_code=400, detail="platform_admin은 company_id가 필요합니다.")
        return company_id
    if current_user.company_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 기업(company_id) 정보가 없습니다.",
        )
    if company_id and company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="다른 기업 데이터에는 접근할 수 없습니다.")
    return current_user.company_id
