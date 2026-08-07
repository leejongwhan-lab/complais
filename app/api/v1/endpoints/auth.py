"""인증(Auth) — 회원가입 / 로그인 / 내 정보."""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_payload, get_db
from app.core.constants import MembershipStatus
from app.core.security import (
    CurrentUser,
    create_access_token,
    get_current_user,
    get_password_hash,
    require_cb_scope,
    verify_password,
)
from app.models.auditor import (
    Auditor,
    AuditorEducation,
    AuditorWorkExperience,
)
from app.models.auth import Users  # Users 모델 (app.models.users 없음)
from app.models.cb import CertificationBodies, CbOperationalRules
from app.models.company import Companies
from app.models.enums import UsersRole

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "client_admin"  # platform_admin, cb_admin, auditor, client_admin
    company_id: Optional[int] = None
    cb_id: Optional[int] = None


class ClientAdminRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    user_name: str
    company_id: int  # 확정된 마스터 DB ID


class ClientStaffRegisterRequest(BaseModel):
    """기업 임직원 소속 가입 신청 — 대표(client_admin) 승인 필요."""

    email: EmailStr
    password: str
    user_name: str
    phone: Optional[str] = None
    company_id: int


class CbAdminRegisterRequest(BaseModel):
    """인증기관 대표 관리자 가입 — 신규 CB 등록 + cb_admin 계정."""

    email: EmailStr
    password: str
    user_name: str
    name: Optional[str] = None  # PHP 필드명 호환 (없으면 user_name)
    phone: Optional[str] = None
    cb_code: str
    cb_name: str
    cb_type: str = "certification"
    cb_initial: Optional[str] = None
    biz_no: Optional[str] = None
    reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    address: Optional[str] = None
    zip_code: Optional[str] = None
    detail_address: Optional[str] = None
    tel: Optional[str] = None
    intro: Optional[str] = None


class CbStaffRegisterRequest(BaseModel):
    """일반 직원/심사원 CB 소속 가입 신청."""

    email: EmailStr
    password: str
    user_name: str
    name: Optional[str] = None  # PHP 필드명 호환
    phone: Optional[str] = None
    cb_id: int
    role: str = "cb_staff"  # cb_staff | auditor | cb_manager | cb_reviewer
    requested_role: Optional[str] = None  # PHP 필드명 호환


class CbSignupRequest(BaseModel):
    """signup_cb_action.php 대응 — signup_type=admin|staff."""

    signup_type: str  # admin | staff
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None

    # admin: 인증기관 마스터
    cb_name: Optional[str] = None
    cb_type: str = "certification"
    cb_code: Optional[str] = None
    cb_initial: Optional[str] = None
    biz_no: Optional[str] = None
    reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    address: Optional[str] = None
    # 우편번호/상세 — DB 컬럼 없으면 address 로 합쳐 저장 (additive, optional)
    zip_code: Optional[str] = None
    detail_address: Optional[str] = None

    # staff: 기존 CB 소속 신청
    selected_cb_id: Optional[int] = None
    requested_role: str = "cb_staff"  # cb_staff | auditor


class MembershipDecisionRequest(BaseModel):
    membership_status: str = Field(..., description="approved | rejected")
    note: Optional[str] = None


class EducationItem(BaseModel):
    school_name: str
    degree: str  # bachelor, master, doctor, other
    major: Optional[str] = None
    entered_at: Optional[str] = None
    graduated_at: Optional[str] = None


class WorkExperienceItem(BaseModel):
    company_name: str
    department: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    note: Optional[str] = None


