"""CB Portal — accreditation request submit (request envelope only; no SoT write)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import CurrentUser, require_cb_portal_user
from app.data.standards_catalog import to_family_initial
from app.models.admin import CBAccreditation, CBAccreditationStatus, CBAccreditedScope
from app.models.auth import Notifications, Users
from app.models.cb import CertificationBodies
from app.models.enums import UsersRole
from app.models.standard import StandardMaster
from app.schemas.admin import CBAccreditedScopeResponse

router = APIRouter(prefix="/cb-portal", tags=["CB Portal Accreditation"])
logger = logging.getLogger(__name__)

_ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx"}


class ScopeRequestIn(BaseModel):
    standard_code: Optional[str] = None
    standard_master_id: Optional[int] = None
    iaf_code: str


class AccreditationRequestOut(BaseModel):
    id: int
    cb_id: int
    accreditation_body: str
    certificate_number: str
    certificate_file_url: Optional[str] = None
    status: str
    scopes: List[CBAccreditedScopeResponse] = Field(default_factory=list)
    message: str = "인정 신청이 접수되었습니다."


def _upload_root() -> Path:
    root = Path(getattr(settings, "UPLOAD_DIR", "") or "").expanduser()
    if not root or str(root) in {".", ""}:
        root = Path(__file__).resolve().parents[4] / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _require_cb_id(user: CurrentUser) -> int:
    if user.cb_id is None:
        raise HTTPException(status_code=403, detail="소속 인증원(CB) 정보가 없습니다.")
    return int(user.cb_id)


def _resolve_standard(db: Session, item: ScopeRequestIn) -> StandardMaster:
    if item.standard_master_id:
        row = db.get(StandardMaster, int(item.standard_master_id))
        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"표준 마스터(id={item.standard_master_id})를 찾을 수 없습니다.",
            )
        return row
    code = (item.standard_code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="standard_code 또는 standard_master_id가 필요합니다.")
    row = (
        db.query(StandardMaster)
        .filter(StandardMaster.standard_code == code)
        .first()
    )
    if row is None:
        fam = to_family_initial(code)
        if fam:
            for cand in (
                db.query(StandardMaster)
                .filter(StandardMaster.is_active.is_(True))
                .all()
            ):
                if to_family_initial(cand.standard_code) == fam:
                    return cand
        raise HTTPException(status_code=404, detail=f"표준을 찾을 수 없습니다: {code}")
    return row


def _parse_scopes(raw: str) -> List[ScopeRequestIn]:
    text = (raw or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="scopes(JSON)가 필요합니다.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"scopes JSON 파싱 실패: {e}") from e
    if not isinstance(data, list) or not data:
        raise HTTPException(status_code=400, detail="scopes는 1개 이상 필요합니다.")
    out: List[ScopeRequestIn] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"scopes[{i}] 형식이 올바르지 않습니다.")
        iaf = str(item.get("iaf_code") or item.get("scope_code") or "").strip()
        if not iaf:
            raise HTTPException(status_code=400, detail=f"scopes[{i}].iaf_code가 필요합니다.")
        out.append(
            ScopeRequestIn(
                standard_code=(item.get("standard_code") or None),
                standard_master_id=item.get("standard_master_id") or item.get("iso_standard_id"),
                iaf_code=iaf,
            )
        )
    return out


def _scope_response(db: Session, scope: CBAccreditedScope) -> CBAccreditedScopeResponse:
    std = scope.standard or db.get(StandardMaster, scope.iso_standard_id)
    return CBAccreditedScopeResponse(
        id=scope.id,
        cb_accreditation_id=scope.cb_accreditation_id,
        iso_standard_id=scope.iso_standard_id,
        iaf_code=scope.iaf_code,
        is_approved=bool(scope.is_approved),
        status=getattr(scope, "status", None),
        reject_reason=getattr(scope, "reject_reason", None),
        standard_code=std.standard_code if std else None,
        standard_name=std.standard_name if std else None,
    )


def _notify_admins_new_request(
    db: Session,
    *,
    cb: CertificationBodies,
    accreditation: CBAccreditation,
    scope_count: int,
) -> None:
    try:
        admin_ids = [
            int(uid)
            for (uid,) in db.query(Users.id)
            .filter(
                Users.role == UsersRole.PLATFORM_ADMIN.value,
                Users.is_active == True,  # noqa: E712
            )
            .all()
            if uid
        ]
    except Exception:
        logger.exception("admin notify lookup soft-fail")
        return
    if not admin_ids:
        return
    now = datetime.utcnow()
    title = "CB 인정범위 승인 요청"
    body = (
        f"{cb.name or cb.code or f'CB#{cb.id}'} — "
        f"{accreditation.accreditation_body} / {accreditation.certificate_number} "
        f"(scope {scope_count}건) 승인 요청이 접수되었습니다."
    )
    link = f"/platform-admin#accreditations?id={accreditation.id}"
    for uid in admin_ids:
        db.add(
            Notifications(
                user_id=uid,
                type="accreditation_request_pending",
                title=title,
                body=body,
                link=link,
                channel="in_app",
                is_read=False,
                sent_at=now,
            )
        )


@router.post(
    "/accreditation-requests",
    response_model=AccreditationRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def submit_accreditation_request(
    accreditation_body: str = Form(..., description="인정기구명 (KAB 등)"),
    certificate_number: str = Form(..., description="인정서 번호"),
    scopes: str = Form(
        ...,
        description='JSON 배열: [{"standard_code":"ISO 9001:2015","iaf_code":"14"}, ...]',
    ),
    certificate_file: UploadFile = File(..., description="인정서 파일"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> AccreditationRequestOut:
    """CB 인정 신청 — PENDING envelope만 생성. SoT/matrix에는 쓰지 않음."""
    cb_id = _require_cb_id(current_user)
    cb = db.get(CertificationBodies, cb_id)
    if not cb:
        raise HTTPException(status_code=404, detail="인증기관을 찾을 수 없습니다.")

    ab = (accreditation_body or "").strip()
    cert_no = (certificate_number or "").strip()
    if not ab or not cert_no:
        raise HTTPException(status_code=400, detail="인정기구명과 인정서 번호가 필요합니다.")

    scope_items = _parse_scopes(scopes)
    resolved = []
    for item in scope_items:
        std = _resolve_standard(db, item)
        resolved.append((std, item.iaf_code.strip()))

    if not certificate_file or not certificate_file.filename:
        raise HTTPException(status_code=400, detail="인정서 파일이 필요합니다.")
    ext = Path(certificate_file.filename).suffix.lower() or ".bin"
    if ext not in _ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")
    content = await certificate_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")

    accreditation = CBAccreditation(
        cb_id=cb_id,
        accreditation_body=ab,
        certificate_number=cert_no,
        certificate_file_url=None,
        status=CBAccreditationStatus.PENDING.value,
    )
    db.add(accreditation)
    db.flush()

    folder = _upload_root() / "accreditation" / str(accreditation.id)
    folder.mkdir(parents=True, exist_ok=True)
    saved_name = f"{uuid.uuid4().hex}{ext}"
    (folder / saved_name).write_bytes(content)
    rel_path = f"accreditation/{accreditation.id}/{saved_name}"
    accreditation.certificate_file_url = rel_path

    for std, iaf in resolved:
        db.add(
            CBAccreditedScope(
                cb_accreditation_id=accreditation.id,
                iso_standard_id=std.id,
                iaf_code=iaf,
                is_approved=False,
                status=CBAccreditationStatus.PENDING.value,
            )
        )

    _notify_admins_new_request(
        db, cb=cb, accreditation=accreditation, scope_count=len(resolved)
    )
    db.commit()
    db.refresh(accreditation)

    return AccreditationRequestOut(
        id=accreditation.id,
        cb_id=accreditation.cb_id,
        accreditation_body=accreditation.accreditation_body,
        certificate_number=accreditation.certificate_number,
        certificate_file_url=accreditation.certificate_file_url,
        status=accreditation.status,
        scopes=[_scope_response(db, s) for s in accreditation.scopes],
    )


@router.get("/accreditation-requests", response_model=List[AccreditationRequestOut])
def list_my_accreditation_requests(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
) -> List[AccreditationRequestOut]:
    cb_id = _require_cb_id(current_user)
    rows = (
        db.query(CBAccreditation)
        .filter(CBAccreditation.cb_id == cb_id)
        .order_by(CBAccreditation.id.desc())
        .limit(100)
        .all()
    )
    return [
        AccreditationRequestOut(
            id=r.id,
            cb_id=r.cb_id,
            accreditation_body=r.accreditation_body,
            certificate_number=r.certificate_number,
            certificate_file_url=r.certificate_file_url,
            status=r.status,
            scopes=[_scope_response(db, s) for s in r.scopes],
            message="",
        )
        for r in rows
    ]
