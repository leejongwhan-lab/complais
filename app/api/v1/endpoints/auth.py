"""인증(Auth) — 회원가입 / 로그인 / 내 정보."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_payload, get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.auditor import Auditor
from app.models.auth import Users  # Users 모델 (app.models.users 없음)

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "client_admin"  # platform_admin, cb_admin, auditor, client_admin
    company_id: Optional[int] = None
    cb_id: Optional[int] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(Users).filter(Users.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    now = datetime.utcnow()
    new_user = Users(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        name=user_in.name,
        role=user_in.role,
        company_id=user_in.company_id,
        cb_id=user_in.cb_id,
        is_active=True,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입이 완료되었습니다.", "user_id": new_user.id}


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # username 필드에 email 입력
    user = db.query(Users).filter(Users.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    if not user.is_active or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화되거나 승인 대기 중인 계정입니다.",
        )

    # entity_id 매핑 (auditor는 auditors.user_id로 역조회)
    entity_id = None
    if user.role == "client_admin":
        entity_id = user.company_id
    elif user.role == "cb_admin":
        entity_id = user.cb_id
    elif user.role == "auditor":
        auditor_record = db.query(Auditor).filter(Auditor.user_id == user.id).first()
        if auditor_record:
            entity_id = auditor_record.id

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        entity_id=entity_id,
    )
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "entity_id": entity_id,
    }


@router.get("/me")
def get_me(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    user_id = payload.get("sub")
    user = db.query(Users).filter(Users.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "entity_id": payload.get("entity_id"),
        "is_active": user.is_active,
        "status": user.status,
    }