class AuditorRegisterRequest(BaseModel):
    """심사원 개인 Identity 가입 — CB 선택 없음 (소속은 별도 memberships/request)."""

    # Step 1: 기본 정보
    name: str
    email: EmailStr
    password: str
    phone: str
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    address: str = "미입력"
    detail_address: str = "미입력"
    zip_code: Optional[str] = None  # 우편번호 — address 앞에 합쳐 저장 (별도 컬럼 없음)

    # Step 2: 고용 형태 (CB 소속과 무관)
    employment_type: str = "fulltime"  # fulltime, parttime
    is_freelance: bool = False
    apply_grade: str = "auditor"  # 희망 등급(프로필 기본값). CB 승인과 별개
    daily_rate: Optional[int] = 0
    fee_ratio: Optional[float] = 0.0
    monthly_fee: Optional[int] = 0

    # 레거시 호환: 전달되어도 무시 (Identity 가입에서 CB 바인딩 금지)
    cb_id: Optional[int] = None

    # Step 3~6: 이력 상세 (선택)
    educations: Optional[List[EducationItem]] = Field(default_factory=list)
    work_experiences: Optional[List[WorkExperienceItem]] = Field(default_factory=list)

    # Step 7: 계좌 정보
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"날짜 형식이 올바르지 않습니다: {value} (YYYY-MM-DD)",
    )


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
        membership_status=MembershipStatus.APPROVED.value,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입이 완료되었습니다.", "user_id": new_user.id}


@router.post("/register/client-admin", status_code=status.HTTP_201_CREATED)
def register_client_admin(
    payload: ClientAdminRegisterRequest,
    db: Session = Depends(get_db),
):
    """기업 담당자(client_admin) 회원가입 — company_id로 기업 마스터에 연결."""
    # 1. 기업 존재 여부 확인
    company = db.query(Companies).filter(Companies.id == payload.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="선택한 기업 정보를 찾을 수 없습니다.",
        )

    # 2. 이메일 중복 확인
    existing_user = db.query(Users).filter(Users.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입되어 있는 이메일 계정입니다.",
        )

    # 3. 계정 생성 및 기업 매핑
    now = datetime.utcnow()
    new_user = Users(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        name=payload.user_name,
        role=UsersRole.CLIENT_ADMIN.value,
        company_id=company.id,
        cb_id=None,
        is_active=True,
        status="active",
        membership_status=MembershipStatus.APPROVED.value,
        created_at=now,
        updated_at=now,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "회원가입이 성공적으로 완료되었습니다.",
        "user_id": new_user.id,
        "company_id": company.id,
        "company_name": company.name,
        "biz_no": company.biz_no,
        "role": new_user.role,
    }


@router.post("/register/client-staff", status_code=status.HTTP_201_CREATED)
def register_client_staff(
    payload: ClientStaffRegisterRequest,
    db: Session = Depends(get_db),
):
    """기업 임직원 가입 신청 — membership_status=pending."""
    company = db.query(Companies).filter(Companies.id == payload.company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="선택한 기업 정보를 찾을 수 없습니다.",
        )

    if db.query(Users).filter(Users.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입되어 있는 이메일 계정입니다.",
        )

    now = datetime.utcnow()
    new_user = Users(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        name=payload.user_name,
        phone=payload.phone,
        role=UsersRole.CLIENT_STAFF.value,
        company_id=company.id,
        cb_id=None,
        is_active=True,
        status="active",
        membership_status=MembershipStatus.PENDING.value,
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "소속 가입 신청이 접수되었습니다. 기업 대표 관리자 승인 후 이용 가능합니다.",
        "user_id": new_user.id,
        "company_id": new_user.company_id,
        "company_name": company.name,
        "role": new_user.role,
        "membership_status": new_user.membership_status,
    }


