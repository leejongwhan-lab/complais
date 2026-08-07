"""Admin HTMX HTML partials — reuses existing DB/query logic."""
from __future__ import annotations

import html
import logging
from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_admin_user
from app.models.admin import CBContract
from app.models.cb import CertificationBodies
from app.models.company import Companies
from app.services.cb_billing import ensure_default_cb_contract
from app.api.v1.endpoints.admin import _batch_scope_and_held

router = APIRouter(tags=["Admin HTMX"])
logger = logging.getLogger(__name__)

# Sliding window of page number buttons (never dump all pages)
PAGINATION_WINDOW = 5


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _corp_type(c: Companies) -> str:
    et = (getattr(c, "entity_type", None) or "").strip()
    if et in {"법인", "개인"}:
        return et
    return "법인" if (c.corp_no or "").strip() else "개인"


def _held_std_buttons(cb_id: int, held_stds: list[str]) -> str:
    """지정 이니셜만 — 배지 없이 개별 클릭 가능 평문."""
    if not held_stds:
        return "—"
    parts = []
    for ini in held_stds:
        parts.append(
            f'<button type="button" class="held-std-link" '
            f'data-cb-held="{cb_id}" data-std-initial="{_esc(ini)}" '
            f'title="{_esc(ini)} 인증수행범위">{_esc(ini)}</button>'
        )
    return f'<div class="held-std-cell">{"".join(parts)}</div>'


def _pagination_window(current: int, total_pages: int, window: int = PAGINATION_WINDOW) -> tuple[int, int]:
    """Return inclusive [start, end] page range centered on current (max `window` pages)."""
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
    """Limited-window pagination with .pagination-container / .page-btn (+ HTMX)."""
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
        text = label if label is not None else str(p)
        if disabled:
            return f'<button type="button" class="{cls}" disabled>{text}</button>'
        return (
            f'<button type="button" class="{cls}" '
            f'hx-get="{page_url(p)}" hx-target="{hx_target}" hx-swap="innerHTML">{text}</button>'
        )

    parts: list[str] = []
    parts.append(page_btn(current - 1, "‹", nav=True, disabled=current <= 1))

    # Build ordered page list: optional 1 + sliding window + optional last (deduped)
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


