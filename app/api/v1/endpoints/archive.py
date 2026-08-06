"""결과보관함(Archive) — 심사 4대 필수 PDF 조회/다운로드."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.config import settings
from app.core.security import CurrentUser, get_current_user
from app.models.audit import AuditDocuments
from app.models.contract import Contracts

router = APIRouter(prefix="/user/archive", tags=["User Archive"])

# 4대 필수 문서 타입 매핑 (저장 doc_type → 표시)
REQUIRED_DOCS = [
    {"key": "contract", "label": "계약서", "aliases": {"contract", "계약서", "cert_contract", "agreement"}},
    {"key": "audit_note", "label": "심사노트", "aliases": {"audit_note", "note", "심사노트", "audit_notes"}},
    {"key": "report", "label": "결과보고서", "aliases": {"report", "audit_report", "결과보고서", "result_report"}},
    {"key": "certificate", "label": "ISO 인증서", "aliases": {"certificate", "cert", "인증서", "iso_certificate"}},
]


class ArchiveDocumentItem(BaseModel):
    key: str
    label: str
    issued: bool
    badge: str
    document_id: Optional[int] = None
    doc_type: Optional[str] = None
    title: Optional[str] = None
    file_path: Optional[str] = None
    download_url: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[str] = None


class ArchiveDocumentsResponse(BaseModel):
    audit_id: int
    company_id: int
    contract_no: Optional[str] = None
    status: Optional[str] = None
    documents: List[ArchiveDocumentItem] = Field(default_factory=list)


class ArchiveAuditItem(BaseModel):
    audit_id: int
    contract_no: Optional[str] = None
    cb_id: int
    audit_type: Optional[str] = None
    standards: Optional[str] = None
    status: Optional[str] = None
    issued_count: int = 0
    required_count: int = 4


def _upload_root() -> Path:
    root = Path(getattr(settings, "UPLOAD_DIR", "") or "").expanduser()
    if not root or str(root) in {".", ""}:
        root = Path(__file__).resolve().parents[4] / "uploads"
    return root


def _resolve_file(file_path: str) -> Path:
    raw = Path(file_path)
    if raw.is_absolute():
        return raw
    return _upload_root() / file_path


def _match_required(doc_type: Optional[str]) -> Optional[dict]:
    if not doc_type:
        return None
    low = doc_type.strip().lower()
    for item in REQUIRED_DOCS:
        if low in item["aliases"] or low == item["key"]:
            return item
    return None


def _owned_contract(db: Session, audit_id: int, company_id: int) -> Contracts:
    row = (
        db.query(Contracts)
        .filter(Contracts.id == audit_id, Contracts.company_id == company_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="심사건(계약)을 찾을 수 없습니다.")
    return row


@router.get("/audits", response_model=List[ArchiveAuditItem])
def list_company_audits(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업의 심사건(contracts) 목록 — 결과보관함 선택용."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    rows = (
        db.query(Contracts)
        .filter(Contracts.company_id == cid)
        .order_by(Contracts.id.desc())
        .limit(100)
        .all()
    )
    out: List[ArchiveAuditItem] = []
    for r in rows:
        docs = (
            db.query(AuditDocuments)
            .filter(AuditDocuments.contract_id == r.id, AuditDocuments.is_visible_to_client.is_(True))
            .all()
        )
        issued = 0
        seen = set()
        for d in docs:
            meta = _match_required(d.doc_type)
            if meta and meta["key"] not in seen and d.file_path:
                seen.add(meta["key"])
                issued += 1
        out.append(
            ArchiveAuditItem(
                audit_id=r.id,
                contract_no=r.contract_id,
                cb_id=r.cb_id,
                audit_type=r.audit_type,
                standards=r.standards,
                status=r.status,
                issued_count=issued,
            )
        )
    return out


@router.get("/documents/{audit_id}", response_model=ArchiveDocumentsResponse)
def get_archive_documents(
    audit_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사건 4대 필수 PDF 발행 여부 + 다운로드 URL."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    contract = _owned_contract(db, audit_id, cid)

    rows = (
        db.query(AuditDocuments)
        .filter(
            AuditDocuments.contract_id == audit_id,
            AuditDocuments.is_visible_to_client.is_(True),
        )
        .order_by(AuditDocuments.id.desc())
        .all()
    )

    by_key: dict = {}
    for row in rows:
        meta = _match_required(row.doc_type)
        if not meta:
            continue
        key = meta["key"]
        if key in by_key:
            continue
        has_file = bool(row.file_path)
        by_key[key] = ArchiveDocumentItem(
            key=key,
            label=meta["label"],
            issued=has_file,
            badge="발행완료" if has_file else "미발행",
            document_id=row.id if has_file else None,
            doc_type=row.doc_type,
            title=row.title,
            file_path=row.file_path,
            download_url=f"/api/v1/user/archive/download/{row.id}" if has_file else None,
            mime_type=row.mime_type,
            uploaded_at=row.uploaded_at.isoformat() if row.uploaded_at else None,
        )

    documents: List[ArchiveDocumentItem] = []
    for meta in REQUIRED_DOCS:
        if meta["key"] in by_key:
            documents.append(by_key[meta["key"]])
        else:
            documents.append(
                ArchiveDocumentItem(
                    key=meta["key"],
                    label=meta["label"],
                    issued=False,
                    badge="미발행",
                )
            )

    return ArchiveDocumentsResponse(
        audit_id=audit_id,
        company_id=cid,
        contract_no=contract.contract_id,
        status=contract.status,
        documents=documents,
    )


@router.get("/download/{document_id}")
def download_archive_document(
    document_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """실제 PDF 파일 스트리밍 다운로드."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)

    doc = db.get(AuditDocuments, document_id)
    if not doc or not doc.is_visible_to_client:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

    contract = (
        db.query(Contracts)
        .filter(Contracts.id == doc.contract_id, Contracts.company_id == cid)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=403, detail="해당 문서에 접근할 수 없습니다.")

    if not doc.file_path:
        raise HTTPException(status_code=404, detail="파일이 아직 발행되지 않았습니다.")

    path = _resolve_file(doc.file_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="저장소에서 파일을 찾을 수 없습니다.")

    filename = path.name
    media = doc.mime_type or "application/pdf"
    return FileResponse(
        path=str(path),
        media_type=media,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class ArchiveYearDoc(BaseModel):
    document_id: int
    key: str
    label: str
    title: Optional[str] = None
    audit_id: int
    contract_no: Optional[str] = None
    uploaded_at: Optional[str] = None
    download_url: Optional[str] = None


class ArchiveYearGroup(BaseModel):
    year: int
    count: int = 0
    documents: List[ArchiveYearDoc] = Field(default_factory=list)


class ArchiveByYearResponse(BaseModel):
    company_id: int
    years: List[ArchiveYearGroup] = Field(default_factory=list)
    description: str = (
        "계약서, 심사노트, 심사결과보고서, 인증서를 최근 5개년 단위로 보관합니다."
    )


@router.get("/by-year", response_model=ArchiveByYearResponse)
def list_archive_by_year(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """결과보관함 — 연도별(최근 5년) 문서 그룹."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    current_year = datetime.now().year
    year_list = list(range(current_year, current_year - 5, -1))
    groups = {y: ArchiveYearGroup(year=y, count=0, documents=[]) for y in year_list}

    contracts = (
        db.query(Contracts)
        .filter(Contracts.company_id == cid)
        .order_by(Contracts.id.desc())
        .limit(200)
        .all()
    )
    contract_map = {c.id: c for c in contracts}
    if not contracts:
        return ArchiveByYearResponse(company_id=cid, years=[groups[y] for y in year_list])

    docs = (
        db.query(AuditDocuments)
        .filter(
            AuditDocuments.contract_id.in_(list(contract_map.keys())),
            AuditDocuments.is_visible_to_client.is_(True),
        )
        .order_by(AuditDocuments.id.desc())
        .all()
    )
    for doc in docs:
        meta = _match_required(doc.doc_type)
        if not meta or not doc.file_path:
            continue
        when = doc.uploaded_at or getattr(doc, "created_at", None)
        year = when.year if when else None
        if year is None:
            # fallback: contract created year if present
            contract = contract_map.get(doc.contract_id)
            created = getattr(contract, "created_at", None) if contract else None
            year = created.year if created else current_year
        if year not in groups:
            continue
        groups[year].documents.append(
            ArchiveYearDoc(
                document_id=doc.id,
                key=meta["key"],
                label=meta["label"],
                title=doc.title,
                audit_id=doc.contract_id,
                contract_no=getattr(contract_map.get(doc.contract_id), "contract_id", None),
                uploaded_at=when.isoformat() if when else None,
                download_url=f"/api/v1/user/archive/download/{doc.id}",
            )
        )
        groups[year].count = len(groups[year].documents)

    return ArchiveByYearResponse(company_id=cid, years=[groups[y] for y in year_list])
