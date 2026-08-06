/**
 * ComplAIs CB Admin API 연동 스크립트
 * 백엔드: /api/v1/cb-admin/*
 *
 * - MD 검토: plus_pct / minus_pct → 서버 Field Alias (add_pct / subtract_pct)
 * - 승인: ApplicationApproveRequest
 * - 배정: AuditorAssignmentRequest 래퍼
 */
const CBAdminAPI = {
  basePath: (typeof window !== "undefined" && window.COMPLAIS_API_BASE
    ? String(window.COMPLAIS_API_BASE).replace(/\/$/, "")
    : "/api/v1") + "/cb-admin",

  _formatDetail(detail) {
    if (detail == null) return "요청 처리 중 오류가 발생했습니다.";
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d && (d.msg || d.message)) || JSON.stringify(d))
        .join("; ");
    }
    if (typeof detail === "object" && detail.message) return detail.message;
    try {
      return JSON.stringify(detail);
    } catch (_) {
      return String(detail);
    }
  },

  // 공통 Fetch 래퍼 (JWT 토큰 및 에러 핸들링)
  async request(endpoint, options = {}) {
    const token = localStorage.getItem("access_token");
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    };

    try {
      const response = await fetch(`${this.basePath}${endpoint}`, {
        ...options,
        headers,
      });

      let data = null;
      const text = await response.text();
      try {
        data = text ? JSON.parse(text) : {};
      } catch (_) {
        data = { detail: text || response.statusText };
      }

      if (!response.ok) {
        throw new Error(this._formatDetail(data.detail) || data.message || "요청 처리 중 오류가 발생했습니다.");
      }
      return data;
    } catch (error) {
      console.error(`[CBAdminAPI Error] ${endpoint}:`, error);
      if (typeof alert === "function") {
        alert(`⚠️ 오류: ${error.message}`);
      }
      throw error;
    }
  },

  // 0. 대시보드 신청 목록
  async listApplications() {
    return this.request("/applications", { method: "GET" });
  },

  // 0-1. 신청서 상세
  async getApplication(appId) {
    return this.request(`/applications/${appId}`, { method: "GET" });
  },

  // 0-1b. 고객사 목록/등록
  async listClients(skip = 0, limit = 100) {
    return this.request(`/clients?skip=${skip}&limit=${limit}`, { method: "GET" });
  },

  async createClient(payload) {
    return this.request("/clients", {
      method: "POST",
      body: JSON.stringify({
        company_name: payload.companyName || payload.company_name,
        biz_no: payload.bizNo || payload.biz_no,
        representative: payload.representative || null,
        employee_count: payload.employeeCount || payload.employee_count || 1,
      }),
    });
  },

  // 0-2. 배정 가능 심사원 (서약서/자격 포함)
  async listAuditors(status = "approved") {
    const q = status ? `?status=${encodeURIComponent(status)}` : "";
    return this.request(`/auditors${q}`, { method: "GET" });
  },

  // 0-3. 계약 목록 (Draft/확정)
  async listContracts() {
    return this.request("/contracts", { method: "GET" });
  },

  // 0-3b. 계약 Draft 생성 (신청건 기반 권장)
  async createContract(payload) {
    const appId = parseInt(payload.applicationId || payload.application_id, 10);
    const body = {
      application_id: appId,
      total_md: parseFloat(payload.totalMd || payload.total_md) || 0,
      total_amount: parseInt(payload.totalAmount || payload.total_amount, 10) || 0,
      audit_standards: payload.auditStandards || payload.audit_standards || [],
      contract_date: payload.contractDate || payload.contract_date || null,
      audit_type: payload.auditType || payload.audit_type || "INITIAL",
    };
    if (appId) {
      return this.request(`/applications/${appId}/contract`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    }
    return this.request("/contracts", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  // 1. MD 검토 및 비율 계산 저장
  async reviewMD(appId, plusPct, minusPct, note, action = "save_md") {
    return this.request(`/applications/${appId}/md-review`, {
      method: "POST",
      body: JSON.stringify({
        action,
        plus_pct: parseInt(plusPct, 10) || 0,
        minus_pct: parseInt(minusPct, 10) || 0,
        calculation_note: note || "",
      }),
    });
  },

  // 2. 신청 승인 (CB Scope 검증 및 Draft 계약 생성)
  async approveApplication(appId, memo, options = {}) {
    return this.request(`/applications/${appId}/approve`, {
      method: "POST",
      body: JSON.stringify({
        memo: memo || "",
        skip_scope_check: Boolean(options.skipScopeCheck),
        force_new_contract: Boolean(options.forceNewContract),
      }),
    });
  },

  // 3. 심사팀 일괄 배정 (서약서 & IAF/13485 검증)
  async assignAuditors(appId, payload) {
    return this.request(`/applications/${appId}/assign-auditors`, {
      method: "POST",
      body: JSON.stringify({
        lead_auditor_id: parseInt(payload.leadAuditorId, 10),
        member_auditor_ids: (payload.memberAuditorIds || []).map((id) => parseInt(id, 10)),
        audit_start: payload.auditStart,
        audit_end: payload.auditEnd,
        audit_type: payload.auditType || "initial",
        stage: payload.stage || "combined",
        total_md: parseFloat(payload.totalMd) || 2.0,
        surveillance_cycle: parseInt(payload.surveillanceCycle, 10) || 12,
        scope_kr: payload.scopeKr || "",
        standard: payload.standard || null,
      }),
    });
  },
};

if (typeof window !== "undefined") {
  window.CBAdminAPI = CBAdminAPI;
}
