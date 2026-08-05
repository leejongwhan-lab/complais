/* ComplAIs — Platform Admin 대시보드 API 연동
 *
 * 백엔드: app/api/v1/endpoints/admin.py (get_current_admin_user / JWT RBAC)
 * 인증: Authorization: Bearer <access_token>
 */
const API_BASE = "/api/v1";
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
  alert(message || "관리자 권한이 없거나 인증이 만료되었습니다.");
  window.location.href = "/login.html";
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    redirectToLogin("로그인이 필요합니다.");
    return;
  }

  // 1. 공통 JWT Fetch 함수
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
    return GRADE_MAP[grade] || grade || "-";
  }

  function employmentLabel(type) {
    if (type === "fulltime") return "정규직";
    if (type === "parttime") return "파트타임";
    return type || "-";
  }

  function genderLabel(gender) {
    if (gender === "M" || gender === "male" || gender === "남") return "남성";
    if (gender === "F" || gender === "female" || gender === "여") return "여성";
    return gender || "-";
  }

  // 3. 탭별 API 호출 분기
  async function loadTabData(tabName) {
    if (tabName === "cb-contracts") {
      await loadCbContracts();
      return;
    }
    if (tabName === "companies") {
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
        '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';
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
            '<tr><td colspan="8" style="text-align: center; color: var(--font-tertiary);">검색 결과가 없습니다.</td></tr>';
        } else {
          tbody.innerHTML = currentCompaniesData
            .map((c) => {
              const corpType = resolveCorpType(c);
              const websiteUrl = c.website
                ? c.website.startsWith("http")
                  ? c.website
                  : `http://${c.website}`
                : null;
              const badgeClass =
                corpType === "법인"
                  ? "badge bg-primary-subtle text-primary"
                  : "badge bg-secondary-subtle text-secondary";

              return `
        <tr>
          <td>${escapeHtml(c.id)}</td>
          <td class="fw-bold text-start text-truncate" style="max-width: 180px;" title="${escapeHtml(c.name)}">${escapeHtml(c.name)}</td>
          <td>${escapeHtml(c.biz_no || "-")}</td>
          <td><span class="${badgeClass}">${escapeHtml(corpType)}</span></td>
          <td>${escapeHtml(c.ceo_name || "-")}</td>
          <td class="text-start text-truncate" style="max-width: 250px;" title="${escapeHtml(c.address_kr || "")}">${escapeHtml(c.address_kr || "-")}</td>
          <td>${websiteUrl ? `<a href="${escapeHtml(websiteUrl)}" target="_blank" rel="noopener" class="text-decoration-none">방문</a>` : "-"}</td>
          <td>
            <button type="button" class="btn-detail" onclick="openDetailModal(${Number(c.id)})">상세</button>
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
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(error.message)})</td></tr>`;
      }
    }
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
    currentCompanyId = detail.id;
    setText("modal-company-title", `${detail.name || "기업"} 상세 정보`);
    setInputValue("ac-id", detail.id);
    setInputValue("ac-id-display", detail.id);
    setInputValue("ac-status", detail.status || "정상");
    setInputValue("ac-name", detail.name);
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

  async function openDetailModal(id) {
    const cached = currentCompaniesData.find((item) => item.id === id);
    if (cached) setText("modal-company-title", `${cached.name} 상세 정보`);
    openCompanyDetailModal();
    try {
      const detail = await fetchCompanyDetail(id);
      bindCompanyDetail(detail);
    } catch (error) {
      console.error("Company detail failed:", error);
      setOrgMsg("ac-basic-msg", error.message || "상세를 불러오지 못했습니다.", "err");
    }
  }

  function collectBasicPayload() {
    const numOrNull = (v) => {
      if (v === "" || v == null) return null;
      const n = Number(v);
      return Number.isFinite(n) ? n : null;
    };
    return {
      name: document.getElementById("ac-name")?.value?.trim() || null,
      name_en: document.getElementById("ac-name_en")?.value?.trim() || null,
      biz_no: document.getElementById("ac-biz_no")?.value?.trim() || null,
      corp_no: document.getElementById("ac-corp_no")?.value?.trim() || null,
      entity_type: document.getElementById("ac-entity_type")?.value || null,
      ceo_name: document.getElementById("ac-ceo_name")?.value?.trim() || null,
      biz_type: document.getElementById("ac-biz_type")?.value?.trim() || null,
      biz_class: document.getElementById("ac-biz_class")?.value?.trim() || null,
      scope_kr: document.getElementById("ac-scope_kr")?.value?.trim() || null,
      scope_en: document.getElementById("ac-scope_en")?.value?.trim() || null,
      address: document.getElementById("ac-address")?.value?.trim() || null,
      detail_address: document.getElementById("ac-detail_address")?.value?.trim() || null,
      address_en: document.getElementById("ac-address_en")?.value?.trim() || null,
      tel: document.getElementById("ac-tel")?.value?.trim() || null,
      email: document.getElementById("ac-email")?.value?.trim() || null,
      website: document.getElementById("ac-website")?.value?.trim() || null,
      ksic_code: document.getElementById("ac-ksic_code")?.value?.trim() || null,
      iaf_code: document.getElementById("ac-iaf_code")?.value?.trim() || null,
      status: document.getElementById("ac-status")?.value || null,
      employee_count: numOrNull(document.getElementById("ac-employee_count")?.value),
      headcount_outsourced: numOrNull(document.getElementById("ac-headcount_outsourced")?.value),
      headcount_regular: numOrNull(document.getElementById("ac-headcount_regular")?.value),
      headcount_non_regular: numOrNull(document.getElementById("ac-headcount_non_regular")?.value),
      headcount_year: numOrNull(document.getElementById("ac-headcount_year")?.value) || new Date().getFullYear(),
    };
  }

  async function saveCompanyProfile(msgId, includeHeadcount) {
    if (!currentCompanyId) return;
    const body = collectBasicPayload();
    if (!includeHeadcount) {
      delete body.employee_count;
      delete body.headcount_outsourced;
      delete body.headcount_regular;
      delete body.headcount_non_regular;
      delete body.headcount_year;
    }
    setOrgMsg(msgId, "저장 중...");
    const res = await authFetch(`${API_BASE}/admin/companies/${currentCompanyId}`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail || err);
      throw new Error(detail || `저장 실패 (HTTP ${res.status})`);
    }
    const data = await res.json();
    const year = includeHeadcount ? body.headcount_year : undefined;
    const detail = await fetchCompanyDetail(currentCompanyId, year);
    bindCompanyDetail(detail);
    setOrgMsg(msgId, includeHeadcount ? `인원현황 ${data.headcount_year}년 저장 완료` : "기본정보 저장 완료", "ok");
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
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${draftSites
            .map(
              (s, idx) => `
            <tr data-idx="${idx}">
              <td><input data-field="site_name" value="${escapeHtml(s.site_name || "")}" /></td>
              <td><input data-field="address" value="${escapeHtml(s.address || "")}" /></td>
              <td><input data-field="detail_address" value="${escapeHtml(s.detail_address || "")}" /></td>
              <td><input data-field="address_en" value="${escapeHtml(s.address_en || "")}" /></td>
              <td><input data-field="employee_count" type="number" min="0" value="${escapeHtml(s.employee_count ?? 0)}" /></td>
              <td><input data-field="work_type" value="${escapeHtml(s.work_type || "")}" /></td>
              <td><button type="button" class="btn-secondary" data-site-del="${idx}">삭제</button></td>
            </tr>`,
            )
            .join("")}
        </tbody>
      </table>`;
  }

  function syncSitesFromDom() {
    const rows = document.querySelectorAll("#ac-site-list tr[data-idx]");
    rows.forEach((tr) => {
      const idx = Number(tr.getAttribute("data-idx"));
      if (!draftSites[idx]) return;
      tr.querySelectorAll("[data-field]").forEach((input) => {
        const field = input.getAttribute("data-field");
        let val = input.value;
        if (field === "employee_count") val = Number(val || 0);
        draftSites[idx][field] = val;
      });
    });
  }

  async function saveAdminSites() {
    if (!currentCompanyId) return;
    syncSitesFromDom();
    setOrgMsg("ac-site-msg", "저장 중...");
    const existing = (currentCompanyDetail?.sites || []).slice();
    const keepIds = new Set(draftSites.filter((s) => s.id).map((s) => s.id));

    for (const old of existing) {
      if (old.id && !keepIds.has(old.id)) {
        const res = await authFetch(`${API_BASE}/admin/companies/${currentCompanyId}/sites/${old.id}`, {
          method: "DELETE",
        });
        if (!res.ok && res.status !== 204) {
          throw new Error(`사업장 삭제 실패 (HTTP ${res.status})`);
        }
      }
    }

    for (const site of draftSites) {
      const payload = {
        site_name: (site.site_name || "").trim(),
        address: site.address || null,
        detail_address: site.detail_address || null,
        address_en: site.address_en || null,
        biz_no: site.biz_no || null,
        employee_count: Number(site.employee_count || 0),
        is_main: false,
        work_type: site.work_type || null,
      };
      if (!payload.site_name) continue;
      const url = site.id
        ? `${API_BASE}/admin/companies/${currentCompanyId}/sites/${site.id}`
        : `${API_BASE}/admin/companies/${currentCompanyId}/sites`;
      const res = await authFetch(url, {
        method: site.id ? "PUT" : "POST",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `사업장 저장 실패 (HTTP ${res.status})`);
      }
    }

    const detail = await fetchCompanyDetail(currentCompanyId, document.getElementById("ac-headcount_year")?.value);
    bindCompanyDetail(detail);
    setOrgMsg("ac-site-msg", "사업장 저장 완료", "ok");
  }

  function renderAdminDepartments() {
    const box = document.getElementById("ac-dept-tags");
    if (!box) return;
    if (!draftDepartments.length) {
      box.innerHTML = '<div class="org-empty">등록된 부서가 없습니다.</div>';
      return;
    }
    box.innerHTML = draftDepartments
      .map(
        (name, idx) =>
          `<span class="dept-tag">${escapeHtml(name)} <button type="button" data-dept-del="${idx}" aria-label="삭제">×</button></span>`,
      )
      .join("");
  }

  async function saveAdminDepartments() {
    if (!currentCompanyId) return;
    setOrgMsg("ac-dept-msg", "저장 중...");
    const res = await authFetch(`${API_BASE}/admin/companies/${currentCompanyId}/departments/bulk`, {
      method: "PUT",
      body: JSON.stringify({ names: draftDepartments }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `부서 저장 실패 (HTTP ${res.status})`);
    }
    const detail = await fetchCompanyDetail(currentCompanyId, document.getElementById("ac-headcount_year")?.value);
    bindCompanyDetail(detail);
    setOrgMsg("ac-dept-msg", "부서 저장 완료", "ok");
  }

  function renderAdminStaff() {
    const body = document.getElementById("ac-staff-body");
    if (!body) return;
    if (!draftStaff.length) {
      body.innerHTML = `<tr><td colspan="8" class="org-empty">등록된 담당자가 없습니다.</td></tr>`;
      return;
    }
    const deptOptions = draftDepartments
      .map((d) => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`)
      .join("");
    body.innerHTML = draftStaff
      .map((s, idx) => {
        const deptSelect = `
          <select data-field="department">
            <option value="">선택</option>
            ${deptOptions}
          </select>`;
        return `
          <tr data-idx="${idx}">
            <td><input data-field="role" value="${escapeHtml(s.role || "")}" /></td>
            <td><input data-field="staff_name" value="${escapeHtml(s.staff_name || "")}" /></td>
            <td>${deptSelect}</td>
            <td><input data-field="position" value="${escapeHtml(s.position || "")}" /></td>
            <td><input data-field="phone" value="${escapeHtml(s.phone || "")}" /></td>
            <td><input data-field="mobile" value="${escapeHtml(s.mobile || "")}" /></td>
            <td><input data-field="email" value="${escapeHtml(s.email || "")}" /></td>
            <td><button type="button" class="btn-secondary" data-staff-del="${idx}">삭제</button></td>
          </tr>`;
      })
      .join("");
    body.querySelectorAll("tr[data-idx]").forEach((tr) => {
      const idx = Number(tr.getAttribute("data-idx"));
      const sel = tr.querySelector('select[data-field="department"]');
      if (sel) sel.value = draftStaff[idx]?.department || "";
    });
  }

  function syncStaffFromDom() {
    document.querySelectorAll("#ac-staff-body tr[data-idx]").forEach((tr) => {
      const idx = Number(tr.getAttribute("data-idx"));
      if (!draftStaff[idx]) return;
      tr.querySelectorAll("[data-field]").forEach((input) => {
        draftStaff[idx][input.getAttribute("data-field")] = input.value;
      });
    });
  }

  async function saveAdminStaff() {
    if (!currentCompanyId) return;
    syncStaffFromDom();
    setOrgMsg("ac-staff-msg", "저장 중...");
    const items = draftStaff
      .map((s) => ({
        staff_name: (s.staff_name || "").trim(),
        role: s.role || null,
        department: s.department || null,
        position: s.position || null,
        phone: s.phone || null,
        mobile: s.mobile || null,
        email: s.email || null,
      }))
      .filter((s) => s.staff_name);
    const res = await authFetch(`${API_BASE}/admin/companies/${currentCompanyId}/staff/bulk`, {
      method: "PUT",
      body: JSON.stringify({ items }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `담당자 저장 실패 (HTTP ${res.status})`);
    }
    const detail = await fetchCompanyDetail(currentCompanyId, document.getElementById("ac-headcount_year")?.value);
    bindCompanyDetail(detail);
    setOrgMsg("ac-staff-msg", "담당자 저장 완료", "ok");
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
    btn.addEventListener("click", () => switchCompanyDetailTab(btn.getAttribute("data-detail-tab")));
  });

  document.getElementById("admin-company-basic-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await saveCompanyProfile("ac-basic-msg", false);
    } catch (err) {
      setOrgMsg("ac-basic-msg", err.message || "저장 실패", "err");
    }
  });

  document.getElementById("admin-company-headcount-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await saveCompanyProfile("ac-headcount-msg", true);
    } catch (err) {
      setOrgMsg("ac-headcount-msg", err.message || "저장 실패", "err");
    }
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

  document.getElementById("ac-site-add")?.addEventListener("click", () => {
    syncSitesFromDom();
    draftSites.push({
      site_name: "",
      address: "",
      detail_address: "",
      address_en: "",
      employee_count: 0,
      work_type: "",
    });
    renderAdminSites();
  });
  document.getElementById("ac-site-list")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-site-del]");
    if (!btn) return;
    syncSitesFromDom();
    draftSites.splice(Number(btn.getAttribute("data-site-del")), 1);
    renderAdminSites();
  });
  document.getElementById("ac-site-save")?.addEventListener("click", async () => {
    try {
      await saveAdminSites();
    } catch (err) {
      setOrgMsg("ac-site-msg", err.message || "저장 실패", "err");
    }
  });

  document.getElementById("ac-dept-add")?.addEventListener("click", () => {
    const inp = document.getElementById("ac-dept-input");
    const name = (inp?.value || "").trim();
    if (!name) return;
    if (!draftDepartments.some((d) => String(d).toLowerCase() === name.toLowerCase())) {
      draftDepartments.push(name);
    }
    if (inp) inp.value = "";
    renderAdminDepartments();
  });
  document.getElementById("ac-dept-tags")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-dept-del]");
    if (!btn) return;
    draftDepartments.splice(Number(btn.getAttribute("data-dept-del")), 1);
    renderAdminDepartments();
  });
  document.getElementById("ac-dept-save")?.addEventListener("click", async () => {
    try {
      await saveAdminDepartments();
    } catch (err) {
      setOrgMsg("ac-dept-msg", err.message || "저장 실패", "err");
    }
  });

  document.getElementById("ac-staff-add")?.addEventListener("click", () => {
    syncStaffFromDom();
    draftStaff.push({
      role: "",
      staff_name: "",
      department: "",
      position: "",
      phone: "",
      mobile: "",
      email: "",
    });
    renderAdminStaff();
  });
  document.getElementById("ac-staff-body")?.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-staff-del]");
    if (!btn) return;
    syncStaffFromDom();
    draftStaff.splice(Number(btn.getAttribute("data-staff-del")), 1);
    renderAdminStaff();
  });
  document.getElementById("ac-staff-save")?.addEventListener("click", async () => {
    try {
      await saveAdminStaff();
    } catch (err) {
      setOrgMsg("ac-staff-msg", err.message || "저장 실패", "err");
    }
  });

  window.openDetailModal = openDetailModal;

  function renderCompanyPagination(total, page, limit) {
    const el = document.getElementById("pagination");
    if (!el) return;

    const totalPages = Math.max(1, Math.ceil(total / limit));
    const current = Math.min(page, totalPages);

    const buttons = [];
    buttons.push(
      `<button type="button" data-page="${current - 1}" ${current <= 1 ? "disabled" : ""}>이전</button>`,
    );

    const windowSize = 5;
    let start = Math.max(1, current - Math.floor(windowSize / 2));
    let end = Math.min(totalPages, start + windowSize - 1);
    start = Math.max(1, end - windowSize + 1);

    for (let p = start; p <= end; p += 1) {
      buttons.push(
        `<button type="button" data-page="${p}" class="${p === current ? "active" : ""}">${p}</button>`,
      );
    }

    buttons.push(
      `<button type="button" data-page="${current + 1}" ${current >= totalPages ? "disabled" : ""}>다음</button>`,
    );

    el.innerHTML = buttons.join("");
    el.querySelectorAll("button[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = Number(btn.getAttribute("data-page"));
        if (!Number.isNaN(next) && next >= 1 && next <= totalPages) {
          fetchCompanies(next);
        }
      });
    });
  }

  // 검색 이벤트
  const searchBtn = document.getElementById("search-companies-btn");
  const searchInput = document.getElementById("search-keyword");
  if (searchBtn) searchBtn.addEventListener("click", () => fetchCompanies(1));
  if (searchInput) {
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
            (a) => `
        <tr>
          <td>${escapeHtml(a.id)}</td>
          <td class="fw-bold text-start">${escapeHtml(a.name || "-")}</td>
          <td class="text-start">${escapeHtml(a.email || "-")}</td>
          <td>${escapeHtml(a.phone || "-")}</td>
          <td><span class="badge bg-info-subtle">${escapeHtml(gradeLabel(a.grade))}</span></td>
          <td>${escapeHtml(employmentLabel(a.employment_type))}</td>
          <td>${a.is_freelance ? '<span class="badge bg-success-subtle">프리랜서</span>' : "-"}</td>
          <td>
            <button type="button" class="btn-detail" onclick="openAuditorDetailModal(${Number(a.id)})">상세</button>
          </td>
        </tr>`,
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
    const el = document.getElementById("auditor-pagination");
    if (!el) return;

    const totalPages = Math.max(1, Math.ceil(total / limit));
    const current = Math.min(page, totalPages);
    const buttons = [];
    buttons.push(
      `<button type="button" data-page="${current - 1}" ${current <= 1 ? "disabled" : ""}>이전</button>`,
    );

    const windowSize = 5;
    let start = Math.max(1, current - Math.floor(windowSize / 2));
    let end = Math.min(totalPages, start + windowSize - 1);
    start = Math.max(1, end - windowSize + 1);

    for (let p = start; p <= end; p += 1) {
      buttons.push(
        `<button type="button" data-page="${p}" class="${p === current ? "active" : ""}">${p}</button>`,
      );
    }
    buttons.push(
      `<button type="button" data-page="${current + 1}" ${current >= totalPages ? "disabled" : ""}>다음</button>`,
    );

    el.innerHTML = buttons.join("");
    el.querySelectorAll("button[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const next = Number(btn.getAttribute("data-page"));
        if (!Number.isNaN(next) && next >= 1 && next <= totalPages) {
          fetchAuditors(next);
        }
      });
    });
  }

  function openAuditorDetailModalShell() {
    const modal = document.getElementById("auditorDetailModal");
    if (!modal) return;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    switchAuditorDetailTab("aud-basic-info");
  }

  function closeAuditorDetailModal() {
    const modal = document.getElementById("auditorDetailModal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  function switchAuditorDetailTab(tabId) {
    document.querySelectorAll("#auditorDetailTab .nav-link").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-auditor-detail-tab") === tabId);
    });
    document.querySelectorAll("#auditorDetailTabContent .detail-tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === tabId);
    });
  }

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
    return map[status] || status || "-";
  }

  function renderMembershipCards(memberships) {
    const el = document.getElementById("cb-membership-list");
    if (!el) return;
    if (!memberships.length) {
      el.innerHTML =
        '<div class="placeholder-box">신청 및 승인된 인증기관 자격 정보가 없습니다.</div>';
      return;
    }
    el.innerHTML = memberships
      .map((m) => {
        const statusClass = m.status === "approved" ? "bg-success" : "bg-warning";
        const approvedGrade = gradeLabel(m.approved_grade || m.grade_at_cb || m.apply_grade);
        return `
      <div class="membership-card">
        <div class="membership-card-header">
          <h6 class="fw-bold">CB ID: ${escapeHtml(m.cb_id)}</h6>
          <span class="badge ${statusClass}">${escapeHtml(membershipStatusLabel(m.status))}</span>
        </div>
        <table class="detail-table" style="margin-top: 8px;">
          <tr>
            <th style="width:25%;">승인 등급</th>
            <td>${escapeHtml(approvedGrade)}</td>
          </tr>
          <tr>
            <th>승인 ISO 표준</th>
            <td><span class="fw-bold text-primary">${escapeHtml(m.cert_standards || "검토 중")}</span></td>
          </tr>
          <tr>
            <th>승인 IAF 코드</th>
            <td>${escapeHtml(m.approved_iaf_codes || "검토 중")}</td>
          </tr>
          <tr>
            <th>자격 부여일</th>
            <td>${escapeHtml(m.qualification_granted_at || "-")}</td>
          </tr>
          <tr>
            <th>자격 만료일</th>
            <td>${escapeHtml(m.qualification_expires_at || "-")}</td>
          </tr>
          <tr>
            <th>지식평가 / CPD</th>
            <td>${escapeHtml(m.knowledge_eval_score ?? "-")}점 / ${escapeHtml(m.cpd_hours_completed ?? 0)}h</td>
          </tr>
          <tr>
            <th>이해상충 선언</th>
            <td>${m.conflict_of_interest_cleared ? "완료" : "미완료"}</td>
          </tr>
        </table>
      </div>`;
      })
      .join("");
  }

  function renderEduList(educations) {
    const el = document.getElementById("aud-edu-list");
    if (!el) return;
    if (!educations.length) {
      el.innerHTML = '<div class="placeholder-box">학력 정보가 없습니다.</div>';
      return;
    }
    el.innerHTML = educations
      .map(
        (e) => `
      <div class="history-item">
        <strong>${escapeHtml(e.school_name)} · ${escapeHtml(e.degree)}</strong>
        <small>전공: ${escapeHtml(e.major || "-")} · ${escapeHtml(e.entered_at || "-")} ~ ${escapeHtml(e.graduated_at || "-")}</small>
      </div>`,
      )
      .join("");
  }

  function renderCareerList(careers) {
    const el = document.getElementById("aud-career-list");
    if (!el) return;
    if (!careers.length) {
      el.innerHTML = '<div class="placeholder-box">실무 경력 정보가 없습니다.</div>';
      return;
    }
    el.innerHTML = careers
      .map(
        (c) => `
      <div class="history-item">
        <strong>${escapeHtml(c.company_name)} · ${escapeHtml(c.position || "-")}</strong>
        <small>${escapeHtml(c.start_date || "-")} ~ ${c.is_current ? "재직중" : escapeHtml(c.end_date || "-")}${c.note ? ` · ${escapeHtml(c.note)}` : ""}</small>
      </div>`,
      )
      .join("");
  }

  async function openAuditorDetailModal(id) {
    const token = localStorage.getItem("access_token");
    if (!token) {
      redirectToLogin("로그인이 필요합니다.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/admin/auditors/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
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

      const data = await response.json();
      const profile = data.profile || {};

      setText("modal-auditor-title", `${profile.name || "심사원"} 심사원 상세 정보`);
      setText("a-id", profile.id);
      setText("a-status", profile.status || "active");
      setText("a-name", profile.name || "-");
      setText("a-email", profile.email || "-");
      setText("a-phone", profile.phone || "-");
      setText(
        "a-birth-gender",
        `${profile.birth_date || "-"} / ${genderLabel(profile.gender)}`,
      );
      setText("a-emp-type", employmentLabel(profile.employment_type));
      setText("a-freelance", profile.is_freelance ? "예" : "아니오");
      setText(
        "a-address",
        `${profile.address || ""} ${profile.detail_address || ""}`.trim() || "-",
      );
      setText(
        "a-bank-account",
        profile.bank_name
          ? `${profile.bank_name} ${profile.account_no || ""} (예금주: ${profile.account_holder || "-"})`
          : "미등록",
      );

      // 2. 자격 & 소속 CB 탭 바인딩
      renderMembershipCards(data.memberships || []);
      // 3. 학력 & 실무경력
      renderEduList(data.educations || []);
      renderCareerList(data.careers || []);

      openAuditorDetailModalShell();
    } catch (error) {
      console.error("Auditor detail fetch failed:", error);
      alert(`심사원 상세를 불러오지 못했습니다.\n${error.message}`);
    }
  }

  document.querySelectorAll("[data-auditor-modal-close]").forEach((btn) => {
    btn.addEventListener("click", closeAuditorDetailModal);
  });
  const auditorModal = document.getElementById("auditorDetailModal");
  if (auditorModal) {
    auditorModal.addEventListener("click", (e) => {
      if (e.target === auditorModal) closeAuditorDetailModal();
    });
  }
  document.querySelectorAll("#auditorDetailTab [data-auditor-detail-tab]").forEach((btn) => {
    btn.addEventListener("click", () =>
      switchAuditorDetailTab(btn.getAttribute("data-auditor-detail-tab")),
    );
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

  async function loadCbContracts() {
    const tbody = document.getElementById("cb-contracts-tbody");
    if (!tbody) return;
    tbody.innerHTML =
      '<tr><td colspan="10" style="text-align: center; color: var(--font-tertiary);">불러오는 중...</td></tr>';

    try {
      const res = await authFetch(`${API_BASE}/admin/cb-contracts?skip=0&limit=100&ensure_missing=true`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `요청 실패 (HTTP ${res.status})`);
      }
      const data = await res.json();
      renderCbContractsTable(data);
    } catch (error) {
      console.error("CB contracts fetch failed:", error);
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--sec-red);">목록을 불러오지 못했습니다. (${escapeHtml(error.message)})</td></tr>`;
    }
  }

  function renderCbContractsTable(records) {
    const tbody = document.getElementById("cb-contracts-tbody");
    if (!tbody) return;

    if (!records || records.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="10" style="text-align: center; color: var(--font-tertiary);">등록된 인증기관이 없습니다.</td></tr>';
      return;
    }

    const fmtMoney = (v) => {
      if (v == null || v === "") return "-";
      const n = Number(v);
      return Number.isFinite(n) ? n.toLocaleString("ko-KR") : String(v);
    };

    tbody.innerHTML = records
      .map((r) => {
        const cbId = r.cb_id ?? r.id;
        const heldCnt = Number(r.held_standard_count ?? 0);
        const scopeCount = Number(r.scope_count ?? 0);
        const heldLabel = heldCnt ? `${heldCnt}개 표준` : `${scopeCount}개 Scope`;
        const abLine = r.ab_summary
          ? `<div style="font-size:12px;color:var(--font-secondary);margin-top:4px;">AB: ${escapeHtml(r.ab_summary)}</div>`
          : (Array.isArray(r.held_standards) && r.held_standards.length
            ? `<div style="font-size:12px;color:var(--font-secondary);margin-top:4px;">${escapeHtml(r.held_standards.slice(0, 3).join(", "))}${r.held_standards.length > 3 ? "…" : ""}</div>`
            : "");
        return `
        <tr>
          <td>${escapeHtml(cbId)}</td>
          <td>${escapeHtml(r.cb_code || "-")}</td>
          <td style="font-weight: var(--font-weight-semibold); text-align:left;">${escapeHtml(r.cb_name)}</td>
          <td><span class="label-chip label-chip-purple">${escapeHtml(r.cb_status || "-")}</span></td>
          <td>
            <button type="button" class="scope-badge" data-cb-detail="${cbId}" title="보유 표준 / 인정정보">
              ${escapeHtml(heldLabel)}
            </button>
            ${abLine}
          </td>
          <td>${escapeHtml(r.contract_year ?? "-")}</td>
          <td>${escapeHtml(r.tier || "-")}</td>
          <td>${fmtMoney(r.annual_base_fee)}</td>
          <td>${fmtMoney(r.price_per_md)}</td>
          <td>
            <button type="button" class="btn-detail" data-cb-detail="${cbId}">상세 및 Scope 관리</button>
          </td>
        </tr>`;
      })
      .join("");

    tbody.querySelectorAll("[data-cb-detail]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = Number(btn.getAttribute("data-cb-detail"));
        if (id) openCbDetailScopeModal(id);
      });
    });
  }

  /* ---- CB 상세 / Scope 관리 모달 ---- */
    const cbScopeState = {
    editingId: null,
    legacyRegNo: null,
    standards: [],
    standardOptions: [],
    standardScopeOptions: [],
    taxonomies: {},
    iaf39Standards: [],
    abBodies: [],
    iafCodes: Array.from({ length: 39 }, (_, i) => String(i + 1).padStart(2, "0")),
    activeScopes: new Set(),
    stdAccMap: {},
  };

  function switchCbScopeTab(name) {
    document.querySelectorAll("#cbDetailScopeModal [data-cb-scope-tab]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-cb-scope-tab") === name);
    });
    document.querySelectorAll("#cbDetailScopeModal .detail-tab-pane").forEach((pane) => {
      pane.classList.toggle("active", pane.id === name);
    });
  }

  function abOptionsHtml(selected) {
    const cur = selected || "";
    return [`<option value="">— 선택 —</option>`]
      .concat(
        cbScopeState.abBodies.map((ab) => {
          const code = ab.code || ab.name;
          const label = ab.name_en ? `${code} · ${ab.name_en}` : code;
          return `<option value="${escapeHtml(code)}" ${code === cur ? "selected" : ""}>${escapeHtml(label)}</option>`;
        }),
      )
      .join("");
  }

  function scopeMetaFor(std) {
    const fromOpt = (cbScopeState.standardScopeOptions || []).find((x) => x.standard_code === std);
    if (fromOpt) return fromOpt;
    const tax = (cbScopeState.iaf39Standards || []).includes(std) ? "iaf39" : "none";
    return {
      standard_code: std,
      taxonomy: tax,
      taxonomy_label: (cbScopeState.taxonomies[tax] || {}).label || tax,
      has_scope_codes: tax !== "none",
      codes: ((cbScopeState.taxonomies[tax] || {}).codes) || [],
    };
  }

  function renderCbStdAccTable() {
    const tbody = document.getElementById("cb-std-acc-tbody");
    if (!tbody) return;
    const list = cbScopeState.standardOptions.length
      ? cbScopeState.standardOptions
      : cbScopeState.standards.map((c) => ({ standard_code: c, standard_name: "" }));
    tbody.innerHTML = list
      .map((s) => {
        const code = s.standard_code || s;
        const name = s.standard_name || "";
        const row = cbScopeState.stdAccMap[code] || {};
        const meta = scopeMetaFor(code);
        const scopes = Array.isArray(row.scope_codes)
          ? row.scope_codes
          : Array.isArray(row.iaf_codes)
            ? row.iaf_codes
            : [];
        let scopeSummary = "없음";
        if (!meta.has_scope_codes) {
          scopeSummary = "코드 불필요";
        } else if (scopes.length) {
          scopeSummary = `${scopes.length}개 (${scopes.slice(0, 6).join(", ")}${scopes.length > 6 ? "…" : ""})`;
        }
        const held = row.is_active || row.ab_code || row.registration_no || scopes.length;
        const editBtn = meta.has_scope_codes
          ? `<button type="button" class="btn-secondary" data-edit-scope="${escapeHtml(code)}" style="padding:4px 10px;font-size:12px;">범위 편집</button>`
          : `<span class="muted" style="font-size:12px;">—</span>`;
        return `<tr data-std="${escapeHtml(code)}">
          <td style="text-align:center;"><input type="checkbox" data-held ${held ? "checked" : ""} /></td>
          <td><strong>${escapeHtml(code)}</strong>${name ? `<div class="muted" style="font-size:12px;color:var(--font-secondary);">${escapeHtml(name)}</div>` : ""}
            <div class="muted" style="font-size:11px;margin-top:2px;">${escapeHtml(meta.taxonomy_label || "")}</div></td>
          <td><select data-ab style="width:100%;padding:8px;border:1px solid var(--gray-line-2);border-radius:8px;">${abOptionsHtml(row.ab_code || "")}</select></td>
          <td><input data-reg type="text" value="${escapeHtml(row.registration_no || "")}" placeholder="인정번호" style="width:100%;padding:8px;border:1px solid var(--gray-line-2);border-radius:8px;" /></td>
          <td>
            <div style="font-size:12px;color:var(--font-secondary);margin-bottom:4px;">${escapeHtml(scopeSummary)}</div>
            ${editBtn}
          </td>
        </tr>`;
      })
      .join("");
    tbody.querySelectorAll("[data-edit-scope]").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchCbScopeTab("cb-scopes");
        const std = btn.getAttribute("data-edit-scope");
        const block = document.querySelector(`#cb-scope-matrix [data-scope-std="${CSS.escape(std)}"]`);
        if (block) block.scrollIntoView({ block: "center", behavior: "smooth" });
      });
    });
  }

  function collectCbStdAcc() {
    return [...document.querySelectorAll("#cb-std-acc-tbody tr")].map((tr) => ({
      standard_code: tr.dataset.std,
      ab_code: tr.querySelector("[data-ab]").value || null,
      registration_no: tr.querySelector("[data-reg]").value.trim() || null,
      is_active: tr.querySelector("[data-held]").checked,
    }));
  }

  function renderCbScopeMatrix() {
    const table = document.getElementById("cb-scope-matrix");
    if (!table) return;
    const list = cbScopeState.standardOptions.length
      ? cbScopeState.standardOptions
      : cbScopeState.standards.map((c) => ({ standard_code: c, standard_name: "" }));

    const sections = [];
    // IAF39 matrix (9001/14001/45001 only)
    const iafStds = list.filter((s) => scopeMetaFor(s.standard_code || s).taxonomy === "iaf39");
    if (iafStds.length) {
      const thead = `<tr><th class="std">표준 \\ IAF</th>${cbScopeState.iafCodes.map((c) => `<th>${c}</th>`).join("")}</tr>`;
      const body = iafStds
        .map((s) => {
          const std = s.standard_code || s;
          const cells = cbScopeState.iafCodes
            .map((iaf) => {
              const key = `${std}|${iaf}`;
              return `<td><input type="checkbox" data-key="${key}" ${
                cbScopeState.activeScopes.has(key) ? "checked" : ""
              } /></td>`;
            })
            .join("");
          return `<tr data-scope-std="${escapeHtml(std)}"><th class="std">${escapeHtml(std)}</th>${cells}</tr>`;
        })
        .join("");
      sections.push(`
        <div data-scope-std="iaf39-block" style="margin-bottom:18px;">
          <h4 style="margin:0 0 8px;font-size:14px;">IAF 01–39 — ISO 9001 / 14001 / 45001 전용</h4>
          <div class="cb-matrix-wrap"><table class="cb-matrix"><thead>${thead}</thead><tbody>${body}</tbody></table></div>
        </div>`);
    }

    // Other taxonomies with codes
    list.forEach((s) => {
      const std = s.standard_code || s;
      const name = s.standard_name || "";
      const meta = scopeMetaFor(std);
      if (meta.taxonomy === "iaf39") return;
      if (!meta.has_scope_codes) {
        sections.push(`
          <div data-scope-std="${escapeHtml(std)}" style="margin-bottom:14px;padding:10px 12px;border:1px solid var(--gray-line-2);border-radius:8px;">
            <strong>${escapeHtml(std)}</strong>${name ? ` · ${escapeHtml(name)}` : ""}
            <div class="muted" style="margin-top:4px;font-size:12px;">인증수행범위 코드 없음 — 보유 표준 · 인정기관 · 인정번호만 관리</div>
          </div>`);
        return;
      }
      const codes = meta.codes || (cbScopeState.taxonomies[meta.taxonomy] || {}).codes || [];
      const checks = codes
        .map((c) => {
          const code = c.code || c;
          const label = c.name_ko ? `${code} — ${c.name_ko}` : code;
          const key = `${std}|${code}`;
          return `<label style="display:flex;gap:8px;align-items:flex-start;margin:4px 0;font-size:12px;">
            <input type="checkbox" data-key="${escapeHtml(key)}" ${cbScopeState.activeScopes.has(key) ? "checked" : ""} />
            <span>${escapeHtml(label)}</span>
          </label>`;
        })
        .join("");
      sections.push(`
        <div data-scope-std="${escapeHtml(std)}" style="margin-bottom:16px;">
          <h4 style="margin:0 0 6px;font-size:14px;">${escapeHtml(std)}${name ? ` · ${escapeHtml(name)}` : ""}</h4>
          <div class="muted" style="font-size:12px;margin-bottom:8px;">${escapeHtml(meta.taxonomy_label || "")}</div>
          <div style="max-height:220px;overflow:auto;border:1px solid var(--gray-line-2);border-radius:8px;padding:8px 10px;">${checks}</div>
        </div>`);
    });

    table.innerHTML = sections.join("") || '<p class="muted">표시할 수행범위가 없습니다.</p>';
  }

  function collectCbScopes() {
    const root = document.getElementById("cb-scope-matrix");
    if (!root) return [];
    return [...root.querySelectorAll("input[type=checkbox][data-key]:checked")].map((el) => {
      const [standard_code, scope_code] = el.dataset.key.split("|");
      return { standard_code, scope_code, iaf_code: scope_code, is_active: true };
    });
  }

  function fillCbScopeForm(d = {}) {
    document.getElementById("cb-f-code").value = d.cb_code || "";
    document.getElementById("cb-f-name").value = d.cb_name || "";
    document.getElementById("cb-f-name-en").value = d.cb_name_en || "";
    cbScopeState.legacyRegNo = d.reg_no || null;
    document.getElementById("cb-f-biz").value = d.biz_reg_no || "";
    document.getElementById("cb-f-ceo").value = d.ceo_name || "";
    document.getElementById("cb-f-email").value = d.email || "";
    document.getElementById("cb-f-web").value = d.website || "";
    document.getElementById("cb-f-tel").value = d.tel || "";
    document.getElementById("cb-f-address").value = d.address || "";
    document.getElementById("cb-f-status").value = d.status || "active";
    const contract = d.contract || {};
    document.getElementById("cb-f-year").value = contract.contract_year || new Date().getFullYear();
    document.getElementById("cb-f-tier").value = contract.tier || "MEDIUM";
    document.getElementById("cb-f-base-fee").value = contract.annual_base_fee ?? "";
    document.getElementById("cb-f-md").value = contract.price_per_md ?? "";
    cbScopeState.activeScopes = new Set(
      (d.scopes || [])
        .filter((s) => s.is_active !== false)
        .map((s) => {
          let code = String(s.scope_code || s.iaf_code || "").trim();
          if (/^\d+$/.test(code)) code = code.padStart(2, "0");
          return `${s.standard_code}|${code}`;
        }),
    );
    (d.scopes || []).forEach((s) => {
      if (s.standard_code && !cbScopeState.standards.includes(s.standard_code)) {
        cbScopeState.standards.push(s.standard_code);
      }
    });
    cbScopeState.stdAccMap = {};
    (d.standard_accreditations || []).forEach((row) => {
      if (row.standard_code) cbScopeState.stdAccMap[row.standard_code] = row;
    });
    renderCbStdAccTable();
    renderCbScopeMatrix();
  }

  function openCbScopeModalShell() {
    const modal = document.getElementById("cbDetailScopeModal");
    if (!modal) return;
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    switchCbScopeTab("cb-basic");
  }

  function closeCbScopeModal() {
    const modal = document.getElementById("cbDetailScopeModal");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    cbScopeState.editingId = null;
    const err = document.getElementById("cb-scope-modal-error");
    if (err) err.textContent = "";
  }

  async function openCbDetailScopeModal(cbId) {
    try {
      const res = await authFetch(`${API_BASE}/admin/certification-bodies/${cbId}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : `상세 조회 실패 (HTTP ${res.status})`,
        );
      }
      cbScopeState.editingId = cbId;
      document.getElementById("cb-scope-modal-title").textContent =
        `상세 및 Scope 관리 — ${data.cb_name || ""}`;
      document.getElementById("cb-scope-modal-sub").textContent =
        `${data.cb_code || ""} · 보유표준 ${(data.standard_accreditations || []).filter((x) => x.is_active).length || 0}/15 · 수행범위 ${data.scope_count ?? 0}`;
      fillCbScopeForm(data);
      openCbScopeModalShell();
    } catch (error) {
      alert(error.message || "상세 조회에 실패했습니다.");
    }
  }

  window.openCbDetailScopeModal = openCbDetailScopeModal;

  document.querySelectorAll("#cbDetailScopeModal [data-cb-scope-tab]").forEach((btn) => {
    btn.addEventListener("click", () => switchCbScopeTab(btn.getAttribute("data-cb-scope-tab")));
  });
  document.querySelectorAll("[data-cb-scope-close]").forEach((btn) => {
    btn.addEventListener("click", closeCbScopeModal);
  });
  const cbScopeModal = document.getElementById("cbDetailScopeModal");
  if (cbScopeModal) {
    cbScopeModal.addEventListener("click", (e) => {
      if (e.target.id === "cbDetailScopeModal") closeCbScopeModal();
    });
  }
  const cbScopeSave = document.getElementById("cb-scope-save");
  if (cbScopeSave) {
    cbScopeSave.addEventListener("click", async () => {
      const err = document.getElementById("cb-scope-modal-error");
      if (err) err.textContent = "";
      if (!cbScopeState.editingId) return;
      if (window.ComplaisValidation) {
        const v = ComplaisValidation.validateFields([
          { el: document.getElementById("cb-f-biz"), kind: "biz", required: false },
          { el: document.getElementById("cb-f-tel"), kind: "phone", required: false },
          { el: document.getElementById("cb-f-email"), kind: "email", required: false },
        ]);
        if (!v.ok) {
          if (err) err.textContent = v.message;
          switchCbScopeTab("cb-basic");
          if (v.field?.el) {
            try {
              v.field.el.focus();
              v.field.el.select?.();
            } catch (_) {
              /* ignore */
            }
          }
          return;
        }
      }
      const payload = {
        cb_code: document.getElementById("cb-f-code").value.trim(),
        cb_name: document.getElementById("cb-f-name").value.trim(),
        cb_name_en: document.getElementById("cb-f-name-en").value.trim() || null,
        reg_no: cbScopeState.legacyRegNo,
        biz_reg_no: document.getElementById("cb-f-biz").value.trim() || null,
        ceo_name: document.getElementById("cb-f-ceo").value.trim() || null,
        email: document.getElementById("cb-f-email").value.trim() || null,
        website: document.getElementById("cb-f-web").value.trim() || null,
        tel: document.getElementById("cb-f-tel").value.trim() || null,
        address: document.getElementById("cb-f-address").value.trim() || null,
        status: document.getElementById("cb-f-status").value,
        scopes: collectCbScopes(),
        standard_accreditations: collectCbStdAcc(),
        contract: {
          contract_year: Number(document.getElementById("cb-f-year").value) || undefined,
          tier: document.getElementById("cb-f-tier").value,
          annual_base_fee: document.getElementById("cb-f-base-fee").value
            ? Number(document.getElementById("cb-f-base-fee").value)
            : undefined,
          price_per_md: document.getElementById("cb-f-md").value
            ? Number(document.getElementById("cb-f-md").value)
            : undefined,
        },
      };
      if (!payload.cb_code || !payload.cb_name) {
        if (err) err.textContent = "기관 코드와 기관명은 필수입니다.";
        return;
      }
      try {
        cbScopeSave.disabled = true;
        const res = await authFetch(
          `${API_BASE}/admin/certification-bodies/${cbScopeState.editingId}`,
          { method: "PUT", body: JSON.stringify(payload) },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(
            typeof data.detail === "string" ? data.detail : `저장 실패 (HTTP ${res.status})`,
          );
        }
        closeCbScopeModal();
        await loadCbContracts();
      } catch (error) {
        if (err) err.textContent = error.message;
      } finally {
        cbScopeSave.disabled = false;
      }
    });
  }

  function bindCbContactValidation() {
    if (!window.ComplaisValidation) return;
    ComplaisValidation.bindField(document.getElementById("cb-f-biz"), "biz");
    ComplaisValidation.bindField(document.getElementById("cb-f-tel"), "phone");
    ComplaisValidation.bindField(document.getElementById("cb-f-email"), "email");
  }

  async function loadCbMatrixMeta() {
    try {
      const res = await authFetch(`${API_BASE}/admin/certification-bodies/meta/matrix-options`);
      if (res.ok) {
        const meta = await res.json();
        if (meta.standards?.length) cbScopeState.standards = meta.standards;
        if (meta.standard_options?.length) cbScopeState.standardOptions = meta.standard_options;
        if (meta.standard_scope_options?.length) cbScopeState.standardScopeOptions = meta.standard_scope_options;
        if (meta.taxonomies) cbScopeState.taxonomies = meta.taxonomies;
        if (meta.iaf39_standards?.length) cbScopeState.iaf39Standards = meta.iaf39_standards;
        if (meta.iaf_codes?.length) cbScopeState.iafCodes = meta.iaf_codes;
        if (meta.accreditation_bodies?.length) cbScopeState.abBodies = meta.accreditation_bodies;
      }
    } catch (_) {
      /* ignore */
    }
    // 메타 API 실패와 무관하게 사업자번호 등 포맷/검증 바인딩
    bindCbContactValidation();
  }
  loadCbMatrixMeta();

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
        const scopesText = (r.scopes || []).map((s) => `IAF ${escapeHtml(s.iaf_code)}`).join(", ") || "-";
        const fileCell = r.certificate_file_url
          ? `<a href="${escapeHtml(r.certificate_file_url)}" style="color: var(--sec-blue);" target="_blank" rel="noopener">파일 보기</a>`
          : "-";
        return `
          <tr>
            <td style="font-weight: var(--font-weight-semibold);">${escapeHtml(r.cb_name)}</td>
            <td>${escapeHtml(r.accreditation_body)}</td>
            <td>${scopesText}</td>
            <td>${fileCell}</td>
            <td><span class="label-chip label-chip-purple">${escapeHtml(r.status)}</span></td>
            <td>
              <button class="badge badge-purple" data-approve="${r.id}">승인</button>
              <button class="badge badge-red" data-reject="${r.id}">반려</button>
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

  async function loadDashboardStats() {
    try {
      const statsRes = await authFetch(`${API_BASE}/admin/stats`);
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

  // 초기 탭 (해시 deep-link 지원: #cb-contracts)
  const initialTab = window.__initialAdminTab || "dashboard";
  if (initialTab !== "dashboard") {
    showTab(initialTab);
  }
  loadTabData(initialTab);
});
