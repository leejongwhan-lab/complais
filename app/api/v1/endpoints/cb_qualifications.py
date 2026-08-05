"""인증원(CB) 심사원 자격 부여 API."""
import csv
import io
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_cb
from app.core.constants import AuditorGrade, MembershipStatus
from app.core.security import CurrentUser, get_password_hash, require_cb_scope
from app.models.auditor import Auditor, AuditorApprovalHistory, AuditorCbMemberships
from app.models.auth import Users
from app.models.enums import (
    AuditorApprovalHistoryActionType,
    AuditorApprovalHistoryResult,
    AuditorCbMembershipsStatus,
    KarQualificationsStatus,
    UsersRole,
)
from app.models.misc import KarQualifications

router = APIRouter(prefix="/cb/qualifications", tags=["CB Qualifications"])

BULK_IMPORT_TEMP_PASSWORD = "ISO17021!!"

_GRADE_ALIASES = {
    "trainee": AuditorGrade.TRAINEE.value,
    "심사원보": AuditorGrade.TRAINEE.value,
    "auditor": AuditorGrade.AUDITOR.value,
    "심사원": AuditorGrade.AUDITOR.value,
    "lead_auditor": AuditorGrade.LEAD_AUDITOR.value,
    "선임심사원": AuditorGrade.LEAD_AUDITOR.value,
    "senior": AuditorGrade.LEAD_AUDITOR.value,
    "verified_auditor": AuditorGrade.VERIFIED_AUDITOR.value,
    "검증심사원": AuditorGrade.VERIFIED_AUDITOR.value,
    "검증원": AuditorGrade.VERIFIED_AUDITOR.value,
    "verifier": AuditorGrade.VERIFIED_AUDITOR.value,
}

class GrantQualificationRequest(BaseModel):
    membership_id: int
    auditor_id: int
    standard: str = Field(..., description='승인 표준 (예: "ISO9001")')
    approved_grade: str = Field(
        ..., description="trainee, auditor, lead_auditor, verified_auditor"
    )
    iaf_codes: str = Field(..., description='예: "14, 19, 28"')
    witness_auditor_id: Optional[int] = None
    witness_contract_id: Optional[int] = None
    witness_date: Optional[str] = None
    note: Optional[str] = None


class UpdateMembershipQualificationRequest(BaseModel):
    """CB 소속 자격/평가 갱신 payload."""

    status: Optional[str] = Field(
        default=None,
        description="requested, under_review, approved, rejected, terminated, suspended, expired",
    )
    approved_grade: Optional[AuditorGrade] = None
    qualification_granted_at: Optional[date] = None
    qualification_expires_at: Optional[date] = None
    knowledge_eval_score: Optional[int] = Field(default=None, ge=0, le=100)
    cpd_hours_completed: Optional[int] = Field(default=None, ge=0)
    conflict_of_interest_cleared: Optional[bool] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    cert_standards: Optional[str] = None
    approved_iaf_codes: Optional[str] = None


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


def _normalize_grade(raw: str) -> str:
    key = (raw or "").strip()
    if not key:
        return AuditorGrade.AUDITOR.value
    mapped = _GRADE_ALIASES.get(key) or _GRADE_ALIASES.get(key.lower())
    if mapped:
        return mapped
    # 이미 코드 형태이면 그대로 허용
    try:
        return AuditorGrade(key.lower()).value
    except ValueError:
        return key


def get_current_cb_admin(
    _: dict = Depends(require_cb),
    current_user: CurrentUser = Depends(require_cb_scope),
) -> CurrentUser:
    """인증원 관리자(또는 플랫폼 관리자) 전용."""
    return current_user


def _require_cb_bulk_manager(current_user: CurrentUser) -> CurrentUser:
    """cb_bulk_import.php — cb_admin / cb_manager 만 허용."""
    if current_user.role not in {
        UsersRole.CB_ADMIN.value,
        UsersRole.CB_MANAGER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다.",
        )
    if current_user.cb_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="소속 인증원(CB) 정보가 없어 업로드할 수 없습니다.",
        )
    return current_user


