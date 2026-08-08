"""Certification-audit process paths — single config for portal “다음 할 일”.

Source of truth for *order* only. Progress is derived from
`AuditDocuments.doc_status` (see `app.services.audit_process_progress`).
Do not sync `Contracts.current_stage`.

Application type on the contract is stored as `Contracts.audit_type`
(copied from `CertificationApplications.application_type` on approve).

Audit notes (“심사노트”) are soft-parallel: shown in the flow and linked
to the portal reports tab, but they do **not** block advancing to the
next document step.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Flow keys used in PROCESS_FLOWS
FLOW_INITIAL = "initial"
FLOW_SURVEILLANCE = "surveillance"
FLOW_RECERT = "recert"
FLOW_TRANSFER = "transfer"
FLOW_SPECIAL = "special"

# Contracts.audit_type / CertificationApplications.application_type → flow key
_TYPE_ALIASES: Dict[str, str] = {
    "initial": FLOW_INITIAL,
    "최초": FLOW_INITIAL,
    "최초심사": FLOW_INITIAL,
    "surveillance": FLOW_SURVEILLANCE,
    "surveillance1": FLOW_SURVEILLANCE,
    "surveillance2": FLOW_SURVEILLANCE,
    "sa1": FLOW_SURVEILLANCE,
    "sa2": FLOW_SURVEILLANCE,
    "사후": FLOW_SURVEILLANCE,
    "사후심사": FLOW_SURVEILLANCE,
    "recert": FLOW_RECERT,
    "recertification": FLOW_RECERT,
    "renewal": FLOW_RECERT,
    "갱신": FLOW_RECERT,
    "갱신심사": FLOW_RECERT,
    "transfer": FLOW_TRANSFER,
    "전환": FLOW_TRANSFER,
    "전환심사": FLOW_TRANSFER,
    "special": FLOW_SPECIAL,
    "특별": FLOW_SPECIAL,
    "특별심사": FLOW_SPECIAL,
    # no dedicated flow yet — treat like initial (plan → … → decision)
    "scope_extension": FLOW_INITIAL,
}


def _doc(
    key: str,
    *,
    title: str,
    slug: str,
    doc_type: str,
    path: str,
    parallel: bool = False,
    open_mode: str = "doc",
    portal_tab: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one flow step.

    open_mode:
      - doc: open /audit-docs/{slug} in portal viewer
      - portal_tab: switch to portal_tab (e.g. reports for audit notes)
    parallel=True → soft-parallel (link only; does not gate next-step)
    """
    return {
        "key": key,
        "title": title,
        "slug": slug,
        "doc_type": doc_type,
        "path": path,
        "parallel": parallel,
        "open_mode": open_mode,
        "portal_tab": portal_tab,
    }


# Shared step builders (doc_type matches demo_audit_docs.DOC_PAGES)
PLAN = _doc(
    "plan",
    title="심사계획서",
    slug="plan",
    doc_type="audit_plan",
    path="/audit-docs/plan",
)
STAGE1_READINESS = _doc(
    "stage1_readiness",
    title="1단계 서류준비성 검토",
    slug="stage1_readiness",
    doc_type="stage1_readiness",
    path="/audit-docs/stage1_readiness",
)
STAGE1_REPORT = _doc(
    "stage1_report",
    title="1단계 심사보고서",
    slug="stage1_report",
    doc_type="stage1_report",
    path="/audit-docs/stage1_report",
)
# Soft-parallel: portal reports/notes — not an AuditDocuments gate
AUDIT_NOTES = _doc(
    "audit_notes",
    title="심사노트",
    slug="notes",
    doc_type="",  # not matched against AuditDocuments
    path="/auditor-portal?tab=reports",
    parallel=True,
    open_mode="portal_tab",
    portal_tab="reports",
)
STAGE2_REPORT = _doc(
    "stage2_report",
    title="2단계 심사보고서",
    slug="stage2_report",
    doc_type="stage2_report",
    path="/audit-docs/stage2_report",
)
STAGE2_REPORT_SURVEILLANCE = _doc(
    "stage2_report",
    title="사후심사 보고서",
    slug="stage2_report",
    doc_type="stage2_report",
    path="/audit-docs/stage2_report",
)
RECERT_SET = _doc(
    "recert",
    title="갱신심사 문서 세트",
    slug="recert",
    doc_type="recert_audit",
    path="/audit-docs/recert",
)
TRANSFER_SET = _doc(
    "transfer",
    title="전환심사 문서 세트",
    slug="transfer",
    doc_type="transfer_audit",
    path="/audit-docs/transfer",
)
SPECIAL_SET = _doc(
    "special",
    title="특별심사 문서 세트",
    slug="special",
    doc_type="special_audit",
    path="/audit-docs/special",
)
CERT_DECISION = _doc(
    "cert_decision",
    title="인증검증 심의서",
    slug="cert_decision",
    doc_type="cert_decision",
    path="/audit-docs/cert_decision",
)

PROCESS_FLOWS: Dict[str, List[Dict[str, Any]]] = {
    # initial: plan → stage1_readiness → stage1_report → (audit notes parallel)
    #          → stage2_report → cert_decision
    FLOW_INITIAL: [
        PLAN,
        STAGE1_READINESS,
        STAGE1_REPORT,
        AUDIT_NOTES,
        STAGE2_REPORT,
        CERT_DECISION,
    ],
    # surveillance: plan → stage2_report (surveillance) → cert_decision
    FLOW_SURVEILLANCE: [
        PLAN,
        STAGE2_REPORT_SURVEILLANCE,
        CERT_DECISION,
    ],
    # recert: plan → recert set → cert_decision
    FLOW_RECERT: [
        PLAN,
        RECERT_SET,
        CERT_DECISION,
    ],
    # transfer: plan → transfer set → cert_decision
    FLOW_TRANSFER: [
        PLAN,
        TRANSFER_SET,
        CERT_DECISION,
    ],
    # special: special set → cert_decision
    FLOW_SPECIAL: [
        SPECIAL_SET,
        CERT_DECISION,
    ],
}

FLOW_LABELS: Dict[str, str] = {
    FLOW_INITIAL: "최초인증",
    FLOW_SURVEILLANCE: "사후심사",
    FLOW_RECERT: "갱신심사",
    FLOW_TRANSFER: "전환심사",
    FLOW_SPECIAL: "특별심사",
}


def normalize_flow_key(audit_type: Optional[str]) -> str:
    """Map Contracts.audit_type (or application_type) → PROCESS_FLOWS key."""
    if not audit_type:
        return FLOW_INITIAL
    raw = str(audit_type).strip().lower().replace(" ", "").replace("-", "_")
    if raw in PROCESS_FLOWS:
        return raw
    compact = raw.replace("_", "")
    if compact in _TYPE_ALIASES:
        return _TYPE_ALIASES[compact]
    if raw in _TYPE_ALIASES:
        return _TYPE_ALIASES[raw]
    # try without underscores against aliases keyed without them
    for alias, flow in _TYPE_ALIASES.items():
        if alias.replace("_", "") == compact:
            return flow
    return FLOW_INITIAL


def get_process_flow(audit_type: Optional[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """Return (flow_key, ordered steps) for the given audit/application type."""
    key = normalize_flow_key(audit_type)
    steps = PROCESS_FLOWS.get(key) or PROCESS_FLOWS[FLOW_INITIAL]
    # shallow copy step dicts so callers can annotate without mutating config
    return key, [dict(s) for s in steps]
