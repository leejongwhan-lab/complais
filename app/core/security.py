"""인증 유틸 — JWT 발급/검증 + RBAC dependency."""
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import jwt
from fastapi import Depends, HTTPException, status
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
    cb_id: Optional[int] = None,
    company_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """JWT 발급 — PHP 세션의 user_id/role/cb_id 고정에 대응."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "entity_id": entity_id,
        "cb_id": cb_id,
        "company_id": company_id,
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


# 역할별 접근 제한 (UsersRole 값과 일치) — JWT payload 기준
require_admin = RoleChecker([UsersRole.PLATFORM_ADMIN.value])
require_cb = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.CB_ADMIN.value])
require_auditor = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.AUDITOR.value])
require_company = RoleChecker([UsersRole.PLATFORM_ADMIN.value, UsersRole.CLIENT_ADMIN.value])


class CurrentUser(BaseModel):
    """인증된 사용자 컨텍스트."""

    id: int
    role: str
    cb_id: Optional[int] = None
    company_id: Optional[int] = None
    entity_id: Optional[int] = None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Authorization: Bearer <JWT> 를 검증하고 DB 사용자를 로드한다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명을 검증할 수 없습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise credentials_exception from exc

    row = (
        db.query(
            Users.id,
            Users.role,
            Users.cb_id,
            Users.company_id,
            Users.is_active,
            Users.status,
            Users.membership_status,
        )
        .filter(Users.id == user_id)
        .first()
    )
    if row is None:
        raise credentials_exception
    if not row.is_active or row.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화되거나 승인 대기 중인 계정입니다.",
        )
    membership_status = getattr(row, "membership_status", "approved") or "approved"
    if membership_status == "pending":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 기관(기업) 대표 관리자의 승인 대기 중입니다.",
        )
    if membership_status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="가입 승인이 거절되었습니다. 관리자에게 문의하세요.",
        )

    # JWT에 고정된 cb_id가 있으면 DB 값과 불일치 시 JWT 스코프를 우선하지 않고 DB를 신뢰
    # (세션 하이재킹/토큰 변조 대비). CB 역할은 DB.cb_id 필수.
    cb_id = row.cb_id
    company_id = row.company_id

    return CurrentUser(
        id=row.id,
        role=row.role,
        cb_id=cb_id,
        company_id=company_id,
        entity_id=payload.get("entity_id"),
    )


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


# 향후 CB 포털 역할이 같은 PATCH API를 재사용한다. 현재는 platform_admin이 주 사용자.
_CB_REVIEW_ROLES = frozenset(
    {
        UsersRole.CB_ADMIN.value,
        UsersRole.CB_STAFF.value,
        UsersRole.CB_MANAGER.value,
        UsersRole.CB_REVIEWER.value,
    }
)


def require_cb_review_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """기업 인증신청 MD 제안검토(PATCH): platform_admin 또는 CB 역할(+cb_id).

    플랫폼 어드민 대시보드의 MD 검토 API용. CB 포털 셸/대시보드는
    ``require_cb_portal_user`` 를 사용한다 (platform_admin 혼용 금지).
    """
    role = (current_user.role or "").lower()
    if role == UsersRole.PLATFORM_ADMIN.value:
        return current_user
    if role in _CB_REVIEW_ROLES:
        if current_user.cb_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="소속 인증원(CB) 정보가 없어 이 리소스에 접근할 수 없습니다.",
            )
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="MD 제안검토 권한이 없습니다. (platform_admin 또는 CB 역할 필요)",
    )


def require_cb_portal_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """CB 포털 전용 — cb_* 역할 + cb_id. platform_admin은 403 (어드민/CB 세션 분리)."""
    role = (current_user.role or "").lower()
    if role == UsersRole.PLATFORM_ADMIN.value or role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="플랫폼 관리자 계정으로는 CB 포털에 접근할 수 없습니다. CB 계정으로 로그인해 주세요.",
        )
    if role not in _CB_REVIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CB 포털 권한이 없습니다. (cb_admin / cb_manager / cb_staff / cb_reviewer)",
        )
    if current_user.cb_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 인증원(CB) 정보가 없어 CB 포털에 접근할 수 없습니다.",
        )
    return current_user


def require_platform_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """플랫폼 관리자 전용 리소스 접근 제한."""
    if current_user.role != UsersRole.PLATFORM_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="플랫폼 관리자만 접근할 수 있는 리소스입니다.",
        )
    return current_user


# 문서/가이드용 별칭 — admin.py의 /cb-contracts 등에서 사용
get_current_admin_user = require_platform_admin
get_current_platform_admin = require_platform_admin