def _register_cb_admin_tx(
    db: Session,
    *,
    email: str,
    password: str,
    name: str,
    phone: Optional[str],
    cb_name: str,
    cb_code: str,
    cb_type: str = "certification",
    cb_initial: Optional[str] = None,
    biz_no: Optional[str] = None,
    reg_no: Optional[str] = None,
    ceo_name: Optional[str] = None,
    address: Optional[str] = None,
    intro: Optional[str] = None,
) -> dict:
    """signup_cb_action.php admin 분기 — CB 생성 + cb_admin(approved) + owner + rules."""
    code = (cb_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="기관 코드(cb_code)는 필수입니다.")
    if not (cb_name or "").strip():
        raise HTTPException(status_code=400, detail="기관명(cb_name)은 필수입니다.")

    if db.query(CertificationBodies).filter(CertificationBodies.code == code).first():
        raise HTTPException(status_code=400, detail="이미 존재하는 기관 코드입니다.")

    from app.core.validators import normalize_biz_no, normalize_email, normalize_phone

    email_norm = normalize_email(email, required=True)
    phone_val = normalize_phone(phone, required=False) if phone else None
    biz_norm = normalize_biz_no(biz_no, required=False) if biz_no else None

    if db.query(Users).filter(Users.email == email_norm).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입되어 있는 이메일 계정입니다.",
        )

    now = datetime.utcnow()

    # 1. 인증기관 마스터 데이터 생성
    cb = CertificationBodies(
        code=code,
        name=cb_name.strip(),
        cb_type=cb_type or "certification",
        cb_initial=(cb_initial or code)[:20],
        biz_no=biz_norm,
        reg_no=reg_no,
        ceo_name=ceo_name,
        address=address,
        tel=phone_val,
        phone=phone_val,
        email=email_norm,
        intro=intro,
        is_active=True,
        fee_per_md=Decimal("0"),
        fee_travel=Decimal("0"),
        fee_cert=Decimal("0"),
        max_consecutive=3,
        impartiality_cycle_months=12,
        doc_rule_contract="CB-QE-{YYMMDD}-{SEQ3}",
        status="정상",
        created_at=now,
        updated_at=now,
    )
    db.add(cb)
    db.flush()

    # 2. 대표 관리자 계정 생성 (즉시 승인)
    new_user = Users(
        email=email_norm,
        password_hash=get_password_hash(password),
        name=name,
        phone=phone_val,
        role=UsersRole.CB_ADMIN.value,
        cb_id=cb.id,
        company_id=None,
        is_active=True,
        status="active",
        membership_status=MembershipStatus.APPROVED.value,
        approved_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    db.flush()

    # 3. CB 소유자 및 기본 운용 규칙 세팅
    cb.owner_user_id = new_user.id
    cb.updated_at = now
    db.add(
        CbOperationalRules(
            cb_id=cb.id,
            doc_rule_contract="CB-QE-{YYMMDD}-{SEQ3}",
            fee_per_md=0,
            fee_travel=0,
            fee_cert=0,
            max_consecutive_audits=3,
            impartiality_cycle_months=12,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()

    # 4. 당해 연도 기본 과금 계약 생성 (어드민 현황/과금 즉시 반영)
    from app.services.cb_billing import ensure_default_cb_contract

    ensure_default_cb_contract(db, cb, year=now.year)

    return {
        "message": "가입 신청이 완료되었습니다.",
        "user_id": new_user.id,
        "cb_id": cb.id,
        "cb_code": cb.code,
        "cb_name": cb.name,
        "role": new_user.role,
        "membership_status": new_user.membership_status,
    }


def _register_cb_member_pending_tx(
    db: Session,
    *,
    email: str,
    password: str,
    name: str,
    phone: Optional[str],
    cb_id: int,
    requested_role: str,
) -> dict:
    """signup_cb_action.php staff 분기 — users(pending)만 생성."""
    role = (requested_role or UsersRole.CB_STAFF.value).strip().lower()
    # 심사원은 Identity 분리: CB staff 가입 경로에서 auditor 계정 생성 금지
    if role == UsersRole.AUDITOR.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="심사원은 개인 계정으로 가입한 뒤 포털에서 CB 소속을 신청하세요. (/register/auditor)",
        )
    allowed = {
        UsersRole.CB_STAFF.value,
        UsersRole.CB_MANAGER.value,
        UsersRole.CB_REVIEWER.value,
    }
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="허용되지 않는 role 입니다. (cb_staff / cb_manager / cb_reviewer)",
        )

    cb = db.query(CertificationBodies).filter(CertificationBodies.id == cb_id).first()
    if not cb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="선택한 인증기관 정보를 찾을 수 없습니다.",
        )

    if db.query(Users).filter(Users.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입되어 있는 이메일 계정입니다.",
        )

    now = datetime.utcnow()
    new_user = Users(
        email=email,
        password_hash=get_password_hash(password),
        name=name,
        phone=(phone or "").strip() or None,
        role=role,
        cb_id=cb_id,
        company_id=None,
        is_active=True,
        status="active",
        membership_status=MembershipStatus.PENDING.value,
        approved_by=None,
        approved_at=None,
        created_at=now,
        updated_at=now,
    )
    db.add(new_user)
    db.flush()

    return {
        "message": "가입 신청이 완료되었습니다.",
        "user_id": new_user.id,
        "cb_id": new_user.cb_id,
        "cb_name": cb.name,
        "role": new_user.role,
        "membership_status": new_user.membership_status,
    }


