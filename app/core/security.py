"""인증 유틸 + 임시 인증 스텁 (Auth Stub).

JWT 발급/검증·비밀번호 해시·역할 체크는 아래에 구현되어 있다.
엔드포인트의 `get_current_user`는 아직 `X-User-Id` 헤더 스텁이며,
JWT 로그인 도입 시 Bearer 검증으로 교체하면 된다.

TODO(auth): get_current_user를 Authorization: Bearer <JWT> 기반으로 교체.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.auth import Users
from app.models.enums import UsersRole

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8시간

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: Any,
    role: str,
    entity_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "entity_id": entity_id,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 검증할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return payload
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, payload: dict = Depends(get_current_user_payload)) -> dict:
        user_role = payload.get("role")
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="해당 리소스에 접근할 권한이 없습니다.",
            )
        return payload


# 역할별 접근 제한 (UsersRole 값과 일치)
require_admin = RoleChecker([UsersRole.PLATFORM_ADMIN.value])
require_cb = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.CB_ADMIN.value])
require_auditor = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.AUDITOR.value])
require_company = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.CLIENT_ADMIN.value])


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
    if current_user.role == UsersRole.PLATFORM_ADMIN.value:
        return current_user
    if current_user.cb_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 인증원(CB) 정보가 없어 이 리소스에 접근할 수 없습니다.",
        )
    return current_user


def require_platform_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """플랫폼 관리자 전용 리소스(CB 인정서 승인, 산출 지침 수정 등)에 접근을 제한한다.

    `require_cb_scope`와 달리 CB 소속 사용자는 role에 관계없이 접근할 수 없고,
    반드시 `role == "platform_admin"`인 사용자만 통과한다.
    """
    if current_user.role != UsersRole.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="플랫폼 관리자만 접근할 수 있는 리소스입니다.",
        )
    return current_user
