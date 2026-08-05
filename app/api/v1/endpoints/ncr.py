"""시정조치(NCR) — 기업 제출/상태 변경 API."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.config import settings
from app.core.security import CurrentUser, get_current_user
from app.models.audit import AuditNcrs
from app.models.contract import Contracts

router = APIRouter(prefix="/user/ncr", tags=["User NCR"])

_ACTIONABLE = {"PENDING", "pending", "OPEN", "open", "ISSUED", "issued", "REJECTED", "rejected"}


class NcrListItem(BaseModel):
    id: int
    contract_id: int
    clause_id: str
    std_code: str
    grade: str
    finding: Optional[str] = None
    requirement: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    correction: Optional[str] = None
    corrective_action: Optional[str] = None
    cause: Optional[str] = None
    ca_submitted_at: Optional[str] = None
    evidence_file: Optional[str] = None


class NcrActionResponse(BaseModel):
    success: bool = True
    ncr_id: int
    status: str
    message: str
    evidence_file: Optional[str] = None


def _upload_root() -> Path:
    root = Path(getattr(settings, "UPLOAD_DIR", "") or "").expanduser()
    if not root or str(root) in {".", ""}:
        root = Path(__file__).resolve().parents[4] / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _parse_evidence(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    return {"note": raw}


def _owned_ncr(db: Session, ncr_id: int, company_id: int) -> AuditNcrs:
    ncr = db.get(AuditNcrs, ncr_id)
    if not ncr:
        raise HTTPException(status_code=404, detail="NCR을 찾을 수 없습니다.")
    contract = (
        db.query(Contracts)
        .filter(Contracts.id == ncr.contract_id, Contracts.company_id == company_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=403, detail="해당 NCR에 접근할 수 없습니다.")
    return ncr


@router.get("", response_model=List[NcrListItem])
def list_company_ncrs(
    contract_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """자사 계약에 발행된 NCR 목록."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)

    q = (
        db.query(AuditNcrs)
        .join(Contracts, Contracts.id == AuditNcrs.contract_id)
        .filter(Contracts.company_id == cid)
    )
    if contract_id is not None:
        q = q.filter(AuditNcrs.contract_id == contract_id)
    rows = q.order_by(AuditNcrs.id.desc()).limit(200).all()

    out: List[NcrListItem] = []
    for r in rows:
        ev = _parse_evidence(r.ca_evidence)
        out.append(
            NcrListItem(
                id=r.id,
                contract_id=r.contract_id,
                clause_id=r.clause_id,
                std_code=r.std_code,
                grade=r.grade,
                finding=r.finding,
                requirement=r.requirement,
                due_date=r.due_date.isoformat() if r.due_date else None,
                status=r.status,
                correction=r.correction,
                corrective_action=r.corrective_action,
                cause=r.cause,
                ca_submitted_at=r.ca_submitted_at.isoformat() if r.ca_submitted_at else None,
                evidence_file=ev.get("file_name") or ev.get("file_path"),
            )
        )
    return out


@router.post("/{ncr_id}/action", response_model=NcrActionResponse)
async def submit_ncr_action(
    ncr_id: int,
    correction: str = Form(..., description="즉각시정"),
    corrective_action: str = Form(..., description="시정조치 계획"),
    cause: Optional[str] = Form(None, description="원인분석"),
    note: Optional[str] = Form(None, description="증빙 설명"),
    file: Optional[UploadFile] = File(None, description="개선 증빙 파일"),
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업 시정조치 계획/증빙 제출 — PENDING → ACTION_SUBMITTED."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    ncr = _owned_ncr(db, ncr_id, cid)

    if ncr.status not in _ACTIONABLE and ncr.status != "ACTION_SUBMITTED":
        raise HTTPException(
            status_code=400,
            detail=f"현재 상태({ncr.status})에서는 시정조치를 제출할 수 없습니다.",
        )

    now = datetime.utcnow()
    evidence: dict = _parse_evidence(ncr.ca_evidence)
    evidence["note"] = (note or evidence.get("note") or "").strip() or None

    saved_name: Optional[str] = None
    if file and file.filename:
        ext = Path(file.filename).suffix.lower() or ".bin"
        if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".zip"}:
            raise HTTPException(status_code=400, detail="허용되지 않는 파일 형식입니다.")
        folder = _upload_root() / "ncr" / str(ncr_id)
        folder.mkdir(parents=True, exist_ok=True)
        saved_name = f"{uuid.uuid4().hex}{ext}"
        dest = folder / saved_name
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")
        dest.write_bytes(content)
        evidence["file_path"] = f"ncr/{ncr_id}/{saved_name}"
        evidence["file_name"] = file.filename
        evidence["uploaded_at"] = now.isoformat()

    ncr.correction = correction.strip()
    ncr.corrective_action = corrective_action.strip()
    if cause is not None:
        ncr.cause = cause.strip()
    ncr.ca_evidence = json.dumps(evidence, ensure_ascii=False)
    ncr.ca_submitted_at = now
    ncr.status = "ACTION_SUBMITTED"
    ncr.updated_at = now

    db.commit()
    db.refresh(ncr)

    return NcrActionResponse(
        success=True,
        ncr_id=ncr.id,
        status=ncr.status,
        message="시정조치가 제출되었습니다.",
        evidence_file=saved_name or evidence.get("file_name"),
    )