def _compose_register_address(
    address: Optional[str] = None,
    zip_code: Optional[str] = None,
    detail_address: Optional[str] = None,
) -> Optional[str]:
    """우편번호·기본주소·상세를 단일 address 문자열로 합친다 (기존 컬럼 호환)."""
    parts = [
        (zip_code or "").strip(),
        (address or "").strip(),
        (detail_address or "").strip(),
    ]
    # address 가 이미 합쳐진 값이면 zip/detail 중복 합치기 방지
    base = parts[1]
    if base and parts[0] and parts[0] in base and not parts[2]:
        return base
    if base and parts[0] and parts[0] in base and parts[2] and parts[2] in base:
        return base
    merged = " ".join(p for p in parts if p)
    return merged or None


@router.post("/register/cb", status_code=status.HTTP_201_CREATED)
def register_cb(
    payload: CbSignupRequest,
    db: Session = Depends(get_db),
):
    """signup_cb_action.php — CB 대표(admin) / 직원·심사원(staff) 통합 가입."""
    signup_type = (payload.signup_type or "").strip().lower()
    if signup_type not in {"admin", "staff"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="signup_type은 admin 또는 staff 만 가능합니다.",
        )

    try:
        if signup_type == "admin":
            composed_address = _compose_register_address(
                address=payload.address,
                zip_code=payload.zip_code,
                detail_address=payload.detail_address,
            )
            result = _register_cb_admin_tx(
                db,
                email=str(payload.email),
                password=payload.password,
                name=payload.name.strip(),
                phone=payload.phone,
                cb_name=payload.cb_name or "",
                cb_code=payload.cb_code or "",
                cb_type=payload.cb_type or "certification",
                cb_initial=payload.cb_initial,
                biz_no=payload.biz_no,
                reg_no=payload.reg_no,
                ceo_name=payload.ceo_name,
                address=composed_address,
            )
        else:
            if not payload.selected_cb_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="selected_cb_id(소속 인증기관)는 필수입니다.",
                )
            result = _register_cb_member_pending_tx(
                db,
                email=str(payload.email),
                password=payload.password,
                name=payload.name.strip(),
                phone=payload.phone,
                cb_id=payload.selected_cb_id,
                requested_role=payload.requested_role,
            )
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"가입 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/register/cb-admin", status_code=status.HTTP_201_CREATED)
def register_cb_admin(
    payload: CbAdminRegisterRequest,
    db: Session = Depends(get_db),
):
    """인증기관 대표 가입 — /register/cb (admin) 래퍼."""
    try:
        result = _register_cb_admin_tx(
            db,
            email=str(payload.email),
            password=payload.password,
            name=(payload.name or payload.user_name or "").strip(),
            phone=payload.phone or payload.tel,
            cb_name=payload.cb_name,
            cb_code=payload.cb_code,
            cb_type=payload.cb_type or "certification",
            cb_initial=payload.cb_initial,
            biz_no=payload.biz_no,
            reg_no=payload.reg_no,
            ceo_name=payload.ceo_name,
            address=_compose_register_address(
                address=payload.address,
                zip_code=payload.zip_code,
                detail_address=payload.detail_address,
            ),
            intro=payload.intro,
        )
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"가입 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.post("/register/auditor", status_code=status.HTTP_201_CREATED)
def register_auditor(
    payload: AuditorRegisterRequest,
    db: Session = Depends(get_db),
):
    """심사원 개인 Identity 회원가입.

    - users.cb_id = NULL (특정 CB에 종속되지 않음)
    - users.membership_status = approved (플랫폼 계정은 즉시 사용 가능)
    - CB 소속/자격은 POST /auditor/memberships/request 로 별도 신청
    """
    if db.query(Users).filter(Users.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 가입되어 있는 이메일 주소입니다.",
        )

    now = datetime.utcnow()
    birth_date = _parse_date(payload.birth_date)

    try:
        new_user = Users(
            name=payload.name,
            email=payload.email,
            password_hash=get_password_hash(payload.password),
            phone=payload.phone,
            role=UsersRole.AUDITOR.value,
            cb_id=None,  # Identity — CB 비종속
            company_id=None,
            is_active=True,
            status="active",
            membership_status=MembershipStatus.APPROVED.value,
            created_at=now,
            updated_at=now,
        )
        db.add(new_user)
        db.flush()

        addr_base = (payload.address or "").strip() or "미입력"
        zip_c = (payload.zip_code or "").strip()
        if zip_c and addr_base != "미입력" and zip_c not in addr_base:
            addr_base = f"{zip_c} {addr_base}"
        new_auditor = Auditor(
            user_id=new_user.id,
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            birth_date=birth_date,
            gender=payload.gender,
            address=addr_base,
            detail_address=(payload.detail_address or "").strip() or "미입력",
            employment_type=payload.employment_type,
            is_freelance=payload.is_freelance,
            grade=payload.apply_grade,
            primary_cb_id=None,
            daily_rate=float(payload.daily_rate or 0) or None,
            fee_ratio=float(payload.fee_ratio or 0) or None,
            monthly_fee=float(payload.monthly_fee or 0) or None,
            bank_name=payload.bank_name,
            account_no=payload.account_no,
            account_holder=payload.account_holder,
            is_active=True,
            status="active",
            profile_status="active",
            created_at=now,
            updated_at=now,
        )
        db.add(new_auditor)
        db.flush()

        for edu in payload.educations or []:
            db.add(
                AuditorEducation(
                    auditor_id=new_auditor.id,
                    school_name=edu.school_name,
                    degree=edu.degree,
                    major=edu.major or "-",
                    entered_at=_parse_date(edu.entered_at),
                    graduated_at=_parse_date(edu.graduated_at),
                    is_verified=False,
                    created_at=now,
                )
            )

        for work in payload.work_experiences or []:
            start_date = _parse_date(work.start_date)
            if start_date is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"경력 '{work.company_name}'의 시작일(start_date)은 필수입니다.",
                )
            note_parts = [p for p in (work.department, work.note) if p]
            db.add(
                AuditorWorkExperience(
                    auditor_id=new_auditor.id,
                    company_name=work.company_name,
                    position=work.position,
                    start_date=start_date,
                    end_date=_parse_date(work.end_date),
                    is_current=work.is_current,
                    note=" / ".join(note_parts) if note_parts else None,
                    created_at=now,
                )
            )

        db.commit()
        return {
            "message": "심사원 개인 계정이 생성되었습니다. 로그인 후 인증기관(CB) 소속을 신청하세요.",
            "user_id": new_user.id,
            "auditor_id": new_auditor.id,
            "cb_id": None,
            "membership_status": new_user.membership_status,
            "profile_status": new_auditor.profile_status,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"가입 처리 중 오류 발생: {str(e)}",
        )