def _upsert_bulk_auditor_row(
    db: Session,
    *,
    cb_id: int,
    approved_by: int,
    name: str,
    email: str,
    phone: Optional[str],
    birth_date: Optional[date],
    kar_no: Optional[str],
    grade: str,
    standards: Optional[str],
    iaf_codes: Optional[str],
) -> str:
    """유저 + 심사원 + CB 멤버십 upsert. 반환: created | updated."""
    now = datetime.utcnow()
    action = "updated"

    # Identity: 이메일로 user_id만 매핑. users.cb_id 는 항상 NULL 유지 (CB 비종속)
    user = db.query(Users).filter(Users.email == email).first()
    if not user:
        action = "created"
        user = Users(
            email=email,
            password_hash=get_password_hash(BULK_IMPORT_TEMP_PASSWORD),
            name=name,
            phone=phone,
            role=UsersRole.AUDITOR.value,
            cb_id=None,
            company_id=None,
            is_active=True,
            status="active",
            membership_status=MembershipStatus.APPROVED.value,
            approved_by=approved_by,
            approved_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
    else:
        # 타 CB membership / users.cb_id 는 조회·수정하지 않음
        user.name = name or user.name
        user.phone = phone or user.phone
        if user.role != UsersRole.AUDITOR.value:
            user.role = UsersRole.AUDITOR.value
        user.cb_id = None  # Identity 원칙 유지
        user.membership_status = MembershipStatus.APPROVED.value
        user.is_active = True
        user.status = "active"
        user.updated_at = now
        db.flush()

    auditor = db.query(Auditor).filter(Auditor.user_id == user.id).first()
    if not auditor and email:
        auditor = db.query(Auditor).filter(Auditor.email == email).first()
    if not auditor:
        auditor = Auditor(
            user_id=user.id,
            name=name,
            email=email,
            phone=phone,
            birth_date=birth_date,
            grade=grade,
            primary_cb_id=None,  # 첫 승인/소속 시에만 설정 — bulk에서 타 CB 덮어쓰기 금지
            employment_type="fulltime",
            is_freelance=False,
            is_active=True,
            status="active",
            profile_status="active",
            address="미입력",
            detail_address="미입력",
            created_at=now,
            updated_at=now,
        )
        db.add(auditor)
        db.flush()
    else:
        auditor.user_id = user.id
        auditor.name = name or auditor.name
        auditor.email = email
        auditor.phone = phone or auditor.phone
        if birth_date:
            auditor.birth_date = birth_date
        # grade / iaf_codes / primary_cb_id 는 공용 Identity에 타 CB 값 덮어쓰지 않음
        auditor.is_active = True
        auditor.status = "active"
        auditor.profile_status = auditor.profile_status or "active"
        auditor.updated_at = now
        db.flush()

    # 업로드 CB 의 membership 만 upsert — 타 CB 레코드는 조회/수정하지 않음
    membership = (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.auditor_id == auditor.id,
            AuditorCbMemberships.cb_id == cb_id,
        )
        .first()
    )
    if not membership:
        membership = AuditorCbMemberships(
            auditor_id=auditor.id,
            cb_id=cb_id,
            employment_type="fulltime",
            is_freelance=False,
            status=AuditorCbMembershipsStatus.APPROVED.value,
            is_primary=False,
            apply_grade=grade,
            approved_grade=grade,
            grade_at_cb=grade,
            cert_standards=standards,
            approved_iaf_codes=iaf_codes,
            kar_no=kar_no,
            conflict_of_interest_cleared=True,
            cpd_hours_completed=0,
            qualification_granted_at=now.date(),
            approved_by=approved_by,
            approved_at=now,
            requested_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(membership)
        if not auditor.primary_cb_id:
            auditor.primary_cb_id = cb_id
    else:
        membership.status = AuditorCbMembershipsStatus.APPROVED.value
        membership.approved_grade = grade
        membership.grade_at_cb = grade
        membership.apply_grade = grade
        membership.cert_standards = standards
        membership.approved_iaf_codes = iaf_codes
        if kar_no:
            membership.kar_no = kar_no
        membership.conflict_of_interest_cleared = True
        membership.qualification_granted_at = (
            membership.qualification_granted_at or now.date()
        )
        membership.approved_by = approved_by
        membership.approved_at = now
        membership.updated_at = now

    db.flush()
    return action


def _get_membership_in_scope(
    db: Session,
    membership_id: int,
    current_user: CurrentUser,
) -> AuditorCbMemberships:
    membership = (
        db.query(AuditorCbMemberships)
        .filter(AuditorCbMemberships.id == membership_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="소속/자격 정보를 찾을 수 없습니다.",
        )
    if (
        current_user.role != UsersRole.PLATFORM_ADMIN.value
        and membership.cb_id != current_user.cb_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 인증기관의 소속 정보는 수정할 수 없습니다.",
        )
    return membership


@router.patch("/memberships/{membership_id}")
def update_membership_qualification(
    membership_id: int,
    payload: UpdateMembershipQualificationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_cb_admin),
):
    """CB별 심사원 전속 자격/평가 정보 갱신."""
    membership = _get_membership_in_scope(db, membership_id, current_user)
    now = datetime.utcnow()
    data = payload.model_dump(exclude_unset=True)

    if "status" in data and data["status"] is not None:
        allowed = {s.value for s in AuditorCbMembershipsStatus}
        if data["status"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"허용되지 않는 status 입니다: {data['status']}",
            )
        membership.status = data["status"]
        if data["status"] == AuditorCbMembershipsStatus.APPROVED.value:
            if membership.approved_at is None:
                membership.approved_at = now
            membership.approved_by = current_user.id

    if "approved_grade" in data and data["approved_grade"] is not None:
        grade = data["approved_grade"]
        grade_value = grade.value if isinstance(grade, AuditorGrade) else grade
        membership.approved_grade = grade_value
        membership.grade_at_cb = grade_value
        auditor = db.query(Auditor).filter(Auditor.id == membership.auditor_id).first()
        if auditor:
            auditor.grade = grade_value
            auditor.updated_at = now

    for field in (
        "qualification_granted_at",
        "qualification_expires_at",
        "knowledge_eval_score",
        "cpd_hours_completed",
        "conflict_of_interest_cleared",
        "cert_standards",
        "approved_iaf_codes",
    ):
        if field in data:
            setattr(membership, field, data[field])

    if "extra_metadata" in data:
        # 부분 병합: 기존 JSON을 유지한 채 전달된 키만 갱신
        merged = dict(membership.extra_metadata or {})
        if data["extra_metadata"] is None:
            membership.extra_metadata = None
        else:
            merged.update(data["extra_metadata"])
            membership.extra_metadata = merged

    membership.updated_at = now
    db.commit()
    db.refresh(membership)

    return {
        "message": "소속 자격/평가 정보가 갱신되었습니다.",
        "membership_id": membership.id,
        "auditor_id": membership.auditor_id,
        "cb_id": membership.cb_id,
        "status": membership.status,
        "approved_grade": membership.approved_grade,
        "qualification_granted_at": membership.qualification_granted_at,
        "qualification_expires_at": membership.qualification_expires_at,
        "knowledge_eval_score": membership.knowledge_eval_score,
        "cpd_hours_completed": membership.cpd_hours_completed,
        "conflict_of_interest_cleared": membership.conflict_of_interest_cleared,
        "extra_metadata": membership.extra_metadata,
    }


@router.get("/memberships/{membership_id}")
def get_membership_qualification(
    membership_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_cb_admin),
):
    """CB별 심사원 전속 자격/평가 정보 조회."""
    membership = _get_membership_in_scope(db, membership_id, current_user)
    return {
        "id": membership.id,
        "auditor_id": membership.auditor_id,
        "cb_id": membership.cb_id,
        "status": membership.status,
        "approved_grade": membership.approved_grade,
        "cert_standards": membership.cert_standards,
        "approved_iaf_codes": membership.approved_iaf_codes,
        "qualification_granted_at": membership.qualification_granted_at,
        "qualification_expires_at": membership.qualification_expires_at,
        "knowledge_eval_score": membership.knowledge_eval_score,
        "cpd_hours_completed": membership.cpd_hours_completed,
        "conflict_of_interest_cleared": membership.conflict_of_interest_cleared,
        "extra_metadata": membership.extra_metadata,
        "requested_at": membership.requested_at,
        "approved_at": membership.approved_at,
        "approved_by": membership.approved_by,
    }


