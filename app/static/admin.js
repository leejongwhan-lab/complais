/* ComplAIs — Platform Admin 대시보드 API 연동
 *
 * 백엔드: app/api/v1/endpoints/admin.py (get_current_admin_user / JWT RBAC)
 * 인증: Authorization: Bearer <access_token>
 */
// Same-origin relative base when served from :8000; override via window.COMPLAIS_API_BASE if needed.
const API_BASE =
  typeof window !== "undefined" && window.COMPLAIS_API_BASE
    ? String(window.COMPLAIS_API_BASE).replace(/\/$/, "")
    : "/api/v1";
const TOKEN_KEY = "access_token";

function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function clearAuthToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem("user_id");
  localStorage.removeItem("user_name");
  localStorage.removeItem("role");
  localStorage.removeItem("cb_id");
  localStorage.removeItem("company_id");
  localStorage.removeItem("client_company_id");
  localStorage.removeItem("membership_status");
}

function redirectToLogin(message) {
  if (window.__adminLoginRedirecting) return;
  window.__adminLoginRedirecting = true;
  const token = localStorage.getItem(TOKEN_KEY);
  // 미로그인 진입은 조용히 로그인으로 이동 (alert 반복 방지)
  if (!token) {
    window.location.replace("/login?next=/admin");
    return;
  }
  if (message) alert(message);
  clearAuthToken();
  window.location.href = "/login?next=/admin";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    redirectToLogin();
    return;
  }

  document.body.addEventListener("htmx:responseError", (e) => {
    const status = e.detail.xhr?.status;
    if (status === 401 || status === 403) {
      redirectToLogin(
        status === 401
          ? "인증이 만료되었습니다. 다시 로그인해주세요."
          : "관리자 권한이 없습니다. platform_admin 계정으로 로그인하세요.",
      );
    }
  });

  const useHtmxCompanies = !!document.getElementById("company-htmx-panel");
  const useHtmxCb = !!document.getElementById("cb-htmx-panel");

  async function authFetch(url, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}`,
      ...options.headers,
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      clearAuthToken();
      redirectToLogin(
        res.status === 401
          ? "인증이 만료되었습니다. 다시 로그인해주세요."
          : "관리자 권한이 없습니다.",
      );
    }
    return res;
  }

  // 2. 사이드바 메뉴 클릭 이벤트 바인딩
  const menuItems = document.querySelectorAll(".sidebar-menu-item");
  const panels = document.querySelectorAll(".tab-panel");

  function showTab(tabName) {
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `tab-${tabName}`);
    });
    menuItems.forEach((m) => {
      m.classList.toggle("active", m.getAttribute("data-tab") === tabName);
    });
    if (tabName) {
      try {
        history.replaceState(null, "", `#${tabName}`);
      } catch (_) {
        /* ignore */
      }
    }
  }

  menuItems.forEach((item) => {
    item.addEventListener("click", (e) => {
      const targetTab = item.getAttribute("data-tab");
      if (!targetTab) return; // 외부 링크(기업 포털 등)는 기본 이동 유지
      e.preventDefault();
      showTab(targetTab);
      loadTabData(targetTab);
    });
  });

  const hashTab = (location.hash || "").replace(/^#/, "");
  if (hashTab && document.getElementById(`tab-${hashTab}`)) {
    showTab(hashTab);
    // loadTabData is defined later — defer via setTimeout after full init
    window.__initialAdminTab = hashTab;
  }

  // 기업 현황 목록 상태
  let companyPage = 1;
  const companyLimit = 10;
  let currentCompaniesData = []; // 현재 로드된 목록 캐싱

  // 심사원 현황 목록 상태
  let auditorPage = 1;
  const auditorLimit = 10;
  let currentAuditorsData = [];

  // app/core/constants.py AUDITOR_GRADE_MAP 과 동기화
  const GRADE_MAP = {
    trainee: "심사원보",
    auditor: "심사원",
    lead_auditor: "선임심사원",
    verified_auditor: "검증심사원",
    // legacy
    senior: "선임심사원",
    verifier: "검증심사원",
  };

  function resolveCorpType(company) {
    if (company.entity_type || company.corp_type) {
      return company.entity_type || company.corp_type;
    }
    const mid = company.biz_no?.split("-")[1] || "";
    // 사업자번호 가운데 자리 8x → 법인 추정
    return mid.startsWith("8") ? "법인" : "개인/기타";
  }

  function gradeLabel(grade) {
    return GRADE_MAP[grade] || grade || "—";
  }

  function employmentLabel(type) {
    if (type === "fulltime") return "정규직";
    if (type === "parttime") return "파트타임";
    return type || "—";
  }

  function genderLabel(gender) {
    if (gender === "M" || gender === "male" || gender === "남") return "남성";
    if (gender === "F" || gender === "female" || gender === "여") return "여성";
    return gender || "—";
  }

  async function loadTabData(tabName) {
    if (tabName === "cb-contracts") {
      if (useHtmxCb && window.htmx) {
        htmx.trigger(document.body, "refresh-cb");
        return;
      }
      await loadCbContracts();
      return;
    }
    if (tabName === "companies") {
      if (useHtmxCompanies && window.htmx) {
        const form = document.getElementById("company-search-form");
        if (form) htmx.trigger(form, "submit");
        return;
      }
      companyPage = 1;
      await fetchCompanies(1);
      return;
    }
    if (tabName === "auditors") {
      auditorPage = 1;
      await fetchAuditors(1);
      return;
    }
    if (tabName === "accreditations") {
      await fetchAccreditationRequests();
      return;
    }
    if (tabName === "dashboard") {
      await loadDashboardStats();
      return;
    }
    if (tabName === "calc-rules") {
      await loadEmissionFactors();
    }
  }

  async function fetchCompanies(page = 1) {
    const keyword = document.getElementById("search-keyword")?.value || "";
    const token = localStorage.getItem("access_token");
    const tbody = document.getElementById("company-table-body");
    companyPage = page;

    if (!token) {
      redirectToLogin("로그인이 필요합니다.");
      return;
    }

    if (tbody) {
      tbody.innerHTML =
        '<tr><td colspan="9" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';
    }

    try {
      const response = await fetch(
        `${API_BASE}/admin/companies?page=${page}&limit=${companyLimit}&keyword=${encodeURIComponent(keyword)}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        },
      );

      if (response.status === 401 || response.status === 403) {
        clearAuthToken();
        redirectToLogin(
          response.status === 401
            ? "인증이 만료되었습니다. 다시 로그인해주세요."
            : "관리자 권한이 없습니다.",
        );
        return;
      }

      if (response.ok) {
        const res = await response.json();
        currentCompaniesData = res.data || [];
        document.getElementById("total-count").innerText = res.total;

        if (!currentCompaniesData.length) {
          tbody.innerHTML =
            '<tr><td colspan="9" style="text-align: center; color: var(--font-tertiary);">검색 결과가 없습니다.</td></tr>';
        } else {
          tbody.innerHTML = currentCompaniesData
            .map((c, i) => {
              const companyId = c.company_id ?? c.id;
              const seq = (companyPage - 1) * companyLimit + i + 1;
              const companyName = c.company_name ?? c.name ?? "";
              const corpType = resolveCorpType(c);
              const websiteUrl = c.website
                ? c.website.startsWith("http")
                  ? c.website
                  : `http://${c.website}`
                : null;
              const held = Array.isArray(c.held_standards) ? c.held_standards : [];
              const heldHtml = held.length
                ? held
                    .slice(0, 6)
                    .map((h) => {
                      const label =
                        (typeof h === "string"
                          ? h
                          : h.label ||
                            [h.iso_code, h.name_kr].filter(Boolean).join(" ") ||
                            h.initial ||
                            h.standard_code) || "";
                      const ab = (typeof h === "object" && h && h.ab_code) || "—";
                      const cb =
                        (typeof h === "object" && h && (h.cb_initial || h.cb_name)) || "—";
                      return escapeHtml(`${label} (AB:${ab} / CB:${cb})`);
                    })
                    .join("<br>") +
                  (held.length > 6
                    ? `<br><span class="muted">+${held.length - 6}</span>`
                    : "")
                : "—";

              return `
        <tr>
          <td>${seq}</td>
          <td class="col-company-name fw-bold" title="${escapeHtml(companyName)}">${escapeHtml(companyName)}</td>
          <td>${escapeHtml(c.biz_no || "-")}</td>
          <td>${escapeHtml(corpType)}</td>
          <td>${escapeHtml(c.ceo_name || "-")}</td>
          <td style="font-size:11px;line-height:1.45;white-space:normal;min-width:160px">${heldHtml}</td>
          <td title="${escapeHtml(c.address_kr || "")}">${escapeHtml(c.address_kr || "-")}</td>
          <td>${websiteUrl ? `<a href="${escapeHtml(websiteUrl)}" target="_blank" rel="noopener" class="text-decoration-none">방문</a>` : "-"}</td>
          <td>
            <button type="button" class="btn-detail" onclick="openDetailModal(${Number(companyId)})">상세정보</button>
          </td>
        </tr>
      `;
            })
            .join("");
        }

        renderCompanyPagination(res.total || 0, res.page || page, res.limit || companyLimit);
      } else {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${response.status})`);
      }
    } catch (error) {
      console.error("Companies fetch failed:", error);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(error.message)})</td></tr>`;
      }
    }
  }

  function renderAdminHeldStandards(held) {
    const body = document.getElementById("ac-held-std-body");
    const countEl = document.getElementById("ac-cert-count");
    const rows = Array.isArray(held) ? held : [];
    if (countEl) countEl.textContent = rows.length ? `(${rows.length})` : "";
    if (!body) return;
    if (!rows.length) {
      body.innerHTML =
        '<tr><td colspan="5" class="muted">등록된 보유 표준이 없습니다.</td></tr>';
      return;
    }
    body.innerHTML = rows
      .map((r) => {
        const label =
          (typeof r === "string"
            ? r
            : r.label ||
              [r.iso_code, r.name_kr].filter(Boolean).join(" ") ||
              r.initial ||
              r.standard_code) || "—";
        const ab = (typeof r === "object" && r && r.ab_code) || "—";
        const cb =
          (typeof r === "object" && r && (r.cb_name || r.cb_initial)) ||
          (typeof r === "object" && r && r.cb_id != null ? `CB#${r.cb_id}` : "—");
        const certNo = (typeof r === "object" && r && r.cert_no) || "—";
        const status = (typeof r === "object" && r && r.status) || "—";
        return `<tr>
          <td>${escapeHtml(label)}</td>
          <td>${escapeHtml(ab)}</td>
          <td>${escapeHtml(cb)}</td>
          <td>${escapeHtml(certNo)}</td>
          <td>${escapeHtml(status)}</td>
        </tr>`;
      })
      .join("");
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value ?? "-";
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

  let currentCompanyDetail = null;
  let currentCompanyId = null;
  let draftDepartments = [];
  let draftSites = [];
  let draftStaff = [];
  let adminEsgPage = 0;
  let adminEsgLimit = 50;
  let adminEsgTotal = 0;
  let adminEsgYears = [];
  let adminEsgStdLoaded = false;
  let adminEsgLoadedFor = null;

  function openCompanyDetailModal() {
    const modal = document.getElementById("companyDetailModal");
    if (!modal) return;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    switchCompanyDetailTab("basic-info");
  }

  function closeCompanyDetailModal() {
    const modal = document.getElementById("companyDetailModal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  function switchCompanyDetailTab(tabId) {
    document.querySelectorAll("#companyDetailTab .nav-link").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-detail-tab") === tabId);
    });
    document.querySelectorAll("#companyDetailTabContent .detail-tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === tabId);
    });
  }

  function fillHeadcountYearSelect(detail) {
    const sel = document.getElementById("ac-headcount_year");
    if (!sel) return;
    const current = new Date().getFullYear();
    const years = Array.isArray(detail.headcount_years) && detail.headcount_years.length
      ? [...detail.headcount_years]
      : [current];
    if (!years.includes(current)) years.unshift(current);
    const selected = detail.headcount_year || current;
    if (!years.includes(selected)) years.unshift(selected);
    sel.innerHTML = years
      .map((y) => `<option value="${y}" ${Number(y) === Number(selected) ? "selected" : ""}>${y}</option>`)
      .join("");
  }

  function bindCompanyDetail(detail) {
    currentCompanyDetail = detail;
    currentCompanyId = detail.company_id ?? detail.id;
    const companyName = detail.company_name || detail.name || "기업";
    setText("modal-company-title", `${companyName} 상세 정보`);
    setInputValue("ac-id", currentCompanyId);
    setInputValue("ac-id-display", currentCompanyId);
    setInputValue("ac-status", detail.status || "정상");
    setInputValue("ac-name", companyName);
    setInputValue("ac-name_en", detail.name_en);
    setInputValue("ac-biz_no", detail.biz_no);
    setInputValue("ac-entity_type", detail.entity_type || "");
    setInputValue("ac-corp_no", detail.corp_no);
    setInputValue("ac-ceo_name", detail.ceo_name);
    setInputValue("ac-biz_type", detail.biz_type);
    setInputValue("ac-biz_class", detail.biz_class);
    setInputValue("ac-ksic_code", detail.ksic_code);
    setInputValue("ac-iaf_code", detail.iaf_code);
    setInputValue("ac-tel", detail.tel);
    setInputValue("ac-email", detail.email);
    setInputValue("ac-website", detail.website);
    setInputValue("ac-address", detail.address);
    setInputValue("ac-detail_address", detail.detail_address);
    setInputValue("ac-address_en", detail.address_en);
    setInputValue("ac-scope_kr", detail.scope_kr);
    setInputValue("ac-scope_en", detail.scope_en);

    fillHeadcountYearSelect(detail);
    setInputValue("ac-employee_count", detail.employee_count ?? "");
    setInputValue("ac-headcount_outsourced", detail.headcount_outsourced ?? "");
    setInputValue("ac-headcount_regular", detail.headcount_regular ?? "");
    setInputValue("ac-headcount_non_regular", detail.headcount_non_regular ?? "");

    draftSites = (detail.sites || []).map((s) => ({ ...s }));
    draftDepartments = (detail.departments || []).map((d) => d.name);
    draftStaff = (detail.staff || []).map((s) => ({ ...s }));
    renderAdminSites();
    renderAdminDepartments();
    renderAdminStaff();
    renderAdminHeldStandards(detail.held_standards || []);
    ["ac-basic-msg", "ac-headcount-msg", "ac-site-msg", "ac-dept-msg", "ac-staff-msg"].forEach((id) =>
      setOrgMsg(id, ""),
    );
  }

  async function fetchCompanyDetail(id, headcountYear) {
    let url = `${API_BASE}/admin/companies/${id}`;
    if (headcountYear) url += `?headcount_year=${encodeURIComponent(headcountYear)}`;
    const res = await authFetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `상세 조회 실패 (HTTP ${res.status})`);
    }
    return res.json();
  }

  function resetAdminEsgPanel() {
    adminEsgPage = 0;
    adminEsgTotal = 0;
    adminEsgYears = [];
    adminEsgStdLoaded = false;
    adminEsgLoadedFor = null;
    const tabCount = document.getElementById("ac-esg-tab-count");
    if (tabCount) tabCount.textContent = "";
    const meta = document.getElementById("ac-esg-meta");
    if (meta) meta.textContent = "";
    const tbody = document.getElementById("ac-esg-tbody");
    if (tbody) {
      tbody.innerHTML =
        '<tr><td colspan="10" class="muted">불러오는 중…</td></tr>';
    }
    const pag = document.getElementById("ac-esg-pagination");
    if (pag) pag.innerHTML = "";
    setOrgMsg("ac-esg-msg", "");
  }

  function adminEsgPathLabel(row) {
    if (row?.data_path_label) return row.data_path_label;
    if (row?.input_mode === "public") return "공공연동";
    if (row?.input_mode === "auditor") return "심사노트";
    if (row?.input_mode === "company") return "직접입력";
    return "—";
  }

  function adminEsgFmtVal(v) {
    if (v == null || v === "") return '<span class="ac-esg-empty">-</span>';
    return escapeHtml(String(v));
  }

  function adminEsgTrendHtml(trend) {
    if (!trend || trend.pct == null) return '<span class="ac-esg-empty">-</span>';
    const dir = trend.direction || "flat";
    const arrow = dir === "up" ? "↑" : dir === "down" ? "↓" : "→";
    return `<span class="ac-esg-trend ${escapeHtml(dir)}">${arrow} ${escapeHtml(trend.pct)}%</span>`;
  }

  function fillAdminEsgStdOptions(standards) {
    const sel = document.getElementById("ac-esg-std");
    if (!sel || !Array.isArray(standards)) return;
    const current = sel.value;
    sel.innerHTML =
      '<option value="">전체</option>' +
      standards.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join("");
    if (current && standards.includes(current)) sel.value = current;
    adminEsgStdLoaded = true;
  }

  function updateAdminEsgThead(years) {
    const thead = document.getElementById("ac-esg-thead");
    if (!thead) return;
    const y = years?.length ? years : adminEsgYears;
    if (!y?.length) return;
    adminEsgYears = y;
    thead.innerHTML = `<tr>
      <th class="ac-esg-col-kpi">KPI 지표</th>
      <th class="ac-esg-col-path">경로</th>
      <th class="ac-esg-col-unit">단위</th>
      ${y.map((yr) => `<th class="ac-esg-col-year">${yr}년</th>`).join("")}
      <th class="ac-esg-col-trend">추세</th>
      <th class="ac-esg-col-goal">목표</th>
    </tr>`;
  }

  function renderAdminEsgRows(rows, years) {
    const groups = new Map();
    rows.forEach((row) => {
      const key = row.sub_category || "미분류";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    });
    let html = "";
    const colSpan = 3 + years.length + 2;
    for (const [sub, items] of groups) {
      html += `<tr class="ac-esg-group-row"><td colspan="${colSpan}"><strong>${escapeHtml(sub)}</strong> <span class="ac-esg-group-count">(${items.length})</span></td></tr>`;
      items.forEach((row) => {
        const yearCells = years
          .map((yr) => {
            const v = row.year_values ? row.year_values[String(yr)] : null;
            return `<td class="ac-esg-col-year num">${adminEsgFmtVal(v)}</td>`;
          })
          .join("");
        const goal =
          row.goal_value != null && row.goal_value !== ""
            ? escapeHtml(row.goal_value)
            : '<span class="ac-esg-empty">-</span>';
        html += `<tr class="ac-esg-data-row">
          <td class="ac-esg-col-kpi">
            <div class="ac-esg-kpi-cell">
              <span class="ac-esg-kpi-code">${escapeHtml(row.kpi_code || row.esg_category || "")}</span>
              <span class="ac-esg-kpi-name">${escapeHtml(row.kpi_name || "—")}</span>
              ${row.is_required ? '<span class="ac-esg-req">필수</span>' : ""}
            </div>
          </td>
          <td class="ac-esg-col-path">${escapeHtml(adminEsgPathLabel(row))}</td>
          <td class="ac-esg-col-unit">${escapeHtml(row.unit_format || "-")}</td>
          ${yearCells}
          <td class="ac-esg-col-trend">${adminEsgTrendHtml(row.trend)}</td>
          <td class="ac-esg-col-goal">${goal}</td>
        </tr>`;
      });
    }
    return html;
  }

  function renderAdminEsgPagination() {
    const box = document.getElementById("ac-esg-pagination");
    if (!box) return;
    const pages = Math.max(1, Math.ceil(adminEsgTotal / adminEsgLimit));
    const cur = adminEsgPage;
    if (adminEsgTotal <= adminEsgLimit) {
      box.innerHTML = "";
      return;
    }
    let html = `<button type="button" data-ac-esg-page="${cur - 1}" ${cur <= 0 ? "disabled" : ""}>이전</button>`;
    const start = Math.max(0, cur - 2);
    const end = Math.min(pages - 1, start + 4);
    for (let i = start; i <= end; i++) {
      html += `<button type="button" class="${i === cur ? "active" : ""}" data-ac-esg-page="${i}">${i + 1}</button>`;
    }
    html += `<button type="button" data-ac-esg-page="${cur + 1}" ${cur >= pages - 1 ? "disabled" : ""}>다음</button>`;
    box.innerHTML = html;
    box.querySelectorAll("button[data-ac-esg-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = Number(btn.dataset.acEsgPage);
        if (Number.isNaN(p) || p < 0 || p >= pages) return;
        adminEsgPage = p;
        loadAdminCompanyEsg(false);
      });
    });
  }

  async function loadAdminCompanyEsg(resetPage) {
    if (!currentCompanyId) return;
    if (resetPage) adminEsgPage = 0;
    const tbody = document.getElementById("ac-esg-tbody");
    const cat = document.getElementById("ac-esg-cat")?.value || "";
    const std = document.getElementById("ac-esg-std")?.value || "";
    const mode = document.getElementById("ac-esg-mode")?.value || "";
    const q = document.getElementById("ac-esg-q")?.value.trim() || "";
    const heldOnly = !!document.getElementById("ac-esg-held-only")?.checked;
    const params = new URLSearchParams({
      skip: String(adminEsgPage * adminEsgLimit),
      limit: String(adminEsgLimit),
    });
    if (cat) params.set("esg_category", cat);
    if (std) params.set("managed_standard_name", std);
    if (mode) params.set("source_mode", mode);
    if (q) params.set("q", q);
    if (heldOnly) params.set("held_only", "true");

    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="10" class="muted">불러오는 중…</td></tr>';
    }
    setOrgMsg("ac-esg-msg", "");

    try {
      const res = await authFetch(
        `${API_BASE}/admin/companies/${currentCompanyId}/esg-kpis?${params}`,
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `ESG 조회 실패 (HTTP ${res.status})`,
        );
      }

      adminEsgTotal = data.total || 0;
      adminEsgLoadedFor = currentCompanyId;
      const tabCount = document.getElementById("ac-esg-tab-count");
      if (tabCount) tabCount.textContent = adminEsgTotal ? `(${adminEsgTotal})` : "(0)";

      if (!adminEsgStdLoaded && data.available_standards?.length) {
        fillAdminEsgStdOptions(data.available_standards);
      }

      const years = data.years?.length
        ? data.years
        : Array.from({ length: 5 }, (_, i) => (data.current_year || new Date().getFullYear()) - 4 + i);
      updateAdminEsgThead(years);

      const held = (data.held_standards || []).join(", ") || "없음";
      const srcHint = data.data_source === "kpi_master" ? " · 출처 kpi_master" : "";
      const from = adminEsgTotal ? adminEsgPage * adminEsgLimit + 1 : 0;
      const to = Math.min((adminEsgPage + 1) * adminEsgLimit, adminEsgTotal);
      let metaText = data.matched_to_held
        ? `보유 표준(${held}) 매칭 · ${from}–${to} / ${adminEsgTotal}`
        : `전체 카탈로그 · ${from}–${to} / ${adminEsgTotal}`;
      if (data.notice) metaText = data.notice;
      const meta = document.getElementById("ac-esg-meta");
      if (meta) meta.textContent = metaText + (data.notice ? "" : srcHint);

      if (!tbody) return;
      if (!data.data?.length) {
        const emptyMsg =
          data.notice ||
          (heldOnly
            ? "보유 표준에 매칭되는 KPI가 없습니다. 필터를 해제해 보세요."
            : "조회된 ESG KPI가 없습니다.");
        tbody.innerHTML = `<tr><td colspan="${3 + years.length + 2}" class="muted">${escapeHtml(emptyMsg)}</td></tr>`;
        renderAdminEsgPagination();
        return;
      }
      tbody.innerHTML = renderAdminEsgRows(data.data, years);
      renderAdminEsgPagination();
    } catch (error) {
      console.error("Admin ESG load failed:", error);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="10" class="muted">${escapeHtml(error.message || "ESG 조회 실패")}</td></tr>`;
      }
      setOrgMsg("ac-esg-msg", error.message || "ESG 조회 실패", "err");
    }
  }

  async function openDetailModal(id) {
    const cached = currentCompaniesData.find((item) => item.id === id);
    if (cached) setText("modal-company-title", `${cached.company_name || cached.name} 상세 정보`);
    resetAdminEsgPanel();
    openCompanyDetailModal();
    try {
      const detail = await fetchCompanyDetail(id);
      bindCompanyDetail(detail);
      loadAdminCompanyEsg(true);
    } catch (error) {
      console.error("Company detail failed:", error);
      setOrgMsg("ac-basic-msg", error.message || "상세를 불러오지 못했습니다.", "err");
    }
  }

  async function saveCompanyStatus() {
    if (!currentCompanyId) return;
    const statusVal = document.getElementById("ac-status")?.value || "";
    if (!statusVal) throw new Error("상태를 선택하세요.");
    setOrgMsg("ac-basic-msg", "저장 중...");
    const res = await authFetch(`${API_BASE}/admin/companies/${currentCompanyId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: statusVal }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail || err);
      throw new Error(detail || `상태 저장 실패 (HTTP ${res.status})`);
    }
    const detail = await fetchCompanyDetail(currentCompanyId);
    bindCompanyDetail(detail);
    setOrgMsg("ac-basic-msg", "상태 저장 완료", "ok");
    fetchCompanies(companyPage);
  }

  function renderAdminSites() {
    const box = document.getElementById("ac-site-list");
    if (!box) return;
    if (!draftSites.length) {
      box.innerHTML = '<div class="org-empty">등록된 추가사업장이 없습니다.</div>';
      return;
    }
    box.innerHTML = `
      <table class="org-table">
        <thead>
          <tr>
            <th>사업장명</th>
            <th>주소</th>
            <th>상세주소</th>
            <th>영문주소</th>
            <th>인원</th>
            <th>업무유형</th>
          </tr>
        </thead>
        <tbody>
          ${draftSites
            .map(
              (s) => `
            <tr>
              <td>${escapeHtml(s.site_name || "—")}</td>
              <td>${escapeHtml(s.address || "—")}</td>
              <td>${escapeHtml(s.detail_address || "—")}</td>
              <td>${escapeHtml(s.address_en || "—")}</td>
              <td>${escapeHtml(s.employee_count ?? 0)}</td>
              <td>${escapeHtml(s.work_type || "—")}</td>
            </tr>`,
            )
            .join("")}
        </tbody>
      </table>`;
  }

  function renderAdminDepartments() {
    const box = document.getElementById("ac-dept-tags");
    if (!box) return;
    if (!draftDepartments.length) {
      box.innerHTML = '<div class="org-empty">등록된 부서가 없습니다.</div>';
      return;
    }
    box.innerHTML = draftDepartments
      .map((name) => `<span class="dept-tag">${escapeHtml(name)}</span>`)
      .join("");
  }

  function renderAdminStaff() {
    const body = document.getElementById("ac-staff-body");
    if (!body) return;
    if (!draftStaff.length) {
      body.innerHTML = `<tr><td colspan="7" class="org-empty">등록된 담당자가 없습니다.</td></tr>`;
      return;
    }
    body.innerHTML = draftStaff
      .map(
        (s) => `
          <tr>
            <td>${escapeHtml(s.role || "—")}</td>
            <td>${escapeHtml(s.staff_name || "—")}</td>
            <td>${escapeHtml(s.department || "—")}</td>
            <td>${escapeHtml(s.position || "—")}</td>
            <td>${escapeHtml(s.phone || "—")}</td>
            <td>${escapeHtml(s.mobile || "—")}</td>
            <td>${escapeHtml(s.email || "—")}</td>
          </tr>`,
      )
      .join("");
  }

  // 모달 닫기 / 탭 전환
  document.querySelectorAll("[data-modal-close]").forEach((btn) => {
    btn.addEventListener("click", closeCompanyDetailModal);
  });
  const companyModal = document.getElementById("companyDetailModal");
  if (companyModal) {
    companyModal.addEventListener("click", (e) => {
      if (e.target === companyModal) closeCompanyDetailModal();
    });
  }
  document.querySelectorAll("#companyDetailTab [data-detail-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-detail-tab");
      switchCompanyDetailTab(tabId);
      if (tabId === "esg-info" && currentCompanyId && adminEsgLoadedFor !== currentCompanyId) {
        loadAdminCompanyEsg(true);
      }
    });
  });

  document.getElementById("ac-esg-search-btn")?.addEventListener("click", () => loadAdminCompanyEsg(true));
  document.getElementById("ac-esg-q")?.addEventListener("keyup", (e) => {
    if (e.key === "Enter") loadAdminCompanyEsg(true);
  });
  ["ac-esg-cat", "ac-esg-std", "ac-esg-mode", "ac-esg-held-only"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", () => loadAdminCompanyEsg(true));
  });

  document.getElementById("admin-company-basic-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await saveCompanyStatus();
    } catch (err) {
      setOrgMsg("ac-basic-msg", err.message || "상태 저장 실패", "err");
    }
  });

  document.getElementById("admin-company-headcount-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
  });

  document.getElementById("ac-headcount_year")?.addEventListener("change", async () => {
    if (!currentCompanyId) return;
    try {
      const year = document.getElementById("ac-headcount_year")?.value;
      const detail = await fetchCompanyDetail(currentCompanyId, year);
      bindCompanyDetail(detail);
      setOrgMsg("ac-headcount-msg", `${year}년 인원 불러옴`, "ok");
    } catch (err) {
      setOrgMsg("ac-headcount-msg", err.message || "조회 실패", "err");
    }
  });

  window.openDetailModal = openDetailModal;

  const PAGINATION_WINDOW = 5;

  function buildPaginationPageNums(current, totalPages, windowSize = PAGINATION_WINDOW) {
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

  function renderPaginationButtons(el, total, page, limit, onPage) {
    if (!el) return;
    el.classList.add("pagination-container");
    el.classList.remove("pagination");

    const totalPages = Math.max(1, Math.ceil(total / limit));
    const current = Math.min(Math.max(1, page), totalPages);
    const pageNums = buildPaginationPageNums(current, totalPages);
    const buttons = [];

    buttons.push(
      `<button type="button" class="page-btn nav-btn" data-page="${current - 1}" ${current <= 1 ? "disabled" : ""}>‹</button>`,
    );

    let prevP = null;
    pageNums.forEach((p) => {
      if (prevP !== null && p > prevP + 1) {
        buttons.push(`<button type="button" class="page-btn nav-btn" disabled>…</button>`);
      }
      buttons.push(
        `<button type="button" class="page-btn${p === current ? " active" : ""}" data-page="${p}">${p}</button>`,
      );
      prevP = p;
    });

    buttons.push(
      `<button type="button" class="page-btn nav-btn" data-page="${current + 1}" ${current >= totalPages ? "disabled" : ""}>›</button>`,
    );

    el.innerHTML = buttons.join("");
    el.querySelectorAll("button[data-page]:not(:disabled)").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = Number(btn.getAttribute("data-page"));
        if (!Number.isNaN(next) && next >= 1 && next <= totalPages) onPage(next);
      });
    });
  }

  function renderCompanyPagination(total, page, limit) {
    renderPaginationButtons(document.getElementById("pagination"), total, page, limit, fetchCompanies);
  }

  const searchBtn = document.getElementById("search-companies-btn");
  const searchInput = document.getElementById("search-keyword");
  if (!useHtmxCompanies && searchBtn) searchBtn.addEventListener("click", () => fetchCompanies(1));
  if (!useHtmxCompanies && searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        fetchCompanies(1);
      }
    });
  }

  // onclick="fetchCompanies()" 호환
  window.fetchCompanies = () => fetchCompanies(1);

  async function fetchAuditors(page = 1) {
    const keyword = document.getElementById("auditor-search-keyword")?.value || "";
    const token = localStorage.getItem("access_token");
    const tbody = document.getElementById("auditor-table-body");
    auditorPage = page;

    if (!token) {
      redirectToLogin("로그인이 필요합니다.");
      return;
    }

    if (tbody) {
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';
    }

    try {
      const response = await fetch(
        `${API_BASE}/admin/auditors?page=${page}&limit=${auditorLimit}&keyword=${encodeURIComponent(keyword)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );

      if (response.status === 401 || response.status === 403) {
        clearAuthToken();
        redirectToLogin(
          response.status === 401
            ? "인증이 만료되었습니다. 다시 로그인해주세요."
            : "관리자 권한이 없습니다.",
        );
        return;
      }

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${response.status})`);
      }

      const res = await response.json();
      currentAuditorsData = res.data || [];
      const totalEl = document.getElementById("auditor-total-count");
      if (totalEl) totalEl.innerText = res.total ?? 0;

      if (!currentAuditorsData.length) {
        tbody.innerHTML =
          '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">검색 결과가 없습니다.</td></tr>';
      } else {
        tbody.innerHTML = currentAuditorsData
          .map(
            (a, i) => {
              const seq = (auditorPage - 1) * auditorLimit + i + 1;
              return `
        <tr>
          <td>${seq}</td>
          <td class="fw-bold">${escapeHtml(a.name || "—")}</td>
          <td>${escapeHtml(a.email || "—")}</td>
          <td>${escapeHtml(a.phone || "—")}</td>
          <td>${escapeHtml(gradeLabel(a.grade))}</td>
          <td>${escapeHtml(employmentLabel(a.employment_type))}</td>
          <td>${a.is_freelance ? "프리랜서" : "—"}</td>
          <td>
            <button type="button" class="btn-detail" onclick="openAuditorDetailModal(${Number(a.id)})">상세</button>
          </td>
        </tr>`;
            },
          )
          .join("");
      }

      renderAuditorPagination(res.total || 0, res.page || page, res.limit || auditorLimit);
    } catch (error) {
      console.error("Auditors fetch failed:", error);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(error.message)})</td></tr>`;
      }
    }
  }

  function renderAuditorPagination(total, page, limit) {
    renderPaginationButtons(
      document.getElementById("auditor-pagination"),
      total,
      page,
      limit,
      fetchAuditors,
    );
  }

  /* ---- 심사원 상세정보 (CB 상세정보와 동일 UX) ---- */
  const auditorDetailState = { editingId: null };

  function membershipStatusLabel(status) {
    const map = {
      requested: "신청",
      under_review: "검토중",
      approved: "승인",
      rejected: "반려",
      terminated: "종료",
      suspended: "정지",
      expired: "만료",
    };
    return map[status] || status || "—";
  }

  function renderAffiliationsPlain(affiliations, membershipsFallback) {
    const el = document.getElementById("aud-membership-list");
    if (!el) return;
    const rows =
      Array.isArray(affiliations) && affiliations.length
        ? affiliations
        : (membershipsFallback || []).map((m) => ({
            cb_id: m.cb_id,
            cb_name: m.cb_name,
            cb_code: m.cb_code,
            status: m.status,
            is_primary: m.is_primary,
          }));
    if (!rows.length) {
      el.textContent = "소속 인증기관 없음";
      return;
    }
    // 소속만 표시 — 계약형태·수수료·근무조건 등 계약관계 필드 제외
    el.innerHTML = rows
      .map((m) => {
        const cbLabel = m.cb_name
          ? `${m.cb_name}${m.cb_code ? ` (${m.cb_code})` : ""}`
          : `CB #${m.cb_id}`;
        const status = membershipStatusLabel(m.status);
        const primary = m.is_primary ? " · 주소속" : "";
        return `<div class="history-item" style="margin-bottom:8px;">
          <strong>${escapeHtml(cbLabel)}</strong>
          <small>${escapeHtml(status)}${primary}</small>
        </div>`;
      })
      .join("");
  }

  function renderExternalCertsPlain(certs) {
    const el = document.getElementById("aud-external-certs");
    if (!el) return;
    if (!certs.length) {
      el.textContent = "—";
      return;
    }
    el.innerHTML = certs
      .map(
        (c) => `<div class="history-item" style="margin-bottom:6px;">
          <strong>${escapeHtml(c.cert_name || "—")} · ${escapeHtml(gradeLabel(c.grade))}</strong>
          <small>${escapeHtml(c.issuer || "—")} · ${escapeHtml(c.cert_no || "—")} · ${escapeHtml(c.issued_date || "—")} ~ ${escapeHtml(c.expiry_date || "—")}</small>
        </div>`,
      )
      .join("");
  }

  function renderEduList(educations) {
    const el = document.getElementById("aud-edu-list");
    if (!el) return;
    if (!educations.length) {
      el.textContent = "—";
      return;
    }
    el.innerHTML = educations
      .map(
        (e) => `
      <div class="history-item">
        <strong>${escapeHtml(e.school_name)} · ${escapeHtml(e.degree)}</strong>
        <small>전공: ${escapeHtml(e.major || "—")} · ${escapeHtml(e.entered_at || "—")} ~ ${escapeHtml(e.graduated_at || "—")}</small>
      </div>`,
      )
      .join("");
  }

  function renderCareerList(careers) {
    const el = document.getElementById("aud-career-list");
    if (!el) return;
    if (!careers.length) {
      el.textContent = "—";
      return;
    }
    el.innerHTML = careers
      .map(
        (c) => `
      <div class="history-item">
        <strong>${escapeHtml(c.company_name)} · ${escapeHtml(c.position || "—")}</strong>
        <small>${escapeHtml(c.start_date || "—")} ~ ${c.is_current ? "재직중" : escapeHtml(c.end_date || "—")}${c.note ? ` · ${escapeHtml(c.note)}` : ""}</small>
      </div>`,
      )
      .join("");
  }

  function profileStatusLabel(status) {
    const map = {
      pending: "대기",
      submitted: "제출",
      reviewing: "검토중",
      approved: "승인",
      rejected: "반려",
      active: "활성",
    };
    return map[status] || status || "—";
  }

  function fillAuditorDetailForm(profile = {}) {
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val == null || val === "" ? "" : String(val);
    };
    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = dashText(val);
    };

    setText("aud-f-id", profile.id);
    set("aud-f-complais-no", profile.complais_no);
    set("aud-f-name", profile.name);
    set("aud-f-name-en", profile.name_en);
    set("aud-f-birth", profile.birth_date ? String(profile.birth_date).slice(0, 10) : "");
    set("aud-f-gender", profile.gender === "male" ? "M" : profile.gender === "female" ? "F" : profile.gender || "");
    set("aud-f-reg-no", profile.registration_no);
    set("aud-f-status", profile.status || "");
    setText("aud-f-profile-status", profileStatusLabel(profile.profile_status));
    setText(
      "aud-f-is-active",
      profile.is_active == null ? "—" : profile.is_active ? "활성" : "비활성",
    );
    setText("aud-f-created", fmtDateOnly(profile.created_at));
    setText("aud-f-updated", fmtDateOnly(profile.updated_at));

    set("aud-f-email", profile.email);
    set("aud-f-phone", profile.phone);
    set("aud-f-address", profile.address);
    set("aud-f-address-detail", profile.detail_address);

    // grade select: map legacy senior → keep value so option matches
    set("aud-f-grade", profile.grade || "");
    set("aud-f-iaf", profile.iaf_codes);
    set("aud-f-edu-level", profile.education_level);
    set("aud-f-school", profile.school_name);
    set("aud-f-major", profile.major);

    set("aud-f-emp-type", profile.employment_type || "");
    set(
      "aud-f-freelance",
      profile.is_freelance == null ? "" : profile.is_freelance ? "true" : "false",
    );
    // 계약관계(계약형태·수수료·주소속 단일표기)는 상세 UI에서 숨김 — 소속은 affiliations 목록 사용

    set("aud-f-bank", profile.bank_name);
    set("aud-f-account", profile.account_no);
    set("aud-f-holder", profile.account_holder);
    set("aud-f-career-summary", profile.career_summary);
    set("aud-f-intro", profile.intro);
  }

  async function openAuditorDetailModal(id) {
    try {
      const response = await authFetch(`${API_BASE}/admin/auditors/${id}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `상세 조회 실패 (HTTP ${response.status})`,
        );
      }
      const profile = data.profile || {};
      auditorDetailState.editingId = id;
      const titleEl = document.getElementById("auditor-detail-modal-title");
      const subEl = document.getElementById("auditor-detail-modal-sub");
      if (titleEl) titleEl.textContent = "심사원 상세정보";
      if (subEl) {
        subEl.textContent = `${profile.name || "—"} · ${gradeLabel(profile.grade)}`;
      }
      fillAuditorDetailForm(profile);
      renderAffiliationsPlain(data.affiliations || [], data.memberships || []);
      renderExternalCertsPlain(data.external_certs || []);
      renderEduList(data.educations || []);
      renderCareerList(data.careers || []);
      const err = document.getElementById("auditor-detail-modal-error");
      if (err) err.textContent = "";
      setOrgMsg("auditor-action-msg", "");
      showModal("auditorDetailModal", true);
    } catch (error) {
      console.error("Auditor detail fetch failed:", error);
      alert(error.message || "심사원 상세를 불러오지 못했습니다.");
    }
  }

  function closeAuditorDetailModal() {
    showModal("auditorDetailModal", false);
    auditorDetailState.editingId = null;
  }

  document.querySelectorAll("[data-auditor-modal-close]").forEach((btn) => {
    btn.addEventListener("click", closeAuditorDetailModal);
  });
  const auditorModal = document.getElementById("auditorDetailModal");
  if (auditorModal) {
    auditorModal.addEventListener("click", (e) => {
      if (e.target.id === "auditorDetailModal") closeAuditorDetailModal();
    });
  }

  async function refreshAuditorDetailAfterAction() {
    if (!auditorDetailState.editingId) return;
    const response = await authFetch(
      `${API_BASE}/admin/auditors/${auditorDetailState.editingId}`,
    );
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(
        typeof data.detail === "string" ? data.detail : `상세 조회 실패 (HTTP ${response.status})`,
      );
    }
    const profile = data.profile || {};
    fillAuditorDetailForm(profile);
    renderAffiliationsPlain(data.affiliations || [], data.memberships || []);
    renderExternalCertsPlain(data.external_certs || []);
    renderEduList(data.educations || []);
    renderCareerList(data.careers || []);
    const subEl = document.getElementById("auditor-detail-modal-sub");
    if (subEl) subEl.textContent = `${profile.name || "—"} · ${gradeLabel(profile.grade)}`;
    await fetchAuditors(auditorPage);
  }

  async function postAuditorAction(path, body, successMsg) {
    const err = document.getElementById("auditor-detail-modal-error");
    if (err) err.textContent = "";
    if (!auditorDetailState.editingId) return;
    setOrgMsg("auditor-action-msg", "처리 중...");
    const opts = { method: "PATCH" };
    if (body) opts.body = JSON.stringify(body);
    const res = await authFetch(
      `${API_BASE}/admin/auditors/${auditorDetailState.editingId}${path}`,
      opts,
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail =
        typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
      throw new Error(detail || `처리 실패 (HTTP ${res.status})`);
    }
    await refreshAuditorDetailAfterAction();
    setOrgMsg("auditor-action-msg", successMsg, "ok");
  }

  document.getElementById("auditor-status-save")?.addEventListener("click", async () => {
    try {
      const statusVal = (document.getElementById("aud-f-status")?.value || "").trim();
      if (!statusVal) throw new Error("상태를 선택하세요.");
      await postAuditorAction("/status", { status: statusVal }, "상태 저장 완료");
    } catch (error) {
      setOrgMsg("auditor-action-msg", error.message || "상태 저장 실패", "err");
      const err = document.getElementById("auditor-detail-modal-error");
      if (err) err.textContent = error.message || "상태 저장 실패";
    }
  });

  const searchAuditorsBtn = document.getElementById("search-auditors-btn");
  const searchAuditorsInput = document.getElementById("auditor-search-keyword");
  if (searchAuditorsBtn) searchAuditorsBtn.addEventListener("click", () => fetchAuditors(1));
  if (searchAuditorsInput) {
    searchAuditorsInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        fetchAuditors(1);
      }
    });
  }

  window.fetchAuditors = () => fetchAuditors(1);
  window.openAuditorDetailModal = openAuditorDetailModal;

  async function refreshCbContractsList() {
    if (useHtmxCb && window.htmx) {
      htmx.trigger(document.body, "refresh-cb");
      return;
    }
    await loadCbContracts();
  }

  async function loadCbContracts() {
    const tbody = document.getElementById("cb-contracts-tbody");
    if (!tbody) return;
    tbody.innerHTML =
      '<tr><td colspan="9" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';

    try {
      const res = await authFetch(`${API_BASE}/admin/cb-contracts?skip=0&limit=100&ensure_missing=false`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${res.status})`);
      }
      const data = await res.json();
      renderCbContractsTable(data);
    } catch (error) {
      console.error("CB contracts fetch failed:", error);
      tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(error.message)})</td></tr>`;
    }
  }

  function renderCbContractsTable(records) {
    const tbody = document.getElementById("cb-contracts-tbody");
    if (!tbody) return;

    if (!records || records.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">등록된 인증기관이 없습니다.</td></tr>';
      return;
    }

    const fmtMoney = (v) => {
      if (v == null || v === "") return "-";
      const n = Number(v);
      return Number.isFinite(n) ? n.toLocaleString("ko-KR") : String(v);
    };

    tbody.innerHTML = records
      .map((r, i) => {
        const cbId = r.cb_id ?? r.id;
        const seq = (typeof r._seq === "number" ? r._seq : i + 1);
        const stds = Array.isArray(r.held_standards) ? r.held_standards : [];
        const heldCell = stds.length
          ? `<div class="held-std-cell">${stds
              .map(
                (ini) =>
                  `<button type="button" class="held-std-link" data-cb-held="${cbId}" data-std-initial="${escapeHtml(ini)}" title="${escapeHtml(ini)} 인정·인증수행범위">${escapeHtml(ini)}</button>`,
              )
              .join("")}</div>`
          : "—";
        const abDisplay = r.ab_summary || r.accreditation_body || "-";
        return `
        <tr>
          <td>${seq}</td>
          <td>${escapeHtml(r.cb_code || "-")}</td>
          <td class="col-cb-name fw-bold" title="${escapeHtml(r.cb_name)}">${escapeHtml(r.cb_name)}</td>
          <td>${escapeHtml(r.cb_status || "-")}</td>
          <td class="col-held-std">${heldCell}</td>
          <td>${escapeHtml(abDisplay)}</td>
          <td>${fmtMoney(r.annual_base_fee)}</td>
          <td>
            <button type="button" class="btn-detail" data-cb-detail="${cbId}">상세정보</button>
          </td>
        </tr>`;
      })
      .join("");
  }

  /* ---- CB 상세정보 (목록에 없는 필드) / 보유 표준·IAF 팝업 ---- */
  const cbDetailState = {
    editingId: null,
    accreditationBody: "KAB",
    cbInitial: null,
    cbCode: "",
    cbName: "",
    status: "active",
    contractYear: new Date().getFullYear(),
    // CB-level legacy (상세정보에서 편집 제거 — 저장 시 기존값 유지)
    legacyRegNo: null,
    legacyExpireDate: null,
  };

  const cbHeldState = {
    cbId: null,
    familyInitial: null,
  };

  function showModal(id, show) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.toggle("show", !!show);
    modal.setAttribute("aria-hidden", show ? "false" : "true");
  }

  function dashText(v) {
    if (v == null) return "—";
    const s = String(v).trim();
    return s ? s : "—";
  }

  function fmtDateOnly(v) {
    if (!v) return "—";
    const s = String(v).trim();
    if (!s) return "—";
    return s.slice(0, 10);
  }

  function fillCbDetailForm(d = {}) {
    cbDetailState.accreditationBody = d.accreditation_body || "KAB";
    cbDetailState.cbInitial = d.cb_initial || null;
    cbDetailState.cbCode = d.cb_code || d.code || "";
    cbDetailState.cbName = d.cb_name || d.name || "";
    cbDetailState.status = d.status || "active";
    const contract = d.contract || {};
    cbDetailState.contractYear = contract.contract_year || new Date().getFullYear();

    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val == null || val === "" ? "" : String(val);
    };
    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = dashText(val);
    };

    cbDetailState.legacyRegNo = d.reg_no || null;
    cbDetailState.legacyExpireDate = d.expire_date || null;

    set("cb-f-name-en", d.cb_name_en || d.name_en);
    set("cb-f-initial", d.cb_initial);
    set("cb-f-biz", d.biz_reg_no || d.biz_no);
    set("cb-f-corp", d.corp_no);
    set("cb-f-personal", d.personal_no);
    set("cb-f-ceo", d.ceo_name);
    set("cb-f-acc-region", d.accreditation_region);
    set("cb-f-acc-country", d.accreditation_country);
    setText("cb-f-activated", fmtDateOnly(d.activated_at));
    setText("cb-f-eval-score", d.evaluation_score);

    set("cb-f-tel", d.tel);
    set("cb-f-fax", d.fax);
    set("cb-f-email", d.email);
    set("cb-f-tax-email", d.tax_email);
    set("cb-f-web", d.website);
    set("cb-f-zip", "");
    set("cb-f-address", d.address);
    set("cb-f-address-detail", "");

    set("cb-f-bank", d.bank_name);
    set("cb-f-account", d.account_no);
    set("cb-f-holder", d.account_holder);
    set("cb-f-tier", contract.tier || "MEDIUM");
    set("cb-f-base-fee", contract.annual_base_fee != null ? contract.annual_base_fee : "");
    setText("cb-f-contract-year", contract.contract_year || cbDetailState.contractYear);
    const start = fmtDateOnly(contract.contract_start_date);
    const end = fmtDateOnly(contract.contract_end_date);
    setText(
      "cb-f-contract-period",
      start === "—" && end === "—" ? "—" : `${start} ~ ${end}`,
    );

    set("cb-f-intro", d.intro);
  }

  async function openCbDetailModal(cbId) {
    try {
      const res = await authFetch(`${API_BASE}/admin/certification-bodies/${cbId}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `상세 조회 실패 (HTTP ${res.status})`);
      }
      cbDetailState.editingId = cbId;
      document.getElementById("cb-detail-modal-title").textContent = "상세정보";
      document.getElementById("cb-detail-modal-sub").textContent =
        `${data.cb_name || "—"} · ${data.cb_code || "—"}`;
      fillCbDetailForm(data);
      const err = document.getElementById("cb-detail-modal-error");
      if (err) err.textContent = "";
      showModal("cbDetailModal", true);
    } catch (error) {
      alert(error.message || "상세 조회에 실패했습니다.");
    }
  }

  function closeCbDetailModal() {
    showModal("cbDetailModal", false);
    cbDetailState.editingId = null;
  }

  function formatIafPlain(codes) {
    /** IAF/scope codes as plain dark text — never badge/chip HTML. e.g. "1 2 3 4 5 6 7" */
    if (!Array.isArray(codes) || !codes.length) return "—";
    return codes
      .map((c) => {
        const s = String(c ?? "").trim();
        if (!s) return "";
        // display 01 → 1 for IAF39 numeric codes
        if (/^\d+$/.test(s)) return String(parseInt(s, 10));
        return s;
      })
      .filter(Boolean)
      .join(" ");
  }

  async function openCbHeldStandardsModal(cbId, familyInitial = null) {
    const tbody = document.getElementById("cb-held-tbody");
    const errEl = document.getElementById("cb-held-modal-error");
    if (errEl) errEl.textContent = "";
    cbHeldState.cbId = cbId;
    cbHeldState.familyInitial = familyInitial;
    if (tbody) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--font-tertiary);">불러오는 중…</td></tr>';
    }
    showModal("cbHeldStandardsModal", true);
    try {
      const res = await authFetch(`${API_BASE}/admin/certification-bodies/${cbId}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `조회 실패 (HTTP ${res.status})`);
      }
      const ini = (familyInitial || "").trim();
      const titleEl = document.getElementById("cb-held-modal-title");
      const subEl = document.getElementById("cb-held-modal-sub");
      if (titleEl) {
        titleEl.textContent = ini ? `${ini} · 인정·인증수행범위` : "보유 표준 · 인정·인증수행범위";
      }
      if (subEl) {
        subEl.textContent = `${data.cb_code || ""} · ${data.cb_name || ""}`;
      }
      let rows = Array.isArray(data.held_scope_rows) ? data.held_scope_rows : [];
      if (ini) {
        const want = ini.toUpperCase();
        rows = rows.filter((r) => String(r.family_initial || "").toUpperCase() === want);
      }
      if (!tbody) return;
      if (!rows.length) {
        tbody.innerHTML =
          '<tr><td colspan="6" style="text-align:center;color:var(--font-tertiary);">해당 표준의 보유 정보가 없습니다.</td></tr>';
        return;
      }
      tbody.innerHTML = rows
        .map((r) => {
          const iaf = formatIafPlain(r.iaf_codes);
          const exp = r.expiry_date ? String(r.expiry_date).slice(0, 10) : "";
          const md =
            r.md_rate != null && r.md_rate !== ""
              ? Number(r.md_rate).toLocaleString("ko-KR")
              : "—";
          const warn =
            r.expiry_warning ||
            (r.expiry_status === "warn" || r.expiry_status === "locked"
              ? `만료 ${r.days_remaining != null ? `D-${r.days_remaining}` : ""}`
              : "");
          const warnHtml = warn
            ? `<div style="font-size:12px;margin-top:4px;color:${
                r.expiry_status === "locked" ? "var(--sec-red)" : "var(--font-secondary)"
              };">${escapeHtml(warn)}</div>`
            : "";
          return `<tr data-std="${escapeHtml(r.standard_code || "")}" data-ab="${escapeHtml(r.ab_code || "")}">
            <td><strong>${escapeHtml(r.family_initial)}</strong></td>
            <td>${escapeHtml(r.standard_code || "")}${r.standard_name ? `<div style="font-size:12px;color:var(--font-secondary);">${escapeHtml(r.standard_name)}</div>` : ""}</td>
            <td><input type="text" data-held-reg class="form-input" value="${escapeHtml(r.registration_no || "")}" placeholder="인정번호" style="width:100%;min-width:100px;" /></td>
            <td><input type="date" data-held-exp class="form-input" value="${escapeHtml(exp)}" style="width:100%;min-width:130px;" />${warnHtml}</td>
            <td><span class="muted" title="CB 포털에서만 수정 가능">${escapeHtml(md)}</span></td>
            <td><span class="iaf-plain">${escapeHtml(iaf)}</span></td>
          </tr>`;
        })
        .join("");
    } catch (error) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--sec-red);">${escapeHtml(error.message)}</td></tr>`;
      }
    }
  }

  function closeCbHeldStandardsModal() {
    showModal("cbHeldStandardsModal", false);
    cbHeldState.cbId = null;
    cbHeldState.familyInitial = null;
  }

  async function saveCbHeldStandards() {
    const errEl = document.getElementById("cb-held-modal-error");
    if (errEl) errEl.textContent = "";
    if (!cbHeldState.cbId) return;
    const rows = [...document.querySelectorAll("#cb-held-tbody tr[data-std]")];
    if (!rows.length) {
      if (errEl) errEl.textContent = "저장할 표준 행이 없습니다.";
      return;
    }
    const items = rows.map((tr) => {
      const std = tr.getAttribute("data-std") || "";
      const ab = (tr.getAttribute("data-ab") || "").trim() || null;
      const reg = (tr.querySelector("[data-held-reg]")?.value || "").trim() || null;
      const exp = (tr.querySelector("[data-held-exp]")?.value || "").trim() || null;
      return {
        standard_code: std,
        ab_code: ab,
        registration_no: reg,
        expiry_date: exp,
        is_active: true,
      };
    }).filter((it) => it.standard_code);
    const saveBtn = document.getElementById("cb-held-save");
    try {
      if (saveBtn) saveBtn.disabled = true;
      const res = await authFetch(
        `${API_BASE}/admin/certification-bodies/${cbHeldState.cbId}/standard-accreditations`,
        {
          method: "PUT",
          body: JSON.stringify({ items, replace_all: false }),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : `저장 실패 (HTTP ${res.status})`);
      }
      closeCbHeldStandardsModal();
      await refreshCbContractsList();
    } catch (error) {
      if (errEl) errEl.textContent = error.message || "저장에 실패했습니다.";
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  window.openCbDetailModal = openCbDetailModal;
  window.openCbHeldStandardsModal = openCbHeldStandardsModal;
  // 하위 호환
  window.openCbDetailScopeModal = openCbDetailModal;

  document.body.addEventListener("click", (e) => {
    const heldBtn = e.target.closest("[data-cb-held]");
    if (heldBtn) {
      e.preventDefault();
      const id = Number(heldBtn.getAttribute("data-cb-held"));
      const initial = heldBtn.getAttribute("data-std-initial") || null;
      if (id) openCbHeldStandardsModal(id, initial);
      return;
    }
    const detailBtn = e.target.closest("[data-cb-detail]");
    if (detailBtn && document.getElementById("cbDetailModal")) {
      e.preventDefault();
      const id = Number(detailBtn.getAttribute("data-cb-detail"));
      if (id) openCbDetailModal(id);
    }
  });

  document.querySelectorAll("[data-cb-detail-close]").forEach((btn) => {
    btn.addEventListener("click", closeCbDetailModal);
  });
  document.querySelectorAll("[data-cb-held-close]").forEach((btn) => {
    btn.addEventListener("click", closeCbHeldStandardsModal);
  });
  const cbHeldSave = document.getElementById("cb-held-save");
  if (cbHeldSave) {
    cbHeldSave.addEventListener("click", () => {
      saveCbHeldStandards();
    });
  }
  const cbDetailModal = document.getElementById("cbDetailModal");
  if (cbDetailModal) {
    cbDetailModal.addEventListener("click", (e) => {
      if (e.target.id === "cbDetailModal") closeCbDetailModal();
    });
  }
  const cbHeldModal = document.getElementById("cbHeldStandardsModal");
  if (cbHeldModal) {
    cbHeldModal.addEventListener("click", (e) => {
      if (e.target.id === "cbHeldStandardsModal") closeCbHeldStandardsModal();
    });
  }

  if (window.ComplaisValidation) {
    ComplaisValidation.bindField(document.getElementById("cb-f-biz"), "biz");
    ComplaisValidation.bindField(document.getElementById("cb-f-tel"), "phone");
    ComplaisValidation.bindField(document.getElementById("cb-f-email"), "email");
    ComplaisValidation.bindField(document.getElementById("cb-f-tax-email"), "email");
  }

  const cbDetailSave = document.getElementById("cb-detail-save");
  if (cbDetailSave) {
    cbDetailSave.addEventListener("click", async () => {
      const err = document.getElementById("cb-detail-modal-error");
      if (err) err.textContent = "";
      if (!cbDetailState.editingId) return;
      if (window.ComplaisValidation) {
        const v = ComplaisValidation.validateFields([
          { el: document.getElementById("cb-f-biz"), kind: "biz", required: false },
          { el: document.getElementById("cb-f-tel"), kind: "phone", required: false },
          { el: document.getElementById("cb-f-email"), kind: "email", required: false },
          { el: document.getElementById("cb-f-tax-email"), kind: "email", required: false },
        ]);
        if (!v.ok) {
          if (err) err.textContent = v.message;
          return;
        }
      }
      const val = (id) => (document.getElementById(id)?.value || "").trim();
      const numOrNull = (id) => {
        const raw = val(id);
        if (!raw) return null;
        const n = Number(raw);
        return Number.isFinite(n) ? n : null;
      };
      const payload = {
        cb_code: cbDetailState.cbCode,
        cb_name: cbDetailState.cbName,
        cb_name_en: val("cb-f-name-en") || null,
        cb_initial: val("cb-f-initial") || cbDetailState.cbInitial,
        accreditation_body: cbDetailState.accreditationBody || "KAB",
        // 인정번호·만료일은 표준별(보유 표준 모달). CB 레거시 값은 유지.
        reg_no: cbDetailState.legacyRegNo,
        expire_date: cbDetailState.legacyExpireDate,
        biz_reg_no: val("cb-f-biz") || null,
        corp_no: val("cb-f-corp") || null,
        personal_no: val("cb-f-personal") || null,
        ceo_name: val("cb-f-ceo") || null,
        email: val("cb-f-email") || null,
        tax_email: val("cb-f-tax-email") || null,
        website: val("cb-f-web") || null,
        tel: val("cb-f-tel") || null,
        fax: val("cb-f-fax") || null,
        address: (() => {
          const base = val("cb-f-address") || "";
          const detail = val("cb-f-address-detail") || "";
          const joined = [base, detail].filter(Boolean).join(" ").trim();
          return joined || null;
        })(),
        bank_name: val("cb-f-bank") || null,
        account_no: val("cb-f-account") || null,
        account_holder: val("cb-f-holder") || null,
        accreditation_region: val("cb-f-acc-region") || null,
        accreditation_country: val("cb-f-acc-country") || null,
        intro: val("cb-f-intro") || null,
        status: cbDetailState.status,
        contract: {
          contract_year: cbDetailState.contractYear,
          tier: val("cb-f-tier") || "MEDIUM",
          annual_base_fee: numOrNull("cb-f-base-fee"),
          // MD단가는 어드민 미관리 — 미전송 시 기존 DB 값 유지
        },
      };
      try {
        cbDetailSave.disabled = true;
        const res = await authFetch(
          `${API_BASE}/admin/certification-bodies/${cbDetailState.editingId}`,
          { method: "PUT", body: JSON.stringify(payload) },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(typeof data.detail === "string" ? data.detail : `저장 실패 (HTTP ${res.status})`);
        }
        closeCbDetailModal();
        await refreshCbContractsList();
      } catch (error) {
        if (err) err.textContent = error.message;
      } finally {
        cbDetailSave.disabled = false;
      }
    });
  }

  function renderAccreditationTable(records) {
    const tbody = document.getElementById("accreditation-tbody");
    if (!tbody) return;

    if (!records || records.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" style="text-align: center; color: var(--font-tertiary);">대기 중인 승인 요청이 없습니다.</td></tr>';
      return;
    }

    tbody.innerHTML = records
      .map((r) => {
        const codes = (r.scopes || []).map((s) => s.iaf_code).filter(Boolean);
        const plain = formatIafPlain(codes);
        const scopesText =
          plain === "—"
            ? "-"
            : plain
                .split(/\s+/)
                .filter(Boolean)
                .map((c) => `IAF ${escapeHtml(c)}`)
                .join(" ");
        const fileCell = r.certificate_file_url
          ? `<a href="${escapeHtml(r.certificate_file_url)}" style="color: var(--sec-blue);" target="_blank" rel="noopener">파일 보기</a>`
          : "-";
        return `
          <tr>
            <td style="font-weight: var(--font-weight-semibold);">${escapeHtml(r.cb_name)}</td>
            <td>${escapeHtml(r.accreditation_body)}</td>
            <td>${scopesText}</td>
            <td>${fileCell}</td>
            <td>${escapeHtml(r.status)}</td>
            <td>
              <button type="button" class="btn-detail" data-approve="${r.id}">승인</button>
              <button type="button" class="btn-secondary" data-reject="${r.id}">반려</button>
            </td>
          </tr>`;
      })
      .join("");

    tbody.querySelectorAll("[data-approve]").forEach((btn) => {
      btn.addEventListener("click", () => approveAccreditation(Number(btn.getAttribute("data-approve"))));
    });
    tbody.querySelectorAll("[data-reject]").forEach((btn) => {
      btn.addEventListener("click", () => rejectAccreditation(Number(btn.getAttribute("data-reject"))));
    });
  }

  async function fetchAccreditationRequests() {
    const tbody = document.getElementById("accreditation-tbody");
    try {
      const res = await authFetch(`${API_BASE}/admin/accreditations?status=PENDING`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${res.status})`);
      }
      const data = await res.json();
      renderAccreditationTable(data);
    } catch (err) {
      console.error("Accreditation fetch failed:", err);
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(err.message)})</td></tr>`;
      }
    }
  }

  async function approveAccreditation(recordId) {
    if (!confirm("해당 인증기관의 인정서 및 요청 ISO 범위를 승인하시겠습니까?")) return;
    try {
      const res = await authFetch(`${API_BASE}/admin/accreditations/${recordId}/approve`, {
        method: "PATCH",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${res.status})`);
      }
      alert("승인 완료되었습니다.");
      fetchAccreditationRequests();
    } catch (err) {
      alert(`승인 처리 중 오류가 발생했습니다.\n${err.message}`);
    }
  }

  async function rejectAccreditation(recordId) {
    if (!confirm("해당 인증기관의 인정서를 반려하시겠습니까?")) return;
    const reason = window.prompt("반려 사유를 입력하세요 (선택):", "");
    if (reason === null) return;

    try {
      const res = await authFetch(`${API_BASE}/admin/accreditations/${recordId}/reject`, {
        method: "PATCH",
        body: JSON.stringify({ reject_reason: reason || null }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${res.status})`);
      }
      alert("반려 처리되었습니다.");
      fetchAccreditationRequests();
    } catch (err) {
      alert(`반려 처리 중 오류가 발생했습니다.\n${err.message}`);
    }
  }

  function formatKRW(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "₩0";
    return `₩${Math.round(n).toLocaleString("ko-KR")}`;
  }

  function applyRevenue(r) {
    const set = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = formatKRW(val);
    };
    set("rev-total", r.total);
    set("rev-cb-sub", r.cb_subscription);
    set("rev-consulting", r.consulting_subscription);
    set("rev-education", r.education_matching_ads);
    set("rev-promotion", r.company_promotion_fees);
    const cur = document.getElementById("rev-currency-label");
    if (cur) cur.textContent = `${r.currency || "KRW"} · 연간`;
  }

  async function loadDashboardRevenue() {
    try {
      const res = await authFetch(`${API_BASE}/admin/revenue`);
      if (!res.ok) return;
      applyRevenue(await res.json());
    } catch (err) {
      console.error("Dashboard revenue failed:", err);
    }
  }

  let monitoringCache = {
    ongoing_audits_count: 0,
    active_auditors_count: 0,
    ongoing_audits: [],
    active_auditors: [],
  };

  function applyMonitoringCounts(data) {
    monitoringCache = {
      ongoing_audits_count: Number(data?.ongoing_audits_count) || 0,
      active_auditors_count: Number(data?.active_auditors_count) || 0,
      ongoing_audits: Array.isArray(data?.ongoing_audits) ? data.ongoing_audits : [],
      active_auditors: Array.isArray(data?.active_auditors) ? data.active_auditors : [],
    };
    const auditsEl = document.getElementById("monitor-ongoing-audits-count");
    if (auditsEl) auditsEl.textContent = `${monitoringCache.ongoing_audits_count} 건`;
    const auditorsEl = document.getElementById("monitor-active-auditors-count");
    if (auditorsEl) auditorsEl.textContent = `${monitoringCache.active_auditors_count} 명`;
  }

  function closeMonitoringModal() {
    showModal("monitoringDetailModal", false);
  }

  function openMonitoringModal(panel) {
    const titleEl = document.getElementById("monitoring-modal-title");
    const subEl = document.getElementById("monitoring-modal-sub");
    const thead = document.getElementById("monitoring-detail-thead");
    const tbody = document.getElementById("monitoring-detail-tbody");
    if (!thead || !tbody) return;

    const isAudits = panel === "audits";
    if (titleEl) titleEl.textContent = isAudits ? "진행중인 심사" : "활동중인 심사원";
    if (subEl) {
      subEl.textContent = isAudits
        ? `총 ${monitoringCache.ongoing_audits_count}건`
        : `총 ${monitoringCache.active_auditors_count}명`;
    }

    if (isAudits) {
      thead.innerHTML = `
        <tr>
          <th style="width:28%;">기업명</th>
          <th style="width:28%;">심사표준</th>
          <th style="width:22%;">심사유형</th>
          <th style="width:22%;">심사형태</th>
        </tr>`;
      const rows = monitoringCache.ongoing_audits;
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--font-tertiary);">진행 중인 심사 없음</td></tr>`;
      } else {
        tbody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${escapeHtml(r.company_name || "—")}</td>
            <td>${escapeHtml(r.standard || "—")}</td>
            <td>${escapeHtml(r.audit_type || "—")}</td>
            <td>${escapeHtml(r.audit_form || "—")}</td>
          </tr>`
          )
          .join("");
      }
    } else {
      thead.innerHTML = `
        <tr>
          <th style="width:28%;">심사원명</th>
          <th style="width:18%;">팀장</th>
          <th style="width:18%;">팀원</th>
          <th style="width:18%;">참관</th>
          <th style="width:18%;">기술전문가</th>
        </tr>`;
      const rows = monitoringCache.active_auditors;
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--font-tertiary);">활동 중인 심사원 없음 · 연동 예정</td></tr>`;
      } else {
        tbody.innerHTML = rows
          .map(
            (r) => `
          <tr>
            <td>${escapeHtml(r.auditor_name || "—")}</td>
            <td>${escapeHtml(r.role_lead || "—")}</td>
            <td>${escapeHtml(r.role_member || "—")}</td>
            <td>${escapeHtml(r.role_observer || "—")}</td>
            <td>${escapeHtml(r.role_tech_expert || "—")}</td>
          </tr>`
          )
          .join("");
      }
    }

    showModal("monitoringDetailModal", true);
  }

  async function loadDashboardMonitoring() {
    try {
      const res = await authFetch(`${API_BASE}/admin/monitoring`);
      if (!res.ok) {
        applyMonitoringCounts({
          ongoing_audits_count: 0,
          active_auditors_count: 0,
          ongoing_audits: [],
          active_auditors: [],
        });
        return;
      }
      applyMonitoringCounts(await res.json());
    } catch (err) {
      console.error("Dashboard monitoring failed:", err);
      applyMonitoringCounts({
        ongoing_audits_count: 0,
        active_auditors_count: 0,
        ongoing_audits: [],
        active_auditors: [],
      });
    }
  }

  document.querySelectorAll("[data-monitor-panel]").forEach((btn) => {
    btn.addEventListener("click", () => {
      openMonitoringModal(btn.getAttribute("data-monitor-panel"));
    });
  });
  document.querySelectorAll("[data-monitoring-modal-close]").forEach((btn) => {
    btn.addEventListener("click", closeMonitoringModal);
  });
  const monitoringModal = document.getElementById("monitoringDetailModal");
  if (monitoringModal) {
    monitoringModal.addEventListener("click", (e) => {
      if (e.target === monitoringModal) closeMonitoringModal();
    });
  }

  async function loadDashboardStats() {
    try {
      const [statsRes] = await Promise.all([
        authFetch(`${API_BASE}/admin/stats`),
        loadDashboardRevenue(),
        loadDashboardMonitoring(),
      ]);
      if (statsRes.ok) {
        const s = await statsRes.json();
        const cbEl = document.getElementById("stat-cb");
        if (cbEl) cbEl.textContent = `${s.cb_count ?? 0} 개`;
        const companyEl = document.getElementById("stat-companies");
        if (companyEl) companyEl.textContent = `${s.company_count ?? 0} 개사`;
        const auditorEl = document.getElementById("stat-auditors");
        if (auditorEl) auditorEl.textContent = `${s.auditor_count ?? 0} 명`;
        const pendingEl = document.getElementById("stat-pending");
        if (pendingEl) pendingEl.textContent = `${s.pending_accreditation_count ?? 0} 건`;
        return;
      }

      // fallback: 기존 개별 API
      const [pendingRes, companiesRes, auditorsRes, cbRes] = await Promise.all([
        authFetch(`${API_BASE}/admin/accreditations?status=PENDING&limit=100`),
        authFetch(`${API_BASE}/admin/companies?page=1&limit=1`),
        authFetch(`${API_BASE}/admin/auditors?page=1&limit=1`),
        authFetch(`${API_BASE}/admin/cb-contracts?skip=0&limit=100`),
      ]);
      if (cbRes.ok) {
        const cbs = await cbRes.json();
        const el = document.getElementById("stat-cb");
        if (el) el.textContent = `${cbs.length} 개`;
      }
      if (pendingRes.ok) {
        const pending = await pendingRes.json();
        const el = document.getElementById("stat-pending");
        if (el) el.textContent = `${pending.length} 건`;
      }
      if (companiesRes.ok) {
        const companies = await companiesRes.json();
        const el = document.getElementById("stat-companies");
        if (el) el.textContent = `${companies.total ?? 0} 개사`;
      }
      if (auditorsRes.ok) {
        const auditors = await auditorsRes.json();
        const el = document.getElementById("stat-auditors");
        if (el) el.textContent = `${auditors.total ?? 0} 명`;
      }
    } catch (err) {
      console.error("Dashboard stats failed:", err);
    }
  }

  // ── 배출계수 마스터 ──────────────────────────────────────────
  const efState = {
    year: new Date().getFullYear(),
    gwp_ch4: 27.9,
    gwp_n2o: 273,
    items: [],
    yearsFilled: false,
  };

  function fillEfYearSelects() {
    if (efState.yearsFilled) return;
    const cur = new Date().getFullYear();
    const years = [];
    for (let y = cur + 1; y >= 2020; y--) years.push(y);
    const sel = document.getElementById("ef-year-sel");
    const from = document.getElementById("copy-from");
    const to = document.getElementById("copy-to");
    [sel, from, to].forEach((el) => {
      if (!el) return;
      el.innerHTML = years
        .map((y) => `<option value="${y}">${y}년</option>`)
        .join("");
    });
    if (sel) sel.value = String(efState.year);
    if (from) from.value = String(efState.year);
    if (to) to.value = String(efState.year + 1);
    efState.yearsFilled = true;
  }

  function fmtFactor(n, digits = 8) {
    const v = Number(n || 0);
    if (!Number.isFinite(v)) return "—";
    return String(Number(v.toFixed(digits)));
  }

  function computeLocalTotal(co2, ch4, n2o) {
    return (
      Number(co2 || 0) +
      Number(ch4 || 0) * Number(efState.gwp_ch4) +
      Number(n2o || 0) * Number(efState.gwp_n2o)
    );
  }

  function refreshEfmTotal() {
    const total = computeLocalTotal(
      document.getElementById("efm-co2")?.value,
      document.getElementById("efm-ch4")?.value,
      document.getElementById("efm-n2o")?.value,
    );
    const el = document.getElementById("efm-total");
    if (el) el.value = total.toFixed(8);
    const f = document.getElementById("efm-formula");
    if (f) {
      f.textContent = `tCO₂eq = CO₂ + CH₄×${efState.gwp_ch4} + N₂O×${efState.gwp_n2o}`;
    }
  }

  function openModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("show");
    el.setAttribute("aria-hidden", "false");
  }
  function closeModal(id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("show");
    el.setAttribute("aria-hidden", "true");
  }

  async function loadEmissionFactors() {
    fillEfYearSelects();
    const year =
      parseInt(document.getElementById("ef-year-sel")?.value, 10) ||
      efState.year;
    efState.year = year;
    const tbody = document.getElementById("ef-tbody");
    if (tbody) {
      tbody.innerHTML =
        '<tr><td colspan="12" style="text-align:center;color:var(--font-tertiary);">불러오는 중…</td></tr>';
    }
    try {
      const res = await authFetch(
        `${API_BASE}/admin/emission-factors?year=${year}`,
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      efState.gwp_ch4 = data.gwp_ch4;
      efState.gwp_n2o = data.gwp_n2o;
      efState.items = data.items || [];
      const gwpLabel = document.getElementById("ef-gwp-label");
      if (gwpLabel) {
        gwpLabel.textContent = `GWP — CH₄ ${data.gwp_ch4} · N₂O ${data.gwp_n2o}`;
      }
      const meta = document.getElementById("ef-meta");
      if (meta) {
        meta.textContent = `${year}년 · ${data.total || 0}개 · 수정 즉시 기업 탄소계산에 반영`;
      }
      renderEfTable();
    } catch (err) {
      console.error("emission factors load failed", err);
      if (tbody) {
        tbody.innerHTML =
          '<tr><td colspan="12" style="text-align:center;color:var(--sec-red);">불러오기 실패</td></tr>';
      }
    }
  }

  function renderEfTable() {
    const tbody = document.getElementById("ef-tbody");
    if (!tbody) return;
    const rows = efState.items;
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="12" style="text-align:center;color:var(--font-tertiary);padding:28px;">
        ${efState.year}년 배출계수가 없습니다. 전년도에서 복사하거나 신규 추가하세요.
      </td></tr>`;
      return;
    }
    tbody.innerHTML = rows
      .map((r) => {
        const total =
          r.total_ghg_factor != null
            ? Number(r.total_ghg_factor)
            : computeLocalTotal(r.factor_co2, r.factor_ch4, r.factor_n2o);
        const scope =
          r.scope_type == 1
            ? "S1"
            : r.scope_type == 2
              ? "S2"
              : r.scope_type == 3
                ? "S3"
                : "—";
        const active = r.is_active
          ? '<span class="badge" style="background:#ecfdf5;color:#047857;">활성</span>'
          : '<span class="badge" style="background:#fef2f2;color:#b91c1c;">비활성</span>';
        return `<tr data-ef-id="${r.id}">
          <td>${escapeHtml(r.fuel_category || "—")}</td>
          <td>${escapeHtml(r.fuel_subcategory || "—")}</td>
          <td><strong>${escapeHtml(r.fuel_name)}</strong><div class="muted" style="font-size:11px;">${escapeHtml(r.fuel_code)}</div></td>
          <td>${escapeHtml(r.unit_input || "—")}</td>
          <td style="text-align:right;font-variant-numeric:tabular-nums;">${fmtFactor(r.factor_co2)}</td>
          <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--font-secondary);">${fmtFactor(r.factor_ch4)}</td>
          <td style="text-align:right;font-variant-numeric:tabular-nums;color:var(--font-secondary);">${fmtFactor(r.factor_n2o)}</td>
          <td style="text-align:right;font-weight:700;font-variant-numeric:tabular-nums;">${total.toFixed(6)}</td>
          <td style="font-size:12px;">${escapeHtml(r.source_name || r.source || "—")}</td>
          <td style="text-align:center;">${scope}</td>
          <td style="text-align:center;" id="efst-${r.id}">${active}</td>
          <td style="white-space:nowrap;">
            <button type="button" class="btn-secondary btn-sm" data-ef-edit="${r.id}">편집</button>
            <button type="button" class="btn-secondary btn-sm" data-ef-toggle="${r.id}">${r.is_active ? "비활성" : "활성화"}</button>
          </td>
        </tr>`;
      })
      .join("");
  }

  function openEfModal(row) {
    document.getElementById("efm-error").textContent = "";
    document.getElementById("ef-edit-title").textContent = row
      ? "배출계수 편집"
      : "신규 배출계수 추가";
    document.getElementById("efm-id").value = row ? row.id : 0;
    const codeEl = document.getElementById("efm-code");
    codeEl.value = row?.fuel_code || "";
    codeEl.disabled = !!row;
    document.getElementById("efm-name").value = row?.fuel_name || "";
    document.getElementById("efm-cat").value = row?.fuel_category || "";
    document.getElementById("efm-sub").value = row?.fuel_subcategory || "";
    document.getElementById("efm-ftype").value = row?.fuel_type || "fossil_fuel";
    document.getElementById("efm-scope").value = String(row?.scope_type || 1);
    document.getElementById("efm-unit").value = row?.unit_input || "";
    document.getElementById("efm-year").value = row?.factor_year || efState.year;
    document.getElementById("efm-co2").value =
      row?.factor_co2 != null ? row.factor_co2 : "";
    document.getElementById("efm-ch4").value = row?.factor_ch4 ?? 0;
    document.getElementById("efm-n2o").value = row?.factor_n2o ?? 0;
    document.getElementById("efm-src").value = row?.source_name || "";
    document.getElementById("efm-active").checked =
      row ? !!row.is_active : true;
    refreshEfmTotal();
    openModal("efEditModal");
  }

  async function saveEfModal() {
    const id = parseInt(document.getElementById("efm-id").value, 10) || 0;
    const payload = {
      fuel_code: document.getElementById("efm-code").value.trim(),
      fuel_name: document.getElementById("efm-name").value.trim(),
      fuel_category: document.getElementById("efm-cat").value.trim(),
      fuel_subcategory: document.getElementById("efm-sub").value.trim(),
      fuel_type: document.getElementById("efm-ftype").value,
      scope_type: parseInt(document.getElementById("efm-scope").value, 10) || 1,
      unit_input: document.getElementById("efm-unit").value.trim(),
      factor_year: parseInt(document.getElementById("efm-year").value, 10),
      factor_co2: document.getElementById("efm-co2").value,
      factor_ch4: document.getElementById("efm-ch4").value || "0",
      factor_n2o: document.getElementById("efm-n2o").value || "0",
      source_name: document.getElementById("efm-src").value.trim(),
      is_active: document.getElementById("efm-active").checked,
    };
    const errEl = document.getElementById("efm-error");
    if (!payload.fuel_name || payload.factor_co2 === "" || !payload.factor_year) {
      errEl.textContent = "연료명, 적용연도, CO₂ 계수는 필수입니다.";
      return;
    }
    if (!id && !payload.fuel_code) {
      errEl.textContent = "연료코드는 필수입니다.";
      return;
    }
    try {
      const url = id
        ? `${API_BASE}/admin/emission-factors/${id}`
        : `${API_BASE}/admin/emission-factors`;
      const res = await authFetch(url, {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        errEl.textContent = data.detail || "저장 실패";
        return;
      }
      closeModal("efEditModal");
      if (payload.factor_year) {
        document.getElementById("ef-year-sel").value = String(
          payload.factor_year,
        );
      }
      await loadEmissionFactors();
    } catch (e) {
      errEl.textContent = "저장 중 오류";
    }
  }

  document.getElementById("ef-year-sel")?.addEventListener("change", () => {
    loadEmissionFactors();
  });
  document.getElementById("ef-add-btn")?.addEventListener("click", () => {
    openEfModal(null);
  });
  document.getElementById("efm-save")?.addEventListener("click", saveEfModal);
  ["efm-co2", "efm-ch4", "efm-n2o"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", refreshEfmTotal);
  });
  document.querySelectorAll("[data-ef-modal-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal("efEditModal"));
  });
  document.getElementById("ef-gwp-btn")?.addEventListener("click", () => {
    document.getElementById("gwp-ch4-inp").value = efState.gwp_ch4;
    document.getElementById("gwp-n2o-inp").value = efState.gwp_n2o;
    openModal("efGwpModal");
  });
  document.querySelectorAll("[data-ef-gwp-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal("efGwpModal"));
  });
  document.getElementById("gwp-save-btn")?.addEventListener("click", async () => {
    const ch4 = parseFloat(document.getElementById("gwp-ch4-inp").value);
    const n2o = parseFloat(document.getElementById("gwp-n2o-inp").value);
    if (!(ch4 > 0) || !(n2o > 0)) {
      alert("유효한 GWP 값을 입력하세요.");
      return;
    }
    const res = await authFetch(`${API_BASE}/admin/gwp-settings`, {
      method: "PUT",
      body: JSON.stringify({ gwp_ch4: ch4, gwp_n2o: n2o }),
    });
    if (!res.ok) {
      alert("GWP 저장 실패");
      return;
    }
    closeModal("efGwpModal");
    await loadEmissionFactors();
  });
  document.getElementById("ef-copy-btn")?.addEventListener("click", () => {
    fillEfYearSelects();
    document.getElementById("copy-from").value = String(efState.year);
    document.getElementById("copy-to").value = String(efState.year + 1);
    openModal("efCopyModal");
  });
  document.querySelectorAll("[data-ef-copy-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal("efCopyModal"));
  });
  document.getElementById("ef-copy-run")?.addEventListener("click", async () => {
    const from_year = parseInt(document.getElementById("copy-from").value, 10);
    const to_year = parseInt(document.getElementById("copy-to").value, 10);
    const res = await authFetch(`${API_BASE}/admin/emission-factors/copy`, {
      method: "POST",
      body: JSON.stringify({ from_year, to_year }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      alert(data.detail || "복사 실패");
      return;
    }
    closeModal("efCopyModal");
    document.getElementById("ef-year-sel").value = String(to_year);
    await loadEmissionFactors();
    alert(`${from_year}년 → ${to_year}년 복사 완료 (${data.copied || 0}개)`);
  });
  document.getElementById("ef-tbody")?.addEventListener("click", async (e) => {
    const editId = e.target.closest("[data-ef-edit]")?.getAttribute("data-ef-edit");
    const toggleId = e.target
      .closest("[data-ef-toggle]")
      ?.getAttribute("data-ef-toggle");
    if (editId) {
      const row = efState.items.find((r) => String(r.id) === String(editId));
      if (row) openEfModal(row);
      return;
    }
    if (toggleId) {
      const res = await authFetch(
        `${API_BASE}/admin/emission-factors/${toggleId}/toggle`,
        { method: "PATCH" },
      );
      if (res.ok) await loadEmissionFactors();
    }
  });

  // 초기 탭 (해시 deep-link 지원: #cb-contracts)
  const initialTab = window.__initialAdminTab || "dashboard";
  if (initialTab !== "dashboard") {
    showTab(initialTab);
  }
  loadTabData(initialTab);
});