@router.post("/register/cb-staff", status_code=status.HTTP_201_CREATED)
def register_cb_staff(
    payload: CbStaffRegisterRequest,
    db: Session = Depends(get_db),
):
    """CB 직원/심사원 소속 가입 신청 — /register/cb (staff) 래퍼."""
    try:
        result = _register_cb_member_pending_tx(
            db,
            email=str(payload.email),
            password=payload.password,
            name=(payload.name or payload.user_name or "").strip(),
            phone=payload.phone,
            cb_id=payload.cb_id,
            requested_role=payload.requested_role or payload.role,
        )
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"가입 처리 중 오류가 발생했습니다: {str(e)}",
        )


@router.patch("/memberships/{user_id}/decision")
def decide_user_membership(
    user_id: int,
    payload: MembershipDecisionRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """CB 대표(cb_admin)가 소속 직원의 가입 신청을 승인/반려."""
    if current_user.role not in {
        UsersRole.PLATFORM_ADMIN.value,
        UsersRole.CB_ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 승인 권한이 없습니다.",
        )

    decision = payload.membership_status.strip().lower()
    if decision not in {MembershipStatus.APPROVED.value, MembershipStatus.REJECTED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="membership_status는 approved 또는 rejected 만 가능합니다.",
        )

    target = db.query(Users).filter(Users.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="대상 사용자를 찾을 수 없습니다.")

    if (
        current_user.role != UsersRole.PLATFORM_ADMIN.value
        and target.cb_id != current_user.cb_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 인증기관 소속 신청은 처리할 수 없습니다.",
        )

    now = datetime.utcnow()
    target.membership_status = decision
    target.approved_by = current_user.id if decision == MembershipStatus.APPROVED.value else None
    target.approved_at = now if decision == MembershipStatus.APPROVED.value else None
    target.updated_at = now
    db.commit()

    return {
        "message": "소속 승인 상태가 갱신되었습니다.",
        "user_id": target.id,
        "membership_status": target.membership_status,
        "approved_by": target.approved_by,
        "approved_at": target.approved_at,
        "note": payload.note,
    }


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

    # 승인 상태 검증 (login_action.php)
    membership_status = getattr(user, "membership_status", MembershipStatus.APPROVED.value)
    if membership_status == MembershipStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 기관(기업) 대표 관리자의 승인 대기 중입니다.",
        )
    if membership_status == MembershipStatus.REJECTED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="가입 승인이 거절되었습니다. 관리자에게 문의하세요.",
        )

    # entity_id 매핑 + CB/기업 소속 세션 고정 (17021-1 격리)
    entity_id = None
    if user.role in {"client_admin", "client_staff"}:
        entity_id = user.company_id
    elif user.role in {"cb_admin", "cb_staff", "cb_manager", "cb_reviewer"}:
        entity_id = user.cb_id
    elif user.role == "auditor":
        auditor_record = db.query(Auditor).filter(Auditor.user_id == user.id).first()
        if auditor_record:
            entity_id = auditor_record.id

    access_token = create_access_token(
        subject=user.id,
        role=user.role,
        entity_id=entity_id,
        cb_id=user.cb_id,
        company_id=user.company_id,
    )
    user.last_login_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    db.commit()

    # 역할별 리다이렉트 (4대 포탈 체계)
    role = user.role or ""
    if role in {"cb_admin", "cb_manager", "cb_staff", "cb_reviewer"}:
        redirect_to = "/cb-portal"
    elif role in {"client_admin", "client_staff", "enterprise_admin", "enterprise_user"}:
        redirect_to = "/enterprise"
    elif role == "auditor":
        redirect_to = "/auditor-portal"
    elif role in {"platform_admin", "admin"}:
        redirect_to = "/admin"
    else:
        redirect_to = "/admin"

    # 로그인 성공 및 세션 할당 ($_SESSION 대응)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_name": user.name,
        "role": user.role,
        "cb_id": user.cb_id,
        "company_id": user.company_id,
        "client_company_id": user.company_id,  # PHP client_company_id 별칭
        "entity_id": entity_id,
        "membership_status": membership_status,
        "redirect_to": redirect_to,
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
        "user_name": user.name,
        "role": user.role,
        "cb_id": user.cb_id,
        "company_id": user.company_id,
        "client_company_id": user.company_id,
        "entity_id": payload.get("entity_id"),
        "is_active": user.is_active,
        "status": user.status,
        "membership_status": getattr(user, "membership_status", MembershipStatus.APPROVED.value),
        "approved_by": getattr(user, "approved_by", None),
        "approved_at": getattr(user, "approved_at", None),
    }
