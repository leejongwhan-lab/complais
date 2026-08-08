"""Compute audit-doc process progress from AuditDocuments.doc_status.

Does not read or write Contracts.current_stage.
Missing AuditDocuments row for a blocking step ⇒ not completed.
Soft-parallel steps (audit notes) never gate the next-step walk.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.data.audit_process_flows import FLOW_LABELS, get_process_flow
from app.models.audit import AuditDocuments
from app.models.contract import Contracts
from app.models.enums import AuditDocumentsDocStatus

_COMPLETED = {
    AuditDocumentsDocStatus.COMPLETED.value,
    "completed",
    "complete",
    "done",
    "signed",  # legacy/doc signed sometimes used as terminal
}


def _is_completed(doc_status: Optional[str]) -> bool:
    if not doc_status:
        return False
    return str(doc_status).strip().lower() in _COMPLETED


def _status_map_for_contract(db: Session, contract_id: int) -> Dict[str, Dict[str, Any]]:
    """doc_type → best row summary (prefer completed, else latest id)."""
    rows = (
        db.query(AuditDocuments)
        .filter(AuditDocuments.contract_id == int(contract_id))
        .order_by(AuditDocuments.id.desc())
        .all()
    )
    by_type: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        dt = (row.doc_type or "").strip()
        if not dt:
            continue
        completed = _is_completed(row.doc_status)
        existing = by_type.get(dt)
        if existing and existing.get("completed") and not completed:
            continue
        if existing and existing.get("completed") and completed:
            continue  # keep first (newest) completed
        by_type[dt] = {
            "document_id": int(row.id),
            "doc_type": dt,
            "doc_subtype": row.doc_subtype,
            "doc_status": row.doc_status or "pending",
            "status": row.status,
            "title": row.title,
            "completed": completed,
        }
    return by_type


def build_audit_docs_progress(
    db: Session,
    *,
    contract_id: int,
) -> Dict[str, Any]:
    """Return process flow + per-step statuses + next incomplete blocking step."""
    contract = db.get(Contracts, int(contract_id))
    if not contract:
        return {
            "contract_id": int(contract_id),
            "found": False,
            "audit_type": None,
            "flow_key": None,
            "flow_label": None,
            "steps": [],
            "next_step": None,
            "all_completed": False,
        }

    audit_type = (contract.audit_type or "initial").strip()
    flow_key, flow_steps = get_process_flow(audit_type)
    status_map = _status_map_for_contract(db, int(contract.id))

    steps_out: List[Dict[str, Any]] = []
    next_step: Optional[Dict[str, Any]] = None

    for step in flow_steps:
        parallel = bool(step.get("parallel"))
        doc_type = (step.get("doc_type") or "").strip()
        row = status_map.get(doc_type) if doc_type else None

        if parallel:
            # Soft-parallel: informational only — never gates next_step
            completed = False
            doc_status = "parallel"
            document_id = None
        elif row:
            completed = bool(row.get("completed"))
            doc_status = row.get("doc_status") or "pending"
            document_id = row.get("document_id")
        else:
            # No AuditDocuments row yet ⇒ not completed
            completed = False
            doc_status = "pending"
            document_id = None

        item = {
            "key": step["key"],
            "title": step["title"],
            "slug": step.get("slug"),
            "doc_type": doc_type or None,
            "path": step.get("path"),
            "parallel": parallel,
            "open_mode": step.get("open_mode") or "doc",
            "portal_tab": step.get("portal_tab"),
            "doc_status": doc_status,
            "completed": completed,
            "document_id": document_id,
            "is_next": False,
        }
        if not parallel and not completed and next_step is None:
            item["is_next"] = True
            next_step = dict(item)
        steps_out.append(item)

    blocking = [s for s in steps_out if not s.get("parallel")]
    all_completed = bool(blocking) and all(s.get("completed") for s in blocking)

    return {
        "contract_id": int(contract.id),
        "contract_no": contract.contract_id,
        "found": True,
        "audit_type": audit_type,
        "flow_key": flow_key,
        "flow_label": FLOW_LABELS.get(flow_key, flow_key),
        "steps": steps_out,
        "next_step": next_step,
        "all_completed": all_completed,
    }
