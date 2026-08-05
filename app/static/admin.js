/* ComplAIs — Platform Admin 대시보드 API 연동
 *
 * 백엔드: app/api/v1/endpoints/admin.py (require_platform_admin)
 *
 * 임시 인증 스텁: 백엔드가 아직 JWT(Authorization: Bearer)를 지원하지 않고,
 * X-User-Id 헤더로 로그인 사용자를 지정하는 방식만 존재한다 (app/core/security.py 참고).
 * getAuthToken()은 실 로그인 도입 시 채워질 자리이며, 지금은 CURRENT_USER_ID를 그대로 사용한다.
 * TODO(auth): 실제 로그인이 붙으면 getAuthToken()이 세션/토큰을 반환하도록 교체하고,
 *             callAdminApi의 인증 헤더를 X-User-Id -> Authorization: Bearer로 전환한다.
 */
// FastAPI(app/main.py)가 이 정적 파일을 같은 오리진에서 서빙하므로 상대경로로 충분하다.
const API_BASE = "/api/v1";
const CURRENT_USER_ID = 1; // TODO(auth): 실제 로그인 붙이면 세션의 platform_admin 사용자 id로 교체

function getAuthToken() {
  return null; // 백엔드에 JWT 인증이 아직 없어 현재는 사용되지 않는다.
}

async function callAdminApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "X-User-Id": String(CURRENT_USER_ID),
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `요청 실패 (HTTP ${res.status})`);
  }
  return data;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
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
            <button class="badge badge-purple" onclick="approveAccreditation(${r.id})">승인</button>
            <button class="badge badge-red" onclick="rejectAccreditation(${r.id})">반려</button>
          </td>
        </tr>`;
    })
    .join("");
}

async function fetchAccreditationRequests() {
  const tbody = document.getElementById("accreditation-tbody");
  try {
    const data = await callAdminApi("/admin/accreditations?status=PENDING");
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
    await callAdminApi(`/admin/accreditations/${recordId}/approve`, { method: "PATCH" });
    alert("승인 완료되었습니다.");
    fetchAccreditationRequests();
  } catch (err) {
    alert(`승인 처리 중 오류가 발생했습니다.\n${err.message}`);
  }
}

async function rejectAccreditation(recordId) {
  if (!confirm("해당 인증기관의 인정서를 반려하시겠습니까?")) return;
  const reason = window.prompt("반려 사유를 입력하세요 (선택):", "");
  if (reason === null) return; // 사용자가 취소한 경우

  try {
    await callAdminApi(`/admin/accreditations/${recordId}/reject`, {
      method: "PATCH",
      body: JSON.stringify({ reject_reason: reason || null }),
    });
    alert("반려 처리되었습니다.");
    fetchAccreditationRequests();
  } catch (err) {
    alert(`반려 처리 중 오류가 발생했습니다.\n${err.message}`);
  }
}

document.addEventListener("DOMContentLoaded", fetchAccreditationRequests);