@router.get("/companies", response_class=HTMLResponse)
def htmx_companies(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    try:
        q = db.query(Companies)
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
            seq = offset + i + 1  # 1-based continuous across pages
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
            body_rows.append(
                f"""<tr>
          <td>{seq}</td>
          <td class="col-company-name fw-bold" title="{_esc(name)}">{_esc(name)}</td>
          <td>{_esc(c.biz_no or "-")}</td>
          <td>{_esc(corp)}</td>
          <td>{_esc(c.ceo_name or "-")}</td>
          <td title="{_esc(addr)}">{_esc(addr or "-")}</td>
          <td>{web_cell}</td>
          <td><button type="button" class="btn-detail" onclick="openDetailModal({cid})">상세정보</button></td>
        </tr>"""
            )
        if not body_rows:
            body_rows = [
                '<tr><td colspan="8" style="text-align:center;color:var(--font-tertiary);">검색 결과가 없습니다.</td></tr>'
            ]

        pages = max(1, ceil(total / limit))
        pagination = _render_pagination_html(
            page=page,
            total_pages=pages,
            base_url="/admin/partials/companies",
            hx_target="#company-htmx-panel",
            container_id="pagination",
            limit=limit,
            keyword=keyword or "",
        )

        oob_count = f'<span id="total-count" hx-swap-oob="true">{total}</span>'
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
        <th>주소</th>
        <th style="width:8%;">홈페이지</th>
        <th style="width:8%;">관리</th>
      </tr>
    </thead>
    <tbody id="company-table-body">{"".join(body_rows)}</tbody>
  </table>
</div>
{pagination}
"""
        )
    except Exception:
        logger.exception("htmx companies partial failed")
        try:
            db.rollback()
        except Exception:
            pass
        return HTMLResponse(
            '<div class="table-responsive"><table class="data-table"><tbody>'
            '<tr><td style="text-align:center;color:var(--sec-red);">'
            "기업 목록을 불러오지 못했습니다.</td></tr></tbody></table></div>"
        )


@router.get("/cb-contracts", response_class=HTMLResponse)
def htmx_cb_contracts(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=200),
    skip: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    try:
        year = datetime.utcnow().year
        q = db.query(CertificationBodies)
        if keyword and keyword.strip():
            like = f"%{keyword.strip()}%"
            q = q.filter(
                (CertificationBodies.name.ilike(like))
                | (CertificationBodies.code.ilike(like))
                | (CertificationBodies.name_en.ilike(like))
            )
        total = q.count()
        # legacy skip= support
        if skip is not None:
            offset = skip
            page = (skip // limit) + 1 if limit else 1
        else:
            offset = (page - 1) * limit

        cbs = q.order_by(CertificationBodies.id.asc()).offset(offset).limit(limit).all()
        for cb in cbs:
            ensure_default_cb_contract(db, cb, year=year)
        db.commit()

        metrics = _batch_scope_and_held(db, [cb.id for cb in cbs])
        rows_html = []
        for i, cb in enumerate(cbs):
            contract = (
                db.query(CBContract)
                .filter(CBContract.cb_id == cb.id, CBContract.contract_year == year)
                .order_by(CBContract.id.desc())
                .first()
            )
            if contract is None:
                contract = (
                    db.query(CBContract)
                    .filter(CBContract.cb_id == cb.id)
                    .order_by(CBContract.contract_year.desc(), CBContract.id.desc())
                    .first()
                )
            if contract is None:
                continue
            seq = offset + i + 1  # 1-based continuous: (page-1)*limit + index
            _scope_cnt, _held_cnt, held_stds, ab_sum = metrics.get(cb.id, (0, 0, [], ""))
            ab_display = ab_sum or (cb.accreditation_body or "") or "-"
            fee = contract.annual_base_fee
            fee_s = f"{int(fee):,}" if fee is not None else "-"
            status = cb.status or ("정상" if cb.is_active else "정지")
            held_cell = _held_std_buttons(cb.id, held_stds)
            rows_html.append(
                f"""<tr>
          <td>{seq}</td>
          <td>{_esc(cb.code or "-")}</td>
          <td class="col-cb-name fw-bold" title="{_esc(cb.name)}">{_esc(cb.name)}</td>
          <td>{_esc(status)}</td>
          <td class="col-held-std">{held_cell}</td>
          <td>{_esc(ab_display)}</td>
          <td>{_esc(fee_s)}</td>
          <td><button type="button" class="btn-detail" data-cb-detail="{cb.id}">상세정보</button></td>
        </tr>"""
            )
        if not rows_html:
            rows_html = [
                '<tr><td colspan="8" style="text-align:center;color:var(--font-tertiary);">등록된 인증기관이 없습니다.</td></tr>'
            ]

        pages = max(1, ceil(total / limit)) if limit else 1
        pagination = _render_pagination_html(
            page=page,
            total_pages=pages,
            base_url="/admin/partials/cb-contracts",
            hx_target="#cb-htmx-panel",
            container_id="cb-pagination",
            limit=limit,
            keyword=keyword or "",
        )

        oob_count = f'<span id="cb-total-count" hx-swap-oob="true">{total}</span>'
        return HTMLResponse(
            f"""{oob_count}
<div class="table-responsive">
  <table class="data-table admin-data-table text-nowrap cb-contracts-table">
    <thead>
      <tr>
        <th style="width:5%;">순번</th>
        <th style="width:9%;">인증기관 코드</th>
        <th class="col-cb-name">인증기관명</th>
        <th style="width:7%;">상태</th>
        <th class="col-held-std">보유 표준</th>
        <th style="width:9%;">인정기관</th>
        <th style="width:8%;">기본료</th>
        <th style="width:8%;">관리</th>
      </tr>
    </thead>
    <tbody id="cb-contracts-tbody">{"".join(rows_html)}</tbody>
  </table>
</div>
{pagination}
"""
        )
    except Exception:
        logger.exception("htmx cb-contracts partial failed")
        try:
            db.rollback()
        except Exception:
            pass
        return HTMLResponse(
            '<div class="table-responsive"><table class="data-table"><tbody>'
            '<tr><td style="text-align:center;color:var(--sec-red);">'
            "인증기관 목록을 불러오지 못했습니다.</td></tr></tbody></table></div>"
        )