@router.post("/bulk-import", status_code=status.HTTP_200_OK)
async def bulk_import_auditors(
    csv_file: UploadFile = File(..., description="심사원 CSV (header 포함)"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_scope),
):
    """cb_bulk_import.php — CB 심사원 CSV 대량 업로드.

    CSV 컬럼: 0성명, 1이메일, 2연락처, 3생년월일, 4KAR등록번호, 5등급, 6승인표준, 7IAF코드
    임시 비밀번호: ISO17021!!
    """
    _require_cb_bulk_manager(current_user)
    cb_id = current_user.cb_id

    raw = await csv_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("cp949")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="CSV 인코딩을 확인할 수 없습니다. UTF-8 또는 CP949로 저장해 주세요.",
            ) from exc

    reader = csv.reader(io.StringIO(text))
    try:
        next(reader)  # Header 무시
    except StopIteration:
        raise HTTPException(status_code=400, detail="CSV 내용이 없습니다.")

    created = 0
    updated = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    try:
        for row_no, data in enumerate(reader, start=2):
            if not data or all(not str(c).strip() for c in data):
                skipped += 1
                continue

            # pad short rows
            cols = list(data) + [""] * max(0, 8 - len(data))
            name = str(cols[0]).strip()
            email = str(cols[1]).strip()
            phone = str(cols[2]).strip() or None
            birth_raw = str(cols[3]).strip()
            kar_no = str(cols[4]).strip() or None
            grade_raw = str(cols[5]).strip()
            standards = str(cols[6]).strip() or None
            iaf_codes = str(cols[7]).strip() or None

            if not name or not email:
                errors.append(
                    {"row": row_no, "email": email or None, "error": "성명/이메일은 필수입니다."}
                )
                continue

            try:
                birth_date = _parse_date(birth_raw) if birth_raw else None
            except HTTPException as exc:
                errors.append({"row": row_no, "email": email, "error": str(exc.detail)})
                continue

            try:
                action = _upsert_bulk_auditor_row(
                    db,
                    cb_id=cb_id,
                    approved_by=current_user.id,
                    name=name,
                    email=email,
                    phone=phone,
                    birth_date=birth_date,
                    kar_no=kar_no,
                    grade=_normalize_grade(grade_raw),
                    standards=standards,
                    iaf_codes=iaf_codes,
                )
                if action == "created":
                    created += 1
                else:
                    updated += 1
            except Exception as row_err:
                errors.append({"row": row_no, "email": email, "error": str(row_err)})

        if created + updated == 0 and errors:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "업로드 실패: 유효한 행이 없습니다.",
                    "errors": errors,
                },
            )

        db.commit()
        return {
            "message": "대량 업로드가 완료되었습니다.",
            "cb_id": cb_id,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors[:50],
            "temp_password": BULK_IMPORT_TEMP_PASSWORD,
            "redirect_to": "/cb_portal.html?tab=members",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"업로드 실패: {str(e)}",
        )


