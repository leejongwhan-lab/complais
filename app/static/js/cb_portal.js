/**
 * CB Portal shell — tabs, deep links, dashboard, 2-pane HTMX helpers.
 * Auth: CB roles only — platform_admin is rejected (no admin/CB mixing).
 */
(function () {
  const API = (window.COMPLAIS_API_BASE || "/api/v1").replace(/\/$/, "");
  const CB_ROLES = new Set(["cb_admin", "cb_manager", "cb_staff", "cb_reviewer"]);
  const TWO_PANE = new Set([
    "proposals",
    "contracts_pre",
    "contracts",
    "projects",
    "verification",
    "cpd_mgr",
  ]);

  const TAB_TITLES = {
    dashboard: ["대시보드", "인증원현황 · 인증심사운영 · 심사진행상황"],
    applications: ["신청 검토", "인증 신청 접수 및 MD 제안"],
    proposals: ["제안/견적", "제안서·결제 진행"],
    contracts_pre: ["계약 준비", "서명·계약 전 단계"],
    companies: ["고객사현황", "계약·신청 연동 고객사 (조회 전용)"],
    projects: ["심사 프로젝트", "계약 후 심사 운영"],
    audit_docs: ["심사 문서", "노트·보고서 (ISO 17021 읽기 전용)"],
    verification: ["검증·심의", "보고서 검토 및 인증서 발행"],
    auditors: ["심사원 명부", "소속 심사원"],
    cpd_mgr: ["자격/CPD 승인", "자격·코드 신청 큐"],
    conflict: ["이해상충", "이해상충 선언 관리"],
    operations: ["인증원 운영", "입회 관리 · MD17 · MD단가"],
    settlement: ["인증원 운영", "입회 관리 · MD17 · MD단가"],
    billing: ["인증원 운영", "입회 관리 · MD17 · MD단가"],
    finance: ["인증원 운영", "입회 관리 · MD17 · MD단가"],
    cb_info: ["인증원 정보", "기관 프로필 · Scope"],
    approval_policy: ["승인 정책", "내부 승인 규칙"],
  };

  const OPS_SUB_TITLES = {
    dashboard: ["입회 관리 대시보드", "스킴별 입회 현황 · 완료 처리"],
    settings: ["입회 기준/지침 설정", "필수·커버리지·주기 일괄 설정"],
    rates: ["출장비 및 MD 단가 설정", "표준별 MD단가 · 정산 요약"],
  };

  let opsScheme = "";
  let opsWitnessCache = [];
  let opsSettingsCache = [];

  let calYear = null;
  let calMonth = null;
  let calendarEvents = [];

  function token() {
    return localStorage.getItem("access_token");
  }

  function authHeaders() {
    const t = token();
    return t ? { Authorization: "Bearer " + t } : {};
  }

  function clearSession() {
    [
      "access_token",
      "user_id",
      "user_name",
      "role",
      "cb_id",
      "company_id",
      "client_company_id",
      "membership_status",
    ].forEach((k) => localStorage.removeItem(k));
  }

  function forceCbLogin(msg) {
    clearSession();
    const q =
      "/login?next=/cb-portal&msg=" +
      encodeURIComponent(
        msg ||
          "CB 계정으로 로그인해 주세요. 플랫폼 관리자 세션은 CB 포털에 사용할 수 없습니다."
      );
    location.replace(q);
  }

  function qs() {
    return new URLSearchParams(location.search);
  }

  function setQuery(params) {
    const u = new URL(location.href);
    Object.entries(params).forEach(([k, v]) => {
      if (v == null || v === "") u.searchParams.delete(k);
      else u.searchParams.set(k, v);
    });
    history.replaceState(null, "", u.pathname + u.search);
  }

  function fmtMoney(n) {
    const v = Number(n || 0);
    return "₩" + v.toLocaleString("ko-KR");
  }

  function normalizeTab(tab) {
    const t = tab || "dashboard";
    if (t === "settlement" || t === "billing" || t === "finance") return "operations";
    return t;
  }

  function normalizeOpsSub(sub, fromLegacyTab) {
    if (sub === "dashboard" || sub === "settings" || sub === "rates") return sub;
    if (fromLegacyTab === "settlement" || fromLegacyTab === "billing" || fromLegacyTab === "finance") {
      return "rates";
    }
    return "dashboard";
  }

  function switchOpsSub(sub, opts) {
    opts = opts || {};
    const name = normalizeOpsSub(sub);
    document.querySelectorAll(".ops-sub-btn").forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute("data-ops-sub") === name);
    });
    document.querySelectorAll(".ops-sub-panel").forEach((p) => {
      const id = "ops-sub-" + name;
      if (p.id === id) p.hidden = false;
      else p.hidden = true;
    });
    const titles = OPS_SUB_TITLES[name] || TAB_TITLES.operations;
    const h1 = document.getElementById("page-title");
    const subEl = document.getElementById("page-subtitle");
    if (h1) h1.textContent = titles[0];
    if (subEl) subEl.textContent = titles[1];
    if (!opts.skipQuery) {
      setQuery({ tab: "operations", sub: name, scheme: opsScheme || qs().get("scheme") || "" });
    }
    if (name === "dashboard") loadOpsWitnessing();
    else if (name === "settings") loadOpsSettings();
    else if (name === "rates") {
      loadOpsMdRates();
      loadDashboard();
    }
  }

  function switchTab(tab, opts) {
    opts = opts || {};
    const raw = tab || "dashboard";
    const name = normalizeTab(raw);
    document.querySelectorAll(".sidebar-menu-item[data-tab]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-tab") === name);
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("active", p.id === "tab-" + name);
    });
    const titles = TAB_TITLES[name] || [name, ""];
    const h1 = document.getElementById("page-title");
    const sub = document.getElementById("page-subtitle");
    if (h1) h1.textContent = titles[0];
    if (sub) sub.textContent = titles[1];

    if (!opts.skipQuery) {
      const next = { tab: name };
      if (name === "operations") {
        next.sub = normalizeOpsSub(opts.sub || qs().get("sub"), raw);
        if (opts.scheme || opsScheme) next.scheme = opts.scheme || opsScheme;
      } else {
        next.sub = "";
        next.scheme = "";
      }
      if (opts.status) next.status = opts.status;
      else if (!opts.keepStatus) next.status = "";
      if (opts.auditor_id) next.auditor_id = opts.auditor_id;
      if (opts.request_id) next.request_id = opts.request_id;
      if (opts.id) next.id = opts.id;
      setQuery(next);
    }

    if (name === "dashboard") loadDashboard();
    else if (name === "applications") loadCertApplications(opts);
    else if (TWO_PANE.has(name)) loadMasterList(name, opts);
    else if (name === "companies") loadCompanies();
    else if (name === "auditors") loadAuditors();
    else if (name === "cb_info") loadCbInfo();
    else if (name === "operations") {
      switchOpsSub(opts.sub || qs().get("sub") || normalizeOpsSub(null, raw), {
        skipQuery: !!opts.skipQuery,
      });
    }
  }

  const CERT_STATUS_KR = {
    draft: "작성중",
    submitted: "제출완료",
    under_review: "검토중",
    need_fix: "보완요청",
    approved: "승인",
    rejected: "반려",
    contracted: "계약완료",
    withdrawn: "취소",
  };

  async function loadCertApplications(opts) {
    opts = opts || {};
    const tbody = document.getElementById("cert-apps-tbody");
    const countEl = document.getElementById("cert-apps-count");
    if (!tbody) return;
    tbody.innerHTML =
      '<tr><td colspan="8" class="muted">불러오는 중...</td></tr>';
    const status =
      opts.status ||
      qs().get("status") ||
      "submitted,under_review,need_fix";
    try {
      const res = await fetch(
        API +
          "/cb-cert-applications?status=" +
          encodeURIComponent(status),
        { headers: authHeaders(), cache: "no-store" }
      );
      const data = await res.json().catch(() => []);
      if (res.status === 403) {
        forceCbLogin(
          typeof data.detail === "string" ? data.detail : "CB 계정 필요"
        );
        return;
      }
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "목록 로드 실패"
        );
      }
      const rows = Array.isArray(data) ? data : [];
      if (countEl) countEl.textContent = rows.length + "건";
      if (!rows.length) {
        tbody.innerHTML =
          '<tr><td colspan="8" class="muted">신청 건이 없습니다.</td></tr>';
        return;
      }
      tbody.innerHTML = rows
        .map((r) => {
          const stds = (r.standards || [])
            .map((s) => {
              if (s && typeof s === "object") {
                return s.label || [s.initial, s.iso_code, s.name_kr].filter(Boolean).join(" · ") || s.code;
              }
              return s;
            })
            .join("; ");
          const mode = r.audit_mode === "integrated" ? "통합" : "단일";
          const st = CERT_STATUS_KR[r.status] || r.status;
          const desired = r.desired_audit_start || "—";
          return (
            "<tr>" +
            "<td class=\"mono\">" +
            (r.application_no || r.id) +
            "</td>" +
            "<td>" +
            (r.company_name || "—") +
            "</td>" +
            "<td>" +
            (stds || "—") +
            "</td>" +
            "<td>" +
            mode +
            "</td>" +
            "<td>" +
            (r.employee_count ?? "—") +
            "</td>" +
            "<td>" +
            desired +
            "</td>" +
            "<td>" +
            st +
            "</td>" +
            '<td><a class="btn ghost" href="/cb-portal/application-review?id=' +
            r.id +
            '">검토</a></td>' +
            "</tr>"
          );
        })
        .join("");
    } catch (e) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="muted">' +
        (e.message || String(e)) +
        "</td></tr>";
    }
  }

  async function loadDashboard() {
    const errEl = document.getElementById("dash-error");
    if (errEl) errEl.textContent = "";
    try {
      let url = API + "/cb-admin/dashboard";
      if (calYear && calMonth) {
        url += "?year=" + calYear + "&month=" + calMonth;
      }
      const res = await fetch(url, {
        headers: { ...authHeaders() },
        cache: "no-store",
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 403) {
        forceCbLogin(
          typeof data.detail === "string"
            ? data.detail
            : "CB 계정으로 로그인해 주세요."
        );
        return;
      }
      if (!res.ok) throw new Error(data.detail || "대시보드 로드 실패");
      window.__cbDash = data;
      renderDashboard(data);
    } catch (e) {
      if (errEl) errEl.textContent = e.message || String(e);
    }
  }

  function typeLines(t) {
    t = t || {};
    return (
      "최초 " +
      (t.initial || 0) +
      " · 사후 " +
      (t.surveillance || 0) +
      " · 갱신 " +
      (t.renewal || 0) +
      " · 특별 " +
      (t.special || 0)
    );
  }

  function stdLines(rows) {
    rows = rows || [];
    if (!rows.length) return "표준별 실적 없음";
    return rows
      .slice(0, 6)
      .map((r) => escapeHtml(r.standard_code) + " " + (r.count || 0) + "건")
      .join("<br>");
  }

  function renderDashboard(d) {
    const y = d.cert_year || {};
    const m = d.cert_month || {};
    const fin = d.finance || {};
    const aud = d.auditors || {};
    const pipe = d.pipeline || {};
    const cal = d.calendar || {};

    setText("stat-year-total", y.total ?? 0);
    setHtml("stat-year-by-std", stdLines(y.by_standard));
    setText("stat-year-by-type", typeLines(y.by_audit_type));
    setText("stat-year-cancelled", y.cancelled_count ?? 0);

    setText("stat-month-total", m.total ?? 0);
    setHtml("stat-month-by-std", stdLines(m.by_standard));
    setText("stat-month-by-type", typeLines(m.by_audit_type));
    setText("stat-month-cancelled", m.cancelled_count ?? 0);

    setText("stat-aud-registered", aud.registered_this_month ?? 0);
    setText("stat-aud-renewal", aud.renewal_due_count ?? 0);
    setText("stat-pending-qual", aud.pending_qualification_count ?? 0);

    setText("stat-rev-year", fmtMoney(fin.revenue_year));
    setText("stat-rev-month", fmtMoney(fin.revenue_month));
    setText("stat-allowance-total", fmtMoney(fin.auditor_allowance_total));
    setText("stat-settle-pending", fmtMoney(fin.pending_settlement_amount));

    setText("pipe-submitted", pipe.submitted ?? 0);
    setText("pipe-reviewing", pipe.reviewing ?? 0);
    setText("pipe-signed", pipe.signed ?? 0);
    setText("pipe-audit-completed", pipe.audit_completed ?? 0);
    setText("pipe-approved", pipe.approved ?? 0);

    const settleTab = document.getElementById("settle-tab-amount");
    if (settleTab) settleTab.textContent = fmtMoney(fin.pending_settlement_amount);

    calYear = cal.year || calYear || new Date().getFullYear();
    calMonth = cal.month || calMonth || new Date().getMonth() + 1;
    calendarEvents = cal.events || [];
    renderCalendar();

    const warn = document.getElementById("dash-warnings");
    if (warn) {
      warn.textContent = (d.warnings || []).length
        ? "참고: " + d.warnings.join(" · ")
        : "";
    }
  }

  function renderCalendar() {
    const box = document.getElementById("cb-calendar");
    const title = document.getElementById("cal-title");
    if (!box) return;
    if (title) title.textContent = calYear + "년 " + calMonth + "월";

    const first = new Date(calYear, calMonth - 1, 1);
    const startPad = first.getDay(); // 0 Sun
    const daysInMonth = new Date(calYear, calMonth, 0).getDate();
    const byDate = {};
    calendarEvents.forEach((ev) => {
      if (!byDate[ev.date]) byDate[ev.date] = [];
      byDate[ev.date].push(ev);
    });

    const heads = ["일", "월", "화", "수", "목", "금", "토"]
      .map((h) => '<div class="cal-head">' + h + "</div>")
      .join("");
    let cells = "";
    for (let i = 0; i < startPad; i++) {
      cells += '<div class="cal-cell is-empty"></div>';
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const iso =
        calYear +
        "-" +
        String(calMonth).padStart(2, "0") +
        "-" +
        String(d).padStart(2, "0");
      const list = byDate[iso] || [];
      const names = list
        .slice(0, 3)
        .map(
          (ev) =>
            '<button type="button" class="cal-event" data-cal-idx="' +
            calendarEvents.indexOf(ev) +
            '">' +
            escapeHtml(ev.company_name) +
            "</button>"
        )
        .join("");
      const more =
        list.length > 3
          ? '<span class="cal-more">+' + (list.length - 3) + "</span>"
          : "";
      cells +=
        '<div class="cal-cell' +
        (list.length ? " has-events" : "") +
        '"><div class="cal-day">' +
        d +
        "</div>" +
        names +
        more +
        "</div>";
    }
    box.innerHTML = '<div class="cal-grid">' + heads + cells + "</div>";
  }

  function openAuditModal(ev) {
    const modal = document.getElementById("cb-audit-modal");
    const body = document.getElementById("cb-modal-body");
    if (!modal || !body || !ev) return;
    body.innerHTML =
      "<dt>기업</dt><dd>" +
      escapeHtml(ev.company_name) +
      "</dd>" +
      "<dt>표준</dt><dd>" +
      escapeHtml(ev.standard || "—") +
      "</dd>" +
      "<dt>심사유형</dt><dd>" +
      escapeHtml(ev.audit_type || "—") +
      "</dd>" +
      "<dt>심사원</dt><dd>" +
      escapeHtml((ev.auditors || []).join(", ") || "—") +
      "</dd>" +
      "<dt>상태</dt><dd>" +
      escapeHtml(ev.status || "—") +
      "</dd>" +
      "<dt>기간</dt><dd>" +
      escapeHtml(
        (ev.period_start || "—") +
          " ~ " +
          (ev.period_end || ev.period_start || "—")
      ) +
      "</dd>" +
      "<dt>계약</dt><dd>#" +
      escapeHtml(ev.contract_id != null ? String(ev.contract_id) : "—") +
      "</dd>";
    modal.hidden = false;
  }

  function closeAuditModal() {
    const modal = document.getElementById("cb-audit-modal");
    if (modal) modal.hidden = true;
  }

  function setText(id, v) {
    const el = document.getElementById(id);
    if (el) el.textContent = v;
  }

  function setHtml(id, v) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = v;
  }

  function escapeHtml(t) {
    const d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }

  function loadMasterList(tab, opts) {
    opts = opts || {};
    const status = opts.status || qs().get("status") || "";
    const auditorId = opts.auditor_id || qs().get("auditor_id") || "";
    const requestId = opts.request_id || qs().get("request_id") || "";
    const listTab = tab === "contracts" ? "contracts_pre" : tab;
    const panel = document.querySelector("#tab-" + tab + " .master-pane");
    const detail = document.getElementById("detail-pane-" + listTab);
    if (!panel) return;
    let url =
      "/cb-portal/partials/list?tab=" + encodeURIComponent(listTab);
    if (status) url += "&status=" + encodeURIComponent(status);
    if (auditorId) url += "&auditor_id=" + encodeURIComponent(auditorId);
    if (requestId) url += "&request_id=" + encodeURIComponent(requestId);
    if (window.htmx) {
      htmx.ajax("GET", url, { target: panel, swap: "innerHTML" });
    }
    if (detail && opts.id) {
      htmx.ajax(
        "GET",
        "/cb-portal/partials/detail?tab=" +
          encodeURIComponent(listTab) +
          "&id=" +
          encodeURIComponent(opts.id),
        { target: detail, swap: "innerHTML" }
      );
    } else if (detail && !requestId) {
      detail.innerHTML =
        '<div class="detail-empty"><p class="muted">왼쪽 목록에서 항목을 선택하세요.</p></div>';
    }
  }

  let companyPage = 1;
  const companyLimit = 10;
  let currentCompanyId = null;
  let draftSites = [];
  let draftDepartments = [];
  let draftStaff = [];

  function resolveCorpType(company) {
    if (company.entity_type || company.corp_type) {
      return company.entity_type || company.corp_type;
    }
    const mid = (company.biz_no || "").split("-")[1] || "";
    return mid.startsWith("8") ? "법인" : "개인/기타";
  }

  function setInputValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? "";
  }

  function setOrgMsg(id, message, kind) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = message || "";
    el.classList.remove("ok", "err");
    if (kind) el.classList.add(kind);
  }

  function loadCompanies() {
    const panel = document.getElementById("cb-company-htmx-panel");
    if (panel && window.htmx) {
      const form = document.getElementById("cb-company-search-form");
      if (form) {
        const pageInput = document.getElementById("cb-company-page");
        if (pageInput) pageInput.value = "1";
        htmx.trigger(form, "submit");
        return;
      }
      htmx.ajax("GET", "/cb-portal/partials/companies", {
        target: panel,
        swap: "innerHTML",
      });
      return;
    }
    fetchCompanies(1);
  }

  async function fetchCompanies(page) {
    page = page || 1;
    companyPage = page;
    const keyword =
      document.getElementById("cb-company-search-keyword")?.value || "";
    const tbody = document.getElementById("cb-company-table-body");
    const totalEl = document.getElementById("cb-company-total-count");
    if (tbody) {
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';
    }
    try {
      const res = await fetch(
        API +
          "/cb-admin/companies?page=" +
          page +
          "&limit=" +
          companyLimit +
          "&keyword=" +
          encodeURIComponent(keyword),
        { headers: authHeaders(), cache: "no-store" }
      );
      const data = await res.json().catch(() => ({}));
      if (res.status === 403) {
        forceCbLogin(
          typeof data.detail === "string" ? data.detail : "CB 계정 필요"
        );
        return;
      }
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "고객사 목록 실패"
        );
      }
      const rows = data.data || [];
      if (totalEl) totalEl.textContent = String(data.total ?? 0);
      if (!rows.length) {
        if (tbody) {
          tbody.innerHTML =
            '<tr><td colspan="9" style="text-align: center; color: var(--font-tertiary);">등록된 고객사가 없습니다.</td></tr>';
        }
        renderCompanyPagination(0, 1, companyLimit);
        return;
      }
      if (tbody) {
        tbody.innerHTML = rows
          .map((c, i) => {
            const companyId = c.company_id ?? c.id;
            const seq = (companyPage - 1) * companyLimit + i + 1;
            const companyName = c.company_name ?? c.name ?? "";
            const corpType = resolveCorpType(c);
            const websiteUrl = c.website
              ? c.website.startsWith("http")
                ? c.website
                : "http://" + c.website
              : null;
            const addr = c.address_kr || c.address || "";
            const held = Array.isArray(c.held_standards) ? c.held_standards : [];
            const heldHtml = held.length
              ? held
                  .slice(0, 6)
                  .map((h) => {
                    const label =
                      h.label ||
                      [h.initial, h.iso_code, h.name_kr].filter(Boolean).join(" · ") ||
                      h.initial ||
                      h.standard_code ||
                      "";
                    const ab = h.ab_code || "—";
                    const cb = h.cb_initial || h.cb_name || "—";
                    return escapeHtml(label + " (AB:" + ab + " / CB:" + cb + ")");
                  })
                  .join("<br>") +
                (held.length > 6
                  ? "<br><span class='muted'>+" + (held.length - 6) + "</span>"
                  : "")
              : "—";
            return (
              "<tr>" +
              "<td>" +
              seq +
              "</td>" +
              '<td class="col-company-name fw-bold" title="' +
              escapeHtml(companyName) +
              '">' +
              escapeHtml(companyName) +
              "</td>" +
              "<td>" +
              escapeHtml(c.biz_no || "-") +
              "</td>" +
              "<td>" +
              escapeHtml(corpType) +
              "</td>" +
              "<td>" +
              escapeHtml(c.ceo_name || "-") +
              "</td>" +
              '<td style="font-size:11px;line-height:1.45;white-space:normal;min-width:160px">' +
              heldHtml +
              "</td>" +
              '<td title="' +
              escapeHtml(addr) +
              '">' +
              escapeHtml(addr || "-") +
              "</td>" +
              "<td>" +
              (websiteUrl
                ? '<a href="' +
                  escapeHtml(websiteUrl) +
                  '" target="_blank" rel="noopener" class="text-decoration-none">방문</a>'
                : "-") +
              "</td>" +
              '<td><button type="button" class="btn-detail" onclick="openCbCompanyDetail(' +
              Number(companyId) +
              ')">상세정보</button></td>' +
              "</tr>"
            );
          })
          .join("");
      }
      renderCompanyPagination(data.total || 0, data.page || page, data.limit || companyLimit);
    } catch (e) {
      if (tbody) {
        tbody.innerHTML =
          '<tr><td colspan="9" style="text-align: center; color: var(--sec-red);">' +
          escapeHtml(e.message || String(e)) +
          "</td></tr>";
      }
    }
  }

  const PAGINATION_WINDOW = 5;

  function buildPaginationPageNums(current, totalPages, windowSize) {
    windowSize = windowSize || PAGINATION_WINDOW;
    let start = Math.max(1, current - Math.floor(windowSize / 2));
    let end = Math.min(totalPages, start + windowSize - 1);
    start = Math.max(1, end - windowSize + 1);
    const pageNums = [];
    if (start > 1) pageNums.push(1);
    for (let p = start; p <= end; p += 1) {
      if (!pageNums.includes(p)) pageNums.push(p);
    }
    if (end < totalPages && !pageNums.includes(totalPages)) pageNums.push(totalPages);
    return pageNums;
  }

  function renderCompanyPagination(total, page, limit) {
    const el = document.getElementById("cb-company-pagination");
    if (!el) return;
    el.classList.add("pagination-container");
    const totalPages = Math.max(1, Math.ceil((total || 0) / limit));
    const current = Math.min(Math.max(1, page), totalPages);
    if (!total) {
      el.innerHTML = "";
      return;
    }
    const pageNums = buildPaginationPageNums(current, totalPages);
    const buttons = [];
    buttons.push(
      '<button type="button" class="page-btn nav-btn" data-page="' +
        (current - 1) +
        '"' +
        (current <= 1 ? " disabled" : "") +
        ">‹</button>"
    );
    let prevP = null;
    pageNums.forEach((p) => {
      if (prevP !== null && p > prevP + 1) {
        buttons.push(
          '<button type="button" class="page-btn nav-btn" disabled>…</button>'
        );
      }
      buttons.push(
        '<button type="button" class="page-btn' +
          (p === current ? " active" : "") +
          '" data-page="' +
          p +
          '">' +
          p +
          "</button>"
      );
      prevP = p;
    });
    buttons.push(
      '<button type="button" class="page-btn nav-btn" data-page="' +
        (current + 1) +
        '"' +
        (current >= totalPages ? " disabled" : "") +
        ">›</button>"
    );
    el.innerHTML = buttons.join("");
    el.querySelectorAll("button[data-page]:not(:disabled)").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = Number(btn.getAttribute("data-page"));
        if (!Number.isNaN(next) && next >= 1 && next <= totalPages) {
          fetchCompanies(next);
        }
      });
    });
  }

  function openCompanyDetailModal() {
    const modal = document.getElementById("cbCompanyDetailModal");
    if (!modal) return;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    switchCompanyDetailTab("cb-basic-info");
  }

  function closeCompanyDetailModal() {
    const modal = document.getElementById("cbCompanyDetailModal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  function switchCompanyDetailTab(tabId) {
    document.querySelectorAll("#cbCompanyDetailTab .nav-link").forEach((btn) => {
      btn.classList.toggle(
        "active",
        btn.getAttribute("data-cb-detail-tab") === tabId
      );
    });
    document
      .querySelectorAll("#cbCompanyDetailTabContent .detail-tab-pane")
      .forEach((pane) => {
        pane.classList.toggle("active", pane.id === tabId);
      });
  }

  function fillHeadcountYearSelect(detail) {
    const sel = document.getElementById("cbc-headcount_year");
    if (!sel) return;
    const current = new Date().getFullYear();
    const years =
      Array.isArray(detail.headcount_years) && detail.headcount_years.length
        ? detail.headcount_years.slice()
        : [current];
    if (!years.includes(current)) years.unshift(current);
    const selected = detail.headcount_year || current;
    if (!years.includes(selected)) years.unshift(selected);
    sel.innerHTML = years
      .map(
        (y) =>
          '<option value="' +
          y +
          '"' +
          (Number(y) === Number(selected) ? " selected" : "") +
          ">" +
          y +
          "</option>"
      )
      .join("");
  }

  function renderCbSites() {
    const box = document.getElementById("cbc-site-list");
    if (!box) return;
    if (!draftSites.length) {
      box.innerHTML = '<div class="org-empty">등록된 추가사업장이 없습니다.</div>';
      return;
    }
    box.innerHTML =
      '<table class="org-table"><thead><tr>' +
      "<th>사업장명</th><th>주소</th><th>상세주소</th><th>영문주소</th><th>인원</th><th>업무유형</th>" +
      "</tr></thead><tbody>" +
      draftSites
        .map(
          (s) =>
            "<tr><td>" +
            escapeHtml(s.site_name || "—") +
            "</td><td>" +
            escapeHtml(s.address || "—") +
            "</td><td>" +
            escapeHtml(s.detail_address || "—") +
            "</td><td>" +
            escapeHtml(s.address_en || "—") +
            "</td><td>" +
            escapeHtml(s.employee_count ?? 0) +
            "</td><td>" +
            escapeHtml(s.work_type || "—") +
            "</td></tr>"
        )
        .join("") +
      "</tbody></table>";
  }

  function renderCbDepartments() {
    const box = document.getElementById("cbc-dept-tags");
    if (!box) return;
    if (!draftDepartments.length) {
      box.innerHTML = '<div class="org-empty">등록된 부서가 없습니다.</div>';
      return;
    }
    box.innerHTML = draftDepartments
      .map((name) => '<span class="dept-tag">' + escapeHtml(name) + "</span>")
      .join("");
  }

  function renderCbStaff() {
    const body = document.getElementById("cbc-staff-body");
    if (!body) return;
    if (!draftStaff.length) {
      body.innerHTML =
        '<tr><td colspan="7" class="org-empty">등록된 담당자가 없습니다.</td></tr>';
      return;
    }
    body.innerHTML = draftStaff
      .map(
        (s) =>
          "<tr><td>" +
          escapeHtml(s.role || "—") +
          "</td><td>" +
          escapeHtml(s.staff_name || "—") +
          "</td><td>" +
          escapeHtml(s.department || "—") +
          "</td><td>" +
          escapeHtml(s.position || "—") +
          "</td><td>" +
          escapeHtml(s.phone || "—") +
          "</td><td>" +
          escapeHtml(s.mobile || "—") +
          "</td><td>" +
          escapeHtml(s.email || "—") +
          "</td></tr>"
      )
      .join("");
  }

  function renderHeldStandards(held) {
    const body = document.getElementById("cbc-held-std-body");
    const countEl = document.getElementById("cbc-cert-count");
    const rows = Array.isArray(held) ? held : [];
    if (countEl) countEl.textContent = rows.length ? "(" + rows.length + ")" : "";
    if (!body) return;
    if (!rows.length) {
      body.innerHTML =
        '<tr><td colspan="5" class="muted">등록된 보유 표준이 없습니다.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map((r) => {
        const label =
          r.label ||
          [r.initial, r.iso_code, r.name_kr].filter(Boolean).join(" · ") ||
          r.standard_code ||
          "—";
        const cb =
          r.cb_name ||
          r.cb_initial ||
          (r.cb_id != null ? "CB#" + r.cb_id : "—");
        return (
          "<tr>" +
          "<td>" +
          escapeHtml(label) +
          "</td>" +
          "<td>" +
          escapeHtml(r.ab_code || "—") +
          "</td>" +
          "<td>" +
          escapeHtml(cb) +
          "</td>" +
          "<td>" +
          escapeHtml(r.cert_no || "—") +
          "</td>" +
          "<td>" +
          escapeHtml(r.status || "—") +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function bindCompanyDetail(detail) {
    currentCompanyId = detail.company_id ?? detail.id;
    const companyName = detail.company_name || detail.name || "고객사";
    setText("cb-modal-company-title", companyName + " 상세 정보");
    setInputValue("cbc-id-display", currentCompanyId);
    setInputValue("cbc-status", detail.status || "—");
    setInputValue("cbc-name", companyName);
    setInputValue("cbc-name_en", detail.name_en);
    setInputValue("cbc-biz_no", detail.biz_no);
    setInputValue("cbc-entity_type", detail.entity_type || "");
    setInputValue("cbc-corp_no", detail.corp_no);
    setInputValue("cbc-ceo_name", detail.ceo_name);
    setInputValue("cbc-biz_type", detail.biz_type);
    setInputValue("cbc-biz_class", detail.biz_class);
    setInputValue("cbc-ksic_code", detail.ksic_code);
    setInputValue("cbc-iaf_code", detail.iaf_code);
    setInputValue("cbc-tel", detail.tel);
    setInputValue("cbc-email", detail.email);
    setInputValue("cbc-website", detail.website);
    setInputValue("cbc-address", detail.address);
    setInputValue("cbc-detail_address", detail.detail_address);
    setInputValue("cbc-address_en", detail.address_en);
    setInputValue("cbc-scope_kr", detail.scope_kr);
    setInputValue("cbc-scope_en", detail.scope_en);

    fillHeadcountYearSelect(detail);
    setInputValue("cbc-employee_count", detail.employee_count ?? "");
    setInputValue("cbc-headcount_outsourced", detail.headcount_outsourced ?? "");
    setInputValue("cbc-headcount_regular", detail.headcount_regular ?? "");
    setInputValue(
      "cbc-headcount_non_regular",
      detail.headcount_non_regular ?? ""
    );

    draftSites = (detail.sites || []).map((s) => Object.assign({}, s));
    draftDepartments = (detail.departments || []).map((d) => d.name);
    draftStaff = (detail.staff || []).map((s) => Object.assign({}, s));
    renderCbSites();
    renderCbDepartments();
    renderCbStaff();
    renderHeldStandards(detail.held_standards || []);
    ["cbc-basic-msg", "cbc-headcount-msg", "cbc-site-msg", "cbc-dept-msg", "cbc-staff-msg", "cbc-aspects-msg"].forEach(
      (id) => setOrgMsg(id, "")
    );
    loadCompanyAspects(currentCompanyId);
  }

  async function loadCompanyAspects(companyId) {
    if (!companyId || !window.CompanyAspectsForm) return;
    try {
      const res = await fetch(API + "/cb-admin/companies/" + companyId + "/aspects", {
        headers: authHeaders(),
        cache: "no-store",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "특성 정보 로드 실패");
      const cat = data.catalog || {};
      const asp = data.aspects || {};
      CompanyAspectsForm.renderEms(document.getElementById("cbc-ems-box"), cat.ems, asp.ems);
      CompanyAspectsForm.renderOhs(document.getElementById("cbc-ohs-box"), cat.ohs, asp.ohs);
      CompanyAspectsForm.renderEnms(document.getElementById("cbc-enms-box"), cat.enms, asp.enms);
    } catch (e) {
      setOrgMsg("cbc-aspects-msg", e.message || String(e), "err");
    }
  }

  async function saveCompanyAspects() {
    if (!currentCompanyId || !window.CompanyAspectsForm) return;
    try {
      const body = {
        ems: CompanyAspectsForm.collectEms(),
        ohs: CompanyAspectsForm.collectOhs(),
        enms: CompanyAspectsForm.collectEnms(),
      };
      const res = await fetch(API + "/cb-admin/companies/" + currentCompanyId + "/aspects", {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "저장 실패");
      setOrgMsg("cbc-aspects-msg", "특성 정보가 저장되었습니다.", "ok");
    } catch (e) {
      setOrgMsg("cbc-aspects-msg", e.message || String(e), "err");
    }
  }

  async function fetchCompanyDetail(id, headcountYear) {
    let url = API + "/cb-admin/companies/" + id;
    if (headcountYear) {
      url += "?headcount_year=" + encodeURIComponent(headcountYear);
    }
    const res = await fetch(url, { headers: authHeaders(), cache: "no-store" });
    const data = await res.json().catch(() => ({}));
    if (res.status === 403) {
      forceCbLogin(
        typeof data.detail === "string" ? data.detail : "CB 계정 필요"
      );
      throw new Error("권한 없음");
    }
    if (!res.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : "상세 조회 실패 (HTTP " + res.status + ")"
      );
    }
    return data;
  }

  async function openCbCompanyDetail(id) {
    openCompanyDetailModal();
    setText("cb-modal-company-title", "고객사 상세 정보");
    try {
      const detail = await fetchCompanyDetail(id);
      bindCompanyDetail(detail);
    } catch (error) {
      setOrgMsg(
        "cbc-basic-msg",
        error.message || "상세를 불러오지 못했습니다.",
        "err"
      );
    }
  }

  document
    .querySelectorAll("[data-cb-company-modal-close]")
    .forEach((btn) => {
      btn.addEventListener("click", closeCompanyDetailModal);
    });
  const aspectsSaveBtn = document.getElementById("cbc-aspects-save");
  if (aspectsSaveBtn) {
    aspectsSaveBtn.addEventListener("click", () => saveCompanyAspects());
  }
  const companyModal = document.getElementById("cbCompanyDetailModal");
  if (companyModal) {
    companyModal.addEventListener("click", (e) => {
      if (e.target === companyModal) closeCompanyDetailModal();
    });
  }
  document
    .querySelectorAll("#cbCompanyDetailTab [data-cb-detail-tab]")
    .forEach((btn) => {
      btn.addEventListener("click", () =>
        switchCompanyDetailTab(btn.getAttribute("data-cb-detail-tab"))
      );
    });
  document
    .getElementById("cbc-headcount_year")
    ?.addEventListener("change", async () => {
      if (!currentCompanyId) return;
      try {
        const year = document.getElementById("cbc-headcount_year")?.value;
        const detail = await fetchCompanyDetail(currentCompanyId, year);
        bindCompanyDetail(detail);
        setOrgMsg("cbc-headcount-msg", year + "년 인원 불러옴", "ok");
      } catch (err) {
        setOrgMsg(
          "cbc-headcount-msg",
          err.message || "조회 실패",
          "err"
        );
      }
    });

  window.openCbCompanyDetail = openCbCompanyDetail;

  async function loadAuditors() {
    const body = document.getElementById("auditors-body");
    if (!body) return;
    body.innerHTML =
      '<tr><td colspan="4" class="muted">불러오는 중…</td></tr>';
    try {
      const res = await fetch(API + "/cb/memberships?limit=100", {
        headers: authHeaders(),
      });
      const rows = await res.json().catch(() => []);
      if (res.status === 403) {
        forceCbLogin("CB 계정으로 로그인해 주세요.");
        return;
      }
      if (!res.ok) throw new Error(rows.detail || "심사원 목록 실패");
      const list = Array.isArray(rows) ? rows : rows.items || [];
      if (!list.length) {
        body.innerHTML =
          '<tr><td colspan="4" class="muted">소속 심사원이 없습니다.</td></tr>';
        return;
      }
      body.innerHTML = list
        .map(
          (a, i) =>
            `<tr><td>${i + 1}</td><td>${escapeHtml(a.name || a.auditor_name || "—")}</td>` +
            `<td>${escapeHtml(a.grade || a.approved_grade || "—")}</td>` +
            `<td>${escapeHtml(a.status || "—")}</td></tr>`
        )
        .join("");
    } catch (e) {
      body.innerHTML =
        `<tr><td colspan="4" class="muted">${escapeHtml(e.message)}</td></tr>`;
    }
  }

  async function loadCbInfo() {
    const box = document.getElementById("cb-info-body");
    if (!box) return;
    box.innerHTML = '<p class="muted">불러오는 중…</p>';
    try {
      const res = await fetch(API + "/cb/profile", { headers: authHeaders() });
      const d = await res.json();
      if (res.status === 403) {
        forceCbLogin(
          typeof d.detail === "string" ? d.detail : "CB 계정 필요"
        );
        return;
      }
      if (!res.ok) throw new Error(d.detail || "프로필 로드 실패");
      box.innerHTML =
        `<dl class="kv-grid">` +
        `<dt>코드</dt><dd>${escapeHtml(d.code)}</dd>` +
        `<dt>기관명</dt><dd>${escapeHtml(d.name)}</dd>` +
        `<dt>대표</dt><dd>${escapeHtml(d.ceo_name || "—")}</dd>` +
        `<dt>연락처</dt><dd>${escapeHtml(d.phone || d.tel || "—")}</dd>` +
        `<dt>이메일</dt><dd>${escapeHtml(d.email || "—")}</dd>` +
        `<dt>인정기구</dt><dd>${escapeHtml(d.accreditation_body || "—")}</dd>` +
        `<dt>상태</dt><dd>${escapeHtml(d.status || "—")}</dd>` +
        `</dl>` +
        `<div class="org-section" style="margin-top:16px">` +
        `<h3 class="org-section-title">기본 주소</h3>` +
        `<div class="org-field full"><label for="cbi-zip">우편번호 / 주소</label>` +
        `<div class="addr-row">` +
        `<input id="cbi-zip" class="addr-zip" readonly placeholder="우편번호" />` +
        `<input id="cbi-address" class="addr-main" readonly placeholder="도로명/지번 주소" />` +
        `<button type="button" class="btn-postcode" data-postcode-zip="cbi-zip" data-postcode-addr="cbi-address" data-postcode-detail="cbi-detail">주소 검색</button>` +
        `</div></div>` +
        `<div class="org-field full" style="margin-top:8px"><label for="cbi-detail">상세주소</label>` +
        `<input id="cbi-detail" placeholder="상세주소 (선택)" /></div>` +
        `<div class="org-actions" style="margin-top:10px">` +
        `<button type="button" class="btn-primary" id="cbi-addr-save">주소 저장</button></div>` +
        `<div class="org-msg" id="cbi-addr-msg"></div>` +
        `</div>` +
        `<p class="hint"><a href="/static/cb_portal_legacy.html">상세 프로필/Scope 편집 (레거시)</a></p>`;
      const addr = d.address || "";
      document.getElementById("cbi-address").value = addr;
      document.getElementById("cbi-detail").value = "";
      if (typeof wireDaumPostcodeButtons === "function") wireDaumPostcodeButtons(box);
      document.getElementById("cbi-addr-save")?.addEventListener("click", async () => {
        const msgEl = document.getElementById("cbi-addr-msg");
        const base = (document.getElementById("cbi-address").value || "").trim();
        const detail = (document.getElementById("cbi-detail").value || "").trim();
        const composed = [base, detail].filter(Boolean).join(" ").trim() || null;
        try {
          const res2 = await fetch(API + "/cb/profile", {
            method: "PUT",
            headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
            body: JSON.stringify({ address: composed }),
          });
          const d2 = await res2.json().catch(() => ({}));
          if (!res2.ok) throw new Error(typeof d2.detail === "string" ? d2.detail : "저장 실패");
          if (msgEl) {
            msgEl.textContent = "주소가 저장되었습니다.";
            msgEl.className = "org-msg ok";
          }
        } catch (err) {
          if (msgEl) {
            msgEl.textContent = err.message || "저장 실패";
            msgEl.className = "org-msg err";
          }
        }
      });
    } catch (e) {
      box.innerHTML = `<p class="muted">${escapeHtml(e.message)}</p>`;
    }
  }

  async function sessionGate() {
    const meta = document.getElementById("session-meta");
    if (!token()) {
      forceCbLogin("CB 포털 이용을 위해 로그인해 주세요.");
      return false;
    }
    try {
      const res = await fetch(API + "/auth/me", { headers: authHeaders() });
      if (res.status === 401) {
        forceCbLogin("세션이 만료되었습니다. 다시 로그인해 주세요.");
        return false;
      }
      const me = await res.json();
      const role = (me.role || "").toLowerCase();
      if (role === "platform_admin" || role === "admin") {
        forceCbLogin(
          "플랫폼 관리자 계정으로는 CB 포털에 들어갈 수 없습니다. CB 계정(예: cb@complais.com)으로 로그인해 주세요."
        );
        return false;
      }
      if (!CB_ROLES.has(role) || !me.cb_id) {
        if (meta) meta.textContent = "CB 포털 권한이 없습니다.";
        forceCbLogin("CB 역할 계정이 필요합니다.");
        return false;
      }
      localStorage.setItem("role", role);
      localStorage.setItem("cb_id", String(me.cb_id));
      if (meta) {
        meta.textContent =
          (me.name || me.email || "사용자") +
          " · " +
          role +
          " · CB #" +
          me.cb_id;
      }
      return true;
    } catch (_) {
      if (meta) meta.textContent = "세션 확인 실패";
      return false;
    }
  }

  function renderSchemeTabs(containerId, schemes, activeCode, onClick) {
    const box = document.getElementById(containerId);
    if (!box) return;
    const list = schemes || [];
    if (!list.length) {
      box.innerHTML = '<span class="muted">보유 표준 스킴이 없습니다.</span>';
      return;
    }
    box.innerHTML = list
      .map((s) => {
        const active = s.code === activeCode ? " is-active" : "";
        const label = s.code === "OHSMS" ? "OH&S" : s.code;
        return (
          '<button type="button" class="btn-secondary ops-scheme-btn' +
          active +
          '" data-scheme="' +
          escapeHtml(s.code) +
          '" title="' +
          escapeHtml(s.label || s.code) +
          '">' +
          escapeHtml(label) +
          "</button>"
        );
      })
      .join("");
    box.querySelectorAll("[data-scheme]").forEach((btn) => {
      btn.addEventListener("click", () => onClick(btn.getAttribute("data-scheme")));
    });
  }

  async function loadOpsWitnessing() {
    const tbody = document.getElementById("ops-witness-tbody");
    const err = document.getElementById("ops-dash-error");
    if (err) err.textContent = "";
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="muted">불러오는 중…</td></tr>';
    const scheme = opsScheme || qs().get("scheme") || "";
    try {
      const res = await fetch(
        API +
          "/cb-admin/operations/witnessing" +
          (scheme ? "?scheme=" + encodeURIComponent(scheme) : ""),
        { headers: authHeaders(), cache: "no-store" }
      );
      const data = await res.json().catch(() => ({}));
      if (res.status === 403) {
        forceCbLogin(typeof data.detail === "string" ? data.detail : "CB 계정 필요");
        return;
      }
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "입회 현황 로드 실패");
      }
      opsScheme = (data.scheme && data.scheme.code) || scheme || "";
      opsWitnessCache = data.items || [];
      renderSchemeTabs("ops-scheme-tabs", data.schemes || [], opsScheme, (code) => {
        opsScheme = code;
        setQuery({ tab: "operations", sub: "dashboard", scheme: code });
        loadOpsWitnessing();
      });
      const sum = data.summary || {};
      setText("ops-sum-total", sum.total ?? 0);
      setText("ops-sum-due", sum.due_soon ?? 0);
      setText("ops-sum-expired", sum.expired ?? 0);
      setText("ops-sum-missing", sum.missing ?? 0);
      if (!tbody) return;
      if (!opsWitnessCache.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="muted">코드가 없습니다. (시드/인정범위 확인)</td></tr>';
        return;
      }
      tbody.innerHTML = opsWitnessCache
        .map((r) => {
          const crit = r.is_critical ? "필수" : "일반";
          const last = r.last_witness_date || "";
          const due = r.next_due_date || "";
          const others = r.same_iaf_other_schemes || [];
          const integHint = others.length
            ? '<label class="muted" style="display:block;margin-top:4px;font-size:11px;"><input type="checkbox" data-integ="' +
              r.id +
              '"/> 통합심사 — 함께 완료</label>'
            : "";
          return (
            "<tr data-wid=\"" +
            r.id +
            '">' +
            '<td class="mono">' +
            escapeHtml(r.iaf_code) +
            "</td>" +
            "<td>" +
            escapeHtml(r.cluster_name || "—") +
            "</td>" +
            "<td>" +
            crit +
            "</td>" +
            "<td>" +
            (r.cycle_years || 5) +
            "년</td>" +
            "<td>" +
            escapeHtml(last || "—") +
            "</td>" +
            "<td>" +
            escapeHtml(due || "—") +
            "</td>" +
            "<td>" +
            escapeHtml(r.status) +
            "</td>" +
            "<td>" +
            '<input type="date" class="form-input" data-wdate="' +
            r.id +
            '" value="' +
            escapeHtml(last) +
            '" style="min-width:140px;display:inline-block;" /> ' +
            '<button type="button" class="btn-primary" data-wcomplete="' +
            r.id +
            '">완료</button>' +
            integHint +
            "</td>" +
            "</tr>"
          );
        })
        .join("");
    } catch (e) {
      if (err) err.textContent = e.message || String(e);
      if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="muted">불러오기 실패</td></tr>';
    }
  }

  async function completeWitnessing(id) {
    const dateEl = document.querySelector('[data-wdate="' + id + '"]');
    const integEl = document.querySelector('[data-integ="' + id + '"]');
    const d = (dateEl && dateEl.value) || "";
    if (!d) {
      alert("입회일을 선택하세요.");
      return;
    }
    const res = await fetch(API + "/cb-admin/operations/witnessing/" + id + "/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        last_witness_date: d,
        complete_integrated: !!(integEl && integEl.checked),
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 403) {
      forceCbLogin(typeof data.detail === "string" ? data.detail : "CB 계정 필요");
      return;
    }
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "완료 처리 실패");
    }
    const autoN = (data.auto_propagated_ids || []).length;
    const integN = (data.integrated_ids || []).length;
    alert(
      "입회 완료" +
        (autoN ? " · 자동전파 " + autoN + "건" : "") +
        (integN ? " · 통합심사 " + integN + "건" : "")
    );
    loadOpsWitnessing();
  }

  async function loadOpsSettings() {
    const tbody = document.getElementById("ops-settings-tbody");
    const msg = document.getElementById("ops-settings-msg");
    if (msg) msg.textContent = "";
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="muted">불러오는 중…</td></tr>';
    const scheme = opsScheme || qs().get("scheme") || "";
    try {
      const res = await fetch(
        API +
          "/cb-admin/operations/witnessing/settings" +
          (scheme ? "?scheme=" + encodeURIComponent(scheme) : ""),
        { headers: authHeaders(), cache: "no-store" }
      );
      const data = await res.json().catch(() => ({}));
      if (res.status === 403) {
        forceCbLogin(typeof data.detail === "string" ? data.detail : "CB 계정 필요");
        return;
      }
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "설정 로드 실패");
      }
      opsScheme = (data.scheme && data.scheme.code) || scheme || "";
      opsSettingsCache = data.items || [];
      // reuse schemes from dashboard endpoint for tabs
      const dash = await fetch(
        API +
          "/cb-admin/operations/witnessing" +
          (opsScheme ? "?scheme=" + encodeURIComponent(opsScheme) : ""),
        { headers: authHeaders(), cache: "no-store" }
      );
      const dashData = await dash.json().catch(() => ({}));
      renderSchemeTabs(
        "ops-settings-scheme-tabs",
        dashData.schemes || (data.scheme ? [data.scheme] : []),
        opsScheme,
        (code) => {
          opsScheme = code;
          setQuery({ tab: "operations", sub: "settings", scheme: code });
          loadOpsSettings();
        }
      );
      if (!tbody) return;
      if (!opsSettingsCache.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="muted">항목이 없습니다.</td></tr>';
        return;
      }
      tbody.innerHTML = opsSettingsCache
        .map((r) => {
          return (
            '<tr data-sid="' +
            r.id +
            '">' +
            '<td class="mono">' +
            escapeHtml(r.iaf_code) +
            "</td>" +
            "<td>" +
            escapeHtml(r.cluster_name || "—") +
            "</td>" +
            '<td><input type="checkbox" data-crit ' +
            (r.is_critical ? "checked" : "") +
            " /></td>" +
            '<td><input type="checkbox" data-elig ' +
            (r.eligible_for_coverage ? "checked" : "") +
            (r.is_critical ? " disabled" : "") +
            " /></td>" +
            '<td><input type="number" class="form-input" min="1" max="10" data-cycle value="' +
            (r.cycle_years || 5) +
            '" style="width:72px;" /></td>' +
            '<td><input type="date" class="form-input" data-last value="' +
            escapeHtml(r.last_witness_date || "") +
            '" /></td>' +
            "<td>" +
            escapeHtml(r.status) +
            "</td>" +
            "</tr>"
          );
        })
        .join("");
      tbody.querySelectorAll("tr[data-sid]").forEach((tr) => {
        const crit = tr.querySelector("[data-crit]");
        const elig = tr.querySelector("[data-elig]");
        crit?.addEventListener("change", () => {
          if (crit.checked) {
            elig.checked = false;
            elig.disabled = true;
          } else {
            elig.disabled = false;
          }
        });
      });
    } catch (e) {
      if (msg) msg.textContent = e.message || String(e);
      if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="muted">불러오기 실패</td></tr>';
    }
  }

  async function saveOpsSettings() {
    const msg = document.getElementById("ops-settings-msg");
    if (msg) msg.textContent = "";
    const rows = [...document.querySelectorAll("#ops-settings-tbody tr[data-sid]")];
    const items = rows.map((tr) => {
      const crit = !!tr.querySelector("[data-crit]")?.checked;
      return {
        id: Number(tr.getAttribute("data-sid")),
        is_critical: crit,
        eligible_for_coverage: crit ? false : !!tr.querySelector("[data-elig]")?.checked,
        cycle_years: Number(tr.querySelector("[data-cycle]")?.value || 5),
        last_witness_date: (tr.querySelector("[data-last]")?.value || "").trim() || null,
      };
    });
    const res = await fetch(API + "/cb-admin/operations/witnessing/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ scheme: opsScheme || qs().get("scheme") || "QMS", items }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "저장 실패");
    }
    if (msg) msg.textContent = "설정이 저장되었습니다.";
    loadOpsSettings();
  }

  async function loadOpsMdRates() {
    const tbody = document.getElementById("ops-md-rate-tbody");
    const msg = document.getElementById("ops-md-rate-msg");
    if (msg) msg.textContent = "";
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4" class="muted">불러오는 중…</td></tr>';
    try {
      const res = await fetch(API + "/cb/standard-accreditations", {
        headers: authHeaders(),
        cache: "no-store",
      });
      const data = await res.json().catch(() => []);
      if (res.status === 403) {
        forceCbLogin(typeof data.detail === "string" ? data.detail : "CB 계정 필요");
        return;
      }
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "MD단가 조회 실패");
      }
      const held = (Array.isArray(data) ? data : []).filter(
        (r) =>
          r.is_active ||
          r.ab_code ||
          r.registration_no ||
          r.expiry_date ||
          r.md_rate != null
      );
      if (!held.length) {
        tbody.innerHTML =
          '<tr><td colspan="4" class="muted">보유 표준이 없습니다. (어드민에서 보유 표준을 먼저 등록하세요)</td></tr>';
        return;
      }
      tbody.innerHTML = held
        .map((r) => {
          const label =
            r.label ||
            [r.initial, r.iso_code || r.standard_code, r.name_kr || r.standard_name]
              .filter(Boolean)
              .join(" · ") ||
            r.standard_code;
          const exp = r.expiry_date ? String(r.expiry_date).slice(0, 10) : "";
          const md =
            r.md_rate != null && r.md_rate !== ""
              ? String(Math.round(Number(r.md_rate)))
              : "";
          return (
            '<tr data-std="' +
            escapeHtml(r.standard_code || "") +
            '" data-ab="' +
            escapeHtml(r.ab_code || "") +
            '" data-reg="' +
            escapeHtml(r.registration_no || "") +
            '" data-exp="' +
            escapeHtml(exp) +
            '" data-active="' +
            (r.is_active ? "1" : "0") +
            '">' +
            "<td><strong>" +
            escapeHtml(label) +
            "</strong></td>" +
            "<td>" +
            escapeHtml(r.registration_no || "—") +
            "</td>" +
            "<td>" +
            escapeHtml(exp || "—") +
            "</td>" +
            '<td><input type="number" class="form-input" min="0" step="1000" data-md-rate value="' +
            escapeHtml(md) +
            '" placeholder="예: 500000" style="min-width:120px;" /></td>' +
            "</tr>"
          );
        })
        .join("");
    } catch (e) {
      if (msg) msg.textContent = e.message || String(e);
      tbody.innerHTML = '<tr><td colspan="4" class="muted">불러오기 실패</td></tr>';
    }
  }

  async function saveOpsMdRates() {
    const msg = document.getElementById("ops-md-rate-msg");
    if (msg) msg.textContent = "";
    const rows = [...document.querySelectorAll("#ops-md-rate-tbody tr[data-std]")];
    if (!rows.length) {
      if (msg) msg.textContent = "저장할 표준이 없습니다.";
      return;
    }
    const items = rows.map((tr) => {
      const raw = (tr.querySelector("[data-md-rate]")?.value || "").trim();
      const md = raw === "" ? null : Number(raw.replace(/,/g, ""));
      if (raw !== "" && (!Number.isFinite(md) || md < 0)) {
        throw new Error("잘못된 MD단가: " + tr.getAttribute("data-std"));
      }
      return {
        standard_code: tr.getAttribute("data-std"),
        ab_code: (tr.getAttribute("data-ab") || "").trim() || null,
        registration_no: (tr.getAttribute("data-reg") || "").trim() || null,
        expiry_date: (tr.getAttribute("data-exp") || "").trim() || null,
        md_rate: md,
        is_active: tr.getAttribute("data-active") === "1" || md != null,
      };
    });
    const res = await fetch(API + "/cb/standard-accreditations", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ items, replace_all: false }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "저장 실패");
    }
    if (msg) msg.textContent = "MD단가가 저장되었습니다.";
    loadOpsMdRates();
  }

  document.addEventListener("click", function (evt) {
    const opsSub = evt.target.closest("[data-ops-sub]");
    if (opsSub && opsSub.classList.contains("ops-sub-btn")) {
      evt.preventDefault();
      switchOpsSub(opsSub.getAttribute("data-ops-sub"));
      return;
    }
    const wcomplete = evt.target.closest("[data-wcomplete]");
    if (wcomplete) {
      evt.preventDefault();
      completeWitnessing(Number(wcomplete.getAttribute("data-wcomplete"))).catch((e) =>
        alert(e.message || String(e))
      );
      return;
    }
    if (evt.target.id === "ops-settings-save") {
      evt.preventDefault();
      saveOpsSettings().catch((e) => {
        const msg = document.getElementById("ops-settings-msg");
        if (msg) msg.textContent = e.message || String(e);
      });
      return;
    }
    if (evt.target.id === "ops-settings-reload") {
      evt.preventDefault();
      loadOpsSettings();
      return;
    }
    if (evt.target.id === "ops-reload-md-rates") {
      evt.preventDefault();
      loadOpsMdRates();
      return;
    }
    if (evt.target.id === "ops-save-md-rates") {
      evt.preventDefault();
      saveOpsMdRates().catch((e) => {
        const msg = document.getElementById("ops-md-rate-msg");
        if (msg) msg.textContent = e.message || String(e);
      });
      return;
    }
    const nav = evt.target.closest(".sidebar-menu-item[data-tab]");
    if (nav) {
      evt.preventDefault();
      switchTab(nav.getAttribute("data-tab"));
      return;
    }
    const pipe = evt.target.closest("[data-pipeline]");
    if (pipe) {
      evt.preventDefault();
      const tab = pipe.getAttribute("data-tab");
      const status = pipe.getAttribute("data-status") || "";
      switchTab(tab, { status: status, keepStatus: true });
      return;
    }
    const calEv = evt.target.closest("[data-cal-idx]");
    if (calEv) {
      evt.preventDefault();
      const idx = Number(calEv.getAttribute("data-cal-idx"));
      if (!Number.isNaN(idx) && calendarEvents[idx]) {
        openAuditModal(calendarEvents[idx]);
      }
      return;
    }
    if (evt.target.closest("[data-close-modal]")) {
      closeAuditModal();
      return;
    }
    if (evt.target.id === "cal-prev") {
      evt.preventDefault();
      calMonth -= 1;
      if (calMonth < 1) {
        calMonth = 12;
        calYear -= 1;
      }
      loadDashboard();
      return;
    }
    if (evt.target.id === "cal-next") {
      evt.preventDefault();
      calMonth += 1;
      if (calMonth > 12) {
        calMonth = 1;
        calYear += 1;
      }
      loadDashboard();
      return;
    }
    const listItem = evt.target.closest(".master-list-item");
    if (listItem) {
      listItem
        .closest(".master-list")
        ?.querySelectorAll(".master-list-item")
        .forEach((el) => el.classList.remove("is-active"));
      listItem.classList.add("is-active");
    }
    const action = evt.target.closest("[data-cb-action]");
    if (action) {
      evt.preventDefault();
      handleAction(action);
    }
  });

  async function handleAction(btn) {
    const action = btn.getAttribute("data-cb-action");
    const contractId = btn.getAttribute("data-contract-id");
    const membershipId = btn.getAttribute("data-membership-id");
    try {
      if (action === "supplement") {
        await postJson(`/cb-admin/verification/${contractId}/request-supplement`);
      } else if (action === "approve-verify") {
        await postJson(`/cb-admin/verification/${contractId}/approve`);
      } else if (action === "issue-cert") {
        await postJson(`/cb-admin/verification/${contractId}/issue-certificate`);
      } else if (action === "approve-membership") {
        const res = await fetch(
          API + `/cb/memberships/${membershipId}/approve`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json", ...authHeaders() },
            body: JSON.stringify({ decision: "approved" }),
          }
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(formatDetail(data.detail) || "승인 실패");
        alert("승인되었습니다.");
        loadMasterList("cpd_mgr", {});
      } else if (action === "reject-membership") {
        const res = await fetch(
          API + `/cb/memberships/${membershipId}/approve`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json", ...authHeaders() },
            body: JSON.stringify({ decision: "rejected" }),
          }
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(formatDetail(data.detail) || "반려 실패");
        alert("반려되었습니다.");
        loadMasterList("cpd_mgr", {});
      }
    } catch (e) {
      alert(e.message || String(e));
    }
  }

  function formatDetail(detail) {
    if (detail == null) return "";
    if (typeof detail === "string") return detail;
    try {
      return JSON.stringify(detail);
    } catch (_) {
      return String(detail);
    }
  }

  async function postJson(path) {
    const res = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 403) {
      forceCbLogin(
        typeof data.detail === "string" ? data.detail : "CB 계정 필요"
      );
      return;
    }
    if (!res.ok) {
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : data.detail
            ? JSON.stringify(data.detail)
            : "요청 실패 (" + res.status + ")"
      );
    }
    return data;
  }

  document.getElementById("logout-btn")?.addEventListener("click", (e) => {
    e.preventDefault();
    clearSession();
    location.href = "/login?next=/cb-portal";
  });

  async function boot() {
    const ok = await sessionGate();
    if (!ok) return;
    const p = qs();
    const rawTab = p.get("tab") || "dashboard";
    const tab = normalizeTab(rawTab);
    opsScheme = p.get("scheme") || "";
    // Redirect legacy finance tabs in the URL bar
    if (rawTab !== tab || (tab === "operations" && !p.get("sub"))) {
      const sub = normalizeOpsSub(p.get("sub"), rawTab);
      setQuery({
        tab: tab,
        sub: tab === "operations" ? sub : "",
        scheme: tab === "operations" ? opsScheme : "",
        status: p.get("status") || "",
      });
    }
    switchTab(tab, {
      status: p.get("status") || undefined,
      auditor_id: p.get("auditor_id") || undefined,
      request_id: p.get("request_id") || undefined,
      id: p.get("id") || undefined,
      sub: normalizeOpsSub(p.get("sub"), rawTab),
      scheme: opsScheme || undefined,
      skipQuery: true,
      keepStatus: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.CbPortal = { switchTab: switchTab, loadDashboard: loadDashboard };
})();
