"""CB Portal HTMX HTML partials — master-detail panes (CB role)."""
from __future__ import annotations

import html
import logging
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.api.v1.endpoints.cb_portal import _cb_related_company_ids
from app.services.company_held_certs import list_company_held_standards
from app.core.security import CurrentUser, require_cb_portal_user
from app.db.session import get_db
from app.models.company import Companies
from app.models.contract import Contracts
from app.models.enterprise_audit_application import Application

router = APIRouter(tags=["CB Portal HTMX"])
logger = logging.getLogger(__name__)

PAGINATION_WINDOW = 5


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _corp_type(c: Companies) -> str:
    et = (getattr(c, "entity_type", None) or "").strip()
    if et in {"법인", "개인"}:
        return et
    return "법인" if (c.corp_no or "").strip() else "개인"


def _pagination_window(current: int, total_pages: int, window: int = PAGINATION_WINDOW) -> tuple[int, int]:
    total_pages = max(1, total_pages)
    current = min(max(1, current), total_pages)
    start = max(1, current - (window // 2))
    end = min(total_pages, start + window - 1)
    start = max(1, end - window + 1)
    return start, end


def _render_pagination_html(
    *,
    page: int,
    total_pages: int,
    base_url: str,
    hx_target: str,
    container_id: str,
    limit: int,
    keyword: str = "",
    window: int = PAGINATION_WINDOW,
) -> str:
    total_pages = max(1, total_pages)
    current = min(max(1, page), total_pages)
    start, end = _pagination_window(current, total_pages, window)
    kw_q = html.escape(keyword or "", quote=True)

    def page_url(p: int) -> str:
        return f"{base_url}?page={p}&limit={limit}&keyword={kw_q}"

    def page_btn(
        p: int,
        label: str | None = None,
        *,
        active: bool = False,
        nav: bool = False,
        disabled: bool = False,
    ) -> str:
        classes = ["page-btn"]
        if nav:
            classes.append("nav-btn")
        if active:
            classes.append("active")
        cls = " ".join(classes)
        text_label = label if label is not None else str(p)
        if disabled:
            return f'<button type="button" class="{cls}" disabled>{text_label}</button>'
        return (
            f'<button type="button" class="{cls}" '
            f'hx-get="{page_url(p)}" hx-target="{hx_target}" hx-swap="innerHTML">{text_label}</button>'
        )

    parts: list[str] = []
    parts.append(page_btn(current - 1, "‹", nav=True, disabled=current <= 1))
    page_nums: list[int] = []
    if start > 1:
        page_nums.append(1)
    for p in range(start, end + 1):
        if p not in page_nums:
            page_nums.append(p)
    if end < total_pages and total_pages not in page_nums:
        page_nums.append(total_pages)

    prev_p = None
    for p in page_nums:
        if prev_p is not None and p > prev_p + 1:
            parts.append('<button type="button" class="page-btn nav-btn" disabled>…</button>')
        parts.append(page_btn(p, active=(p == current)))
        prev_p = p

    parts.append(page_btn(current + 1, "›", nav=True, disabled=current >= total_pages))
    return f'<div class="pagination-container" id="{container_id}">{"".join(parts)}</div>'


def _cb_id(user: CurrentUser) -> Optional[int]:
    return int(user.cb_id) if user.cb_id is not None else None


def _empty_detail(msg: str = "왼쪽 목록에서 항목을 선택하세요.") -> str:
    return (
        f'<div class="detail-empty">'
        f'<p class="muted">{_esc(msg)}</p></div>'
    )


def _list_item(
    *,
    tab: str,
    item_id: int,
    title: str,
    subtitle: str,
    meta: str = "",
    active: bool = False,
) -> str:
    cls = "master-list-item" + (" is-active" if active else "")
    target = f"#detail-pane-{_esc(tab)}"
    meta_html = ""
    if meta:
        meta_html = f'<span class="meta">{_esc(meta)}</span>'
    return (
        f'<button type="button" class="{cls}" '
        f'data-id="{item_id}" '
        f'hx-get="/cb-portal/partials/detail?tab={_esc(tab)}&id={item_id}" '
        f'hx-target="{target}" hx-swap="innerHTML" '
        f'hx-push-url="false">'
        f"<strong>{_esc(title)}</strong>"
        f"<small>{_esc(subtitle)}</small>"
        f"{meta_html}"
        f"</button>"
    )


@router.get("/list", response_class=HTMLResponse)
def htmx_list(
    tab: str = Query("applications"),
    status: Optional[str] = Query(None),
    auditor_id: Optional[int] = Query(None),
    request_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    tab = (tab or "applications").strip()
    cb_id = _cb_id(current_user)
    if cb_id is None:
        return HTMLResponse('<div class="muted">CB 스코프가 없습니다.</div>')

    try:
        if tab in {"applications", "proposals"}:
            return HTMLResponse(
                _render_applications_list(
                    db, cb_id, status=status, highlight=None, tab=tab
                )
            )
        if tab in {"contracts_pre", "contracts"}:
            return HTMLResponse(
                _render_contracts_list(db, cb_id, status=status or "signed")
            )
        if tab == "projects":
            return HTMLResponse(
                _render_contracts_list(db, cb_id, status=status or "in_progress")
            )
        if tab == "verification":
            return HTMLResponse(
                _render_contracts_list(
                    db, cb_id, status=status or "audit_completed", verification=True
                )
            )
        if tab == "cpd_mgr":
            return HTMLResponse(
                _render_cpd_list(
                    db, cb_id, auditor_id=auditor_id, request_id=request_id
                )
            )
        return HTMLResponse(
            f'<div class="muted">목록 준비 중: {_esc(tab)}</div>'
        )
    except Exception:
        logger.exception("cb portal list partial failed tab=%s", tab)
        try:
            db.rollback()
        except Exception:
            pass
        return HTMLResponse('<div class="muted">목록을 불러오지 못했습니다.</div>')


@router.get("/detail", response_class=HTMLResponse)
def htmx_detail(
    tab: str = Query("applications"),
    id: int = Query(..., alias="id"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    tab = (tab or "applications").strip()
    cb_id = _cb_id(current_user)
    try:
        if tab in {"applications", "proposals"}:
            return HTMLResponse(_render_application_detail(db, cb_id, id))
        if tab in {"contracts_pre", "contracts", "projects"}:
            return HTMLResponse(_render_contract_detail(db, cb_id, id, readonly_docs=False))
        if tab == "verification":
            return HTMLResponse(
                _render_contract_detail(db, cb_id, id, readonly_docs=True, verification=True)
            )
        if tab == "cpd_mgr":
            return HTMLResponse(_render_cpd_detail(db, cb_id, id))
        return HTMLResponse(_empty_detail(f"상세 준비 중: {tab}"))
    except Exception:
        logger.exception("cb portal detail partial failed tab=%s id=%s", tab, id)
        try:
            db.rollback()
        except Exception:
            pass
        return HTMLResponse(_empty_detail("상세를 불러오지 못했습니다."))


def _render_applications_list(
    db: Session,
    cb_id: Optional[int],
    *,
    status: Optional[str],
    highlight: Optional[int],
    tab: str = "applications",
) -> str:
    q = db.query(Application, Companies.name).outerjoin(
        Companies, Companies.id == Application.enterprise_id
    )
    if cb_id is not None:
        q = q.filter(Application.cb_id == cb_id)
    # map UI status → EAA enum
    status_map = {
        "submitted": "SUBMITTED",
        "reviewing": "REVIEWING",
        "reviewed": "REVIEWING",
        "proposed": "PROPOSED",
        "contracted": "CONTRACTED",
    }
    if status:
        mapped = status_map.get(status.lower(), status.upper())
        q = q.filter(Application.status == mapped)
    rows = q.order_by(Application.application_id.desc()).limit(100).all()
    if not rows:
        return '<div class="muted">신청 건이 없습니다.</div>'
    parts = ['<div class="master-list">']
    for eapp, company_name in rows:
        parts.append(
            _list_item(
                tab=tab,
                item_id=int(eapp.application_id),
                title=company_name or f"기업 #{eapp.enterprise_id}",
                subtitle=f"#{eapp.application_id} · {eapp.status}",
                meta=str(eapp.audit_type or ""),
                active=highlight == eapp.application_id,
            )
        )
    parts.append("</div>")
    return "".join(parts)


def _render_application_detail(db: Session, cb_id: Optional[int], app_id: int) -> str:
    q = db.query(Application, Companies.name).outerjoin(
        Companies, Companies.id == Application.enterprise_id
    ).filter(Application.application_id == app_id)
    if cb_id is not None:
        q = q.filter(Application.cb_id == cb_id)
    row = q.first()
    if not row:
        return _empty_detail("신청을 찾을 수 없습니다.")
    eapp, company_name = row
    standards = eapp.applied_standards
    if isinstance(standards, list):
        std_label = ", ".join(str(x) for x in standards)
    else:
        std_label = str(standards or "—")
    md = eapp.final_audit_md if eapp.final_audit_md is not None else (
        (eapp.base_stage1_md or 0) + (eapp.base_stage2_md or 0)
    )
    return f"""
    <div class="detail-card">
      <div class="panel-header">
        <h3 style="font: var(--font-h3); margin: 0;">{_esc(company_name or "신청 상세")}</h3>
        <span class="panel-count">{_esc(eapp.status)}</span>
      </div>
      <dl class="kv-grid">
        <dt>신청 ID</dt><dd>{eapp.application_id}</dd>
        <dt>심사 유형</dt><dd>{_esc(eapp.audit_type)}</dd>
        <dt>표준</dt><dd>{_esc(std_label)}</dd>
        <dt>IAF</dt><dd>{_esc(eapp.iaf_scope_code)}</dd>
        <dt>종업원 수</dt><dd>{eapp.active_employee_count}</dd>
        <dt>복잡도</dt><dd>{_esc(eapp.complexity_level)}</dd>
        <dt>기준 MD</dt><dd>S1 {eapp.base_stage1_md} / S2 {eapp.base_stage2_md}</dd>
        <dt>최종 MD</dt><dd>{_esc(md)}</dd>
        <dt>가감 비율</dt><dd>{_esc(eapp.cb_adjustment_ratio)}%</dd>
      </dl>
      <div class="detail-actions">
        <a class="primary" href="/cb-portal/review.html?id={eapp.application_id}">MD 검토</a>
        <a class="btn ghost" href="/cb-portal/assign.html?id={eapp.application_id}">심사원 배정</a>
      </div>
      <p class="hint">제안/결제 단계에서는 MD 산출·가배정을 우측에서 처리합니다.</p>
    </div>
    """


def _render_contracts_list(
    db: Session,
    cb_id: Optional[int],
    *,
    status: Optional[str],
    verification: bool = False,
) -> str:
    q = db.query(Contracts)
    if cb_id is not None:
        q = q.filter(Contracts.cb_id == cb_id)
    if status:
        st = status.lower()
        if st == "audit_completed":
            q = q.filter(
                Contracts.status.in_(
                    ["note_submitted", "report_ready", "audit_completed", "in_progress"]
                )
            )
        elif st == "approved":
            q = q.filter(
                or_(
                    Contracts.status.in_(["certified", "closed"]),
                    Contracts.verification_status == "approved",
                )
            )
        elif st == "signed":
            q = q.filter(
                Contracts.status.in_(
                    ["signed", "client_signed", "scheduled", "SENT", "SIGNED"]
                )
            )
        else:
            q = q.filter(Contracts.status == status)
    rows = q.order_by(Contracts.id.desc()).limit(100).all()
    if not rows:
        return '<div class="muted">계약/프로젝트가 없습니다.</div>'
    tab = "verification" if verification else "contracts_pre"
    parts = ['<div class="master-list">']
    for c in rows:
        parts.append(
            _list_item(
                tab=tab,
                item_id=int(c.id),
                title=c.contract_id or f"계약 #{c.id}",
                subtitle=f"{_esc(c.status)} · MD {c.total_md}",
                meta=_esc(c.standards)[:40] if c.standards else "",
            )
        )
    parts.append("</div>")
    return "".join(parts)


def _render_contract_detail(
    db: Session,
    cb_id: Optional[int],
    contract_id: int,
    *,
    readonly_docs: bool,
    verification: bool = False,
) -> str:
    q = db.query(Contracts).filter(Contracts.id == contract_id)
    if cb_id is not None:
        q = q.filter(Contracts.cb_id == cb_id)
    c = q.first()
    if not c:
        return _empty_detail("계약을 찾을 수 없습니다.")

    ro = " readonly disabled" if readonly_docs else ""
    actions = ""
    if verification or readonly_docs:
        actions = f"""
        <div class="detail-actions">
          <button type="button" class="btn ghost" data-cb-action="supplement"
                  data-contract-id="{c.id}">보완 요청</button>
          <button type="button" class="primary" data-cb-action="approve-verify"
                  data-contract-id="{c.id}">검증 심의서 승인</button>
          <button type="button" class="primary" data-cb-action="issue-cert"
                  data-contract-id="{c.id}">인증서 PDF 발급</button>
        </div>
        <p class="hint">ISO/IEC 17021: 심사원 노트·보고서·NCR는 읽기 전용입니다. CB는 보완/승인/발급만 가능합니다.</p>
        """
    return f"""
    <div class="detail-card">
      <div class="panel-header">
        <h3 style="font: var(--font-h3); margin: 0;">{_esc(c.contract_id)}</h3>
        <span class="panel-count">{_esc(c.status)}</span>
      </div>
      <dl class="kv-grid">
        <dt>계약 ID</dt><dd>{c.id}</dd>
        <dt>표준</dt><dd>{_esc(c.standards)}</dd>
        <dt>총 MD</dt><dd>{_esc(c.total_md)}</dd>
        <dt>계약금액</dt><dd>{_esc(c.agreed_amount)}</dd>
        <dt>검증상태</dt><dd>{_esc(c.verification_status or "—")}</dd>
        <dt>기간</dt><dd>{_esc(c.audit_period_start)} ~ {_esc(c.audit_period_end)}</dd>
      </dl>
      <label class="form-label">심사원 노트 / 보고서 (읽기 전용)</label>
      <textarea class="form-input" rows="4"{ro} placeholder="제출된 심사 노트·보고서"></textarea>
      <label class="form-label" style="margin-top:12px;">NCR 입력 (읽기 전용)</label>
      <textarea class="form-input" rows="3"{ro} placeholder="NCR 내용"></textarea>
      {actions}
    </div>
    """


def _render_cpd_list(
    db: Session,
    cb_id: Optional[int],
    *,
    auditor_id: Optional[int],
    request_id: Optional[int],
) -> str:
    sql = """
        SELECT m.id, m.auditor_id, m.status, m.apply_grade, a.name
        FROM auditor_cb_memberships m
        LEFT JOIN auditors a ON a.id = m.auditor_id
        WHERE m.status IN ('requested','under_review','pending')
    """
    params: dict = {}
    if cb_id is not None:
        sql += " AND m.cb_id = :cb_id"
        params["cb_id"] = cb_id
    if auditor_id:
        sql += " AND m.auditor_id = :auditor_id"
        params["auditor_id"] = auditor_id
    sql += " ORDER BY m.id DESC LIMIT 100"
    rows = db.execute(text(sql), params).fetchall()
    if not rows:
        return '<div class="muted">대기 중인 자격/코드 신청이 없습니다.</div>'
    parts = ['<div class="master-list">']
    for r in rows:
        mid, aid, st, grade, name = r
        title = name or f"심사원 #{aid}"
        parts.append(
            _list_item(
                tab="cpd_mgr",
                item_id=int(mid),
                title=title,
                subtitle=f"신청 #{mid} · {_esc(st)}",
                meta=_esc(grade or ""),
                active=request_id is not None and int(mid) == int(request_id),
            )
        )
    parts.append("</div>")
    if request_id:
        parts.append(
            f'<div hx-get="/cb-portal/partials/detail?tab=cpd_mgr&id={int(request_id)}" '
            f'hx-trigger="load once" hx-target="#detail-pane-cpd_mgr" hx-swap="innerHTML"></div>'
        )
    return "".join(parts)


def _render_cpd_detail(db: Session, cb_id: Optional[int], membership_id: int) -> str:
    sql = """
        SELECT m.id, m.auditor_id, m.status, m.apply_grade, m.employment_type,
               m.apply_message, a.name
        FROM auditor_cb_memberships m
        LEFT JOIN auditors a ON a.id = m.auditor_id
        WHERE m.id = :mid
    """
    params: dict = {"mid": membership_id}
    if cb_id is not None:
        sql += " AND m.cb_id = :cb_id"
        params["cb_id"] = cb_id
    r = db.execute(text(sql), params).first()
    if not r:
        return _empty_detail("자격 신청을 찾을 수 없습니다.")
    mid, aid, st, grade, emp, msg, name = r
    title = name or f"심사원 #{aid}"
    return f"""
    <div class="detail-card">
      <div class="panel-header">
        <h3 style="font: var(--font-h3); margin: 0;">{_esc(title)}</h3>
        <span class="panel-count">{_esc(st)}</span>
      </div>
      <dl class="kv-grid">
        <dt>신청 ID</dt><dd>{mid}</dd>
        <dt>심사원 ID</dt><dd>{aid}</dd>
        <dt>신청 등급</dt><dd>{_esc(grade or "—")}</dd>
        <dt>고용형태</dt><dd>{_esc(emp)}</dd>
        <dt>신청 메시지</dt><dd>{_esc(msg or "—")}</dd>
      </dl>
      <div class="detail-actions">
        <button type="button" class="primary" data-cb-action="approve-membership"
                data-membership-id="{mid}" data-auditor-id="{aid}">승인</button>
        <button type="button" class="btn ghost" data-cb-action="reject-membership"
                data-membership-id="{mid}">반려</button>
      </div>
    </div>
    """


@router.get("/companies", response_class=HTMLResponse)
def htmx_cb_companies(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_cb_portal_user),
):
    """CB 고객사현황 — admin 기업 테이블과 동일 컬럼/스타일 (스코프 = 소속 CB)."""
    cb_id = _cb_id(current_user)
    if cb_id is None:
        return HTMLResponse(
            '<div class="table-responsive"><table class="data-table admin-data-table">'
            '<tbody><tr><td style="text-align:center;color:var(--font-tertiary);">'
            "CB 스코프가 없습니다.</td></tr></tbody></table></div>"
        )
    try:
        company_ids = _cb_related_company_ids(db, cb_id)
        if not company_ids:
            empty = (
                '<tr><td colspan="9" style="text-align:center;color:var(--font-tertiary);">'
                "등록된 고객사가 없습니다.</td></tr>"
            )
            oob = '<span id="cb-company-total-count" hx-swap-oob="true">0</span>'
            return HTMLResponse(
                f"""{oob}
<div class="table-responsive">
  <table class="data-table admin-data-table text-nowrap companies-table">
    <thead>
      <tr>
        <th style="width:5%;">순번</th>
        <th class="col-company-name">기업명</th>
        <th style="width:12%;">사업자등록번호</th>
        <th style="width:8%;">법인(개인)</th>
        <th style="width:9%;">대표자명</th>
        <th style="width:18%;">보유 표준 (인정/인증)</th>
        <th>주소</th>
        <th style="width:8%;">홈페이지</th>
        <th style="width:8%;">관리</th>
      </tr>
    </thead>
    <tbody id="cb-company-table-body">{empty}</tbody>
  </table>
</div>
<div class="pagination-container" id="cb-company-pagination"></div>
"""
            )

        q = db.query(Companies).filter(Companies.id.in_(company_ids))
        if keyword and keyword.strip():
            like = f"%{keyword.strip()}%"
            q = q.filter(
                (Companies.name.ilike(like))
                | (Companies.biz_no.ilike(like))
                | (Companies.name_en.ilike(like))
            )
        total = q.count()
        offset = (page - 1) * limit
        rows = q.order_by(Companies.id.desc()).offset(offset).limit(limit).all()

        body_rows = []
        for i, c in enumerate(rows):
            cid = c.id
            seq = offset + i + 1
            name = c.name or ""
            corp = _corp_type(c)
            website = (c.website or "").strip()
            if website and not website.startswith("http"):
                website = f"http://{website}"
            web_cell = (
                f'<a href="{_esc(website)}" target="_blank" rel="noopener" class="text-decoration-none">방문</a>'
                if website
                else "-"
            )
            addr = getattr(c, "address", None) or ""
            try:
                held = list_company_held_standards(
                    db, int(cid), cb_id=cb_id, display_mode="cb"
                )
            except Exception:
                held = []
            held_bits = []
            for h in held[:6]:
                label = h.get("label") or h.get("initial") or h.get("standard_code") or ""
                ab = h.get("ab_code") or "—"
                cb_disp = h.get("cb_initial") or h.get("cb_name") or "—"
                held_bits.append(f"{label} (AB:{ab} / CB:{cb_disp})")
            held_cell = "<br>".join(_esc(x) for x in held_bits) if held_bits else "—"
            if len(held) > 6:
                held_cell += f"<br><span class='muted'>+{len(held) - 6}</span>"
            body_rows.append(
                f"""<tr>
          <td>{seq}</td>
          <td class="col-company-name fw-bold" title="{_esc(name)}">{_esc(name)}</td>
          <td>{_esc(c.biz_no or "-")}</td>
          <td>{_esc(corp)}</td>
          <td>{_esc(c.ceo_name or "-")}</td>
          <td style="font-size:11px;line-height:1.45;white-space:normal;min-width:160px">{held_cell}</td>
          <td title="{_esc(addr)}">{_esc(addr or "-")}</td>
          <td>{web_cell}</td>
          <td><button type="button" class="btn-detail" onclick="openCbCompanyDetail({cid})">상세정보</button></td>
        </tr>"""
            )
        if not body_rows:
            body_rows = [
                '<tr><td colspan="9" style="text-align:center;color:var(--font-tertiary);">검색 결과가 없습니다.</td></tr>'
            ]

        pages = max(1, ceil(total / limit)) if total else 1
        pagination = (
            _render_pagination_html(
                page=page,
                total_pages=pages,
                base_url="/cb-portal/partials/companies",
                hx_target="#cb-company-htmx-panel",
                container_id="cb-company-pagination",
                limit=limit,
                keyword=keyword or "",
            )
            if total
            else '<div class="pagination-container" id="cb-company-pagination"></div>'
        )

        oob_count = f'<span id="cb-company-total-count" hx-swap-oob="true">{total}</span>'
        return HTMLResponse(
            f"""{oob_count}
<div class="table-responsive">
  <table class="data-table admin-data-table text-nowrap companies-table">
    <thead>
      <tr>
        <th style="width:5%;">순번</th>
        <th class="col-company-name">기업명</th>
        <th style="width:12%;">사업자등록번호</th>
        <th style="width:8%;">법인(개인)</th>
        <th style="width:9%;">대표자명</th>
        <th style="width:18%;">보유 표준 (인정/인증)</th>
        <th>주소</th>
        <th style="width:8%;">홈페이지</th>
        <th style="width:8%;">관리</th>
      </tr>
    </thead>
    <tbody id="cb-company-table-body">{"".join(body_rows)}</tbody>
  </table>
</div>
{pagination}
"""
        )
    except Exception:
        logger.exception("cb portal companies partial failed")
        try:
            db.rollback()
        except Exception:
            pass
        return HTMLResponse(
            '<div class="table-responsive"><table class="data-table"><tbody>'
            '<tr><td style="text-align:center;color:var(--sec-red);">'
            "고객사 목록을 불러오지 못했습니다.</td></tr></tbody></table></div>"
        )