@router.post("/grant", status_code=status.HTTP_200_OK)
def grant_qualification(
    payload: GrantQualificationRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_cb_admin),
):
    """CB 소속 승인 + KAR 자격 부여 + 승인 이력 기록."""
    # 1. 소속 신청 내역 확인
    membership = (
        db.query(AuditorCbMemberships)
        .filter(
            AuditorCbMemberships.id == payload.membership_id,
            AuditorCbMemberships.auditor_id == payload.auditor_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="신청 정보를 찾을 수 없습니다.",
        )

    # CB 스코프 격리 (platform_admin은 전체 허용)
    if (
        current_user.role != UsersRole.PLATFORM_ADMIN.value
        and membership.cb_id != current_user.cb_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 인증기관의 소속 신청은 승인할 수 없습니다.",
        )

    auditor = db.query(Auditor).filter(Auditor.id == payload.auditor_id).first()
    if not auditor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="심사원 정보를 찾을 수 없습니다.",
        )

    # 2. 최초 자격부여 판단
    existing_quals = (
        db.query(KarQualifications)
        .filter(KarQualifications.auditor_id == payload.auditor_id)
        .count()
    )
    is_initial = existing_quals == 0

    # 3. 최초 자격부여 시 검증심사원 참관 정보 필수
    if is_initial and not payload.witness_auditor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="최초 자격부여 시 검증심사원 참관 정보는 필수 요구사항입니다.",
        )

    witness_date = _parse_date(payload.witness_date)
    now = datetime.utcnow()

    try:
        # 4. CB 소속 승인
        membership.status = AuditorCbMembershipsStatus.APPROVED.value
        membership.approved_grade = payload.approved_grade
        membership.grade_at_cb = payload.approved_grade
        membership.approved_iaf_codes = payload.iaf_codes
        membership.cert_standards = payload.standard
        membership.approved_at = now
        membership.approved_by = current_user.id
        membership.qualification_granted_at = now.date()
        membership.updated_at = now
        if payload.note:
            membership.cb_review_note = payload.note
        # 참관/비고를 가변 메타에 보존
        meta = dict(membership.extra_metadata or {})
        if payload.witness_auditor_id:
            meta["witness_auditor_id"] = payload.witness_auditor_id
        if payload.witness_contract_id:
            meta["witness_contract_id"] = payload.witness_contract_id
        if payload.witness_date:
            meta["witness_date"] = payload.witness_date
        if meta:
            membership.extra_metadata = meta

        # 5. 심사원 최종 등급/상태 업데이트
        auditor.grade = payload.approved_grade
        auditor.profile_status = "approved"
        auditor.status = "active"
        auditor.iaf_codes = payload.iaf_codes
        auditor.primary_cb_id = membership.cb_id
        auditor.updated_at = now

        # 6. KAR 자격 레코드 생성
        qualification = KarQualifications(
            auditor_id=payload.auditor_id,
            qualification_body_id=membership.cb_id,
            standard=payload.standard,
            grade=payload.approved_grade,
            status=KarQualificationsStatus.ACTIVE.value,
            iaf_codes=payload.iaf_codes,
            issued_at=now.date(),
            created_at=now,
        )
        db.add(qualification)

        # 7. 승인 이력 (참관 정보 포함)
        action_type = (
            AuditorApprovalHistoryActionType.INITIAL_VERIFICATION.value
            if is_initial
            else AuditorApprovalHistoryActionType.QUALIFICATION_EXPAND.value
        )
        history = AuditorApprovalHistory(
            auditor_id=payload.auditor_id,
            cb_id=membership.cb_id,
            action_type=action_type,
            standard_code=payload.standard[:20],
            from_grade=None,
            to_grade=payload.approved_grade,
            iaf_codes=payload.iaf_codes,
            result=AuditorApprovalHistoryResult.APPROVED.value,
            detail=payload.note,
            reviewed_by=current_user.id,
            reviewed_at=now,
            witness_auditor_id=payload.witness_auditor_id,
            witness_contract_id=payload.witness_contract_id,
            witness_date=witness_date,
            created_at=now,
        )
        db.add(history)

        db.commit()
        db.refresh(qualification)

        return {
            "message": "자격 부여 및 CB 소속 승인이 완료되었습니다.",
            "is_initial": is_initial,
            "membership_id": membership.id,
            "auditor_id": auditor.id,
            "qualification_id": qualification.id,
            "approved_grade": payload.approved_grade,
            "standard": payload.standard,
            "iaf_codes": payload.iaf_codes,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"자격 부여 처리 중 오류 발생: {str(e)}",
        )
