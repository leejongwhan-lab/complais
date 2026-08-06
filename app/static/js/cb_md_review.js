/** Minimal CB MD review panel helper (adjustment ratio / witness / status) */
(function () {
  const API = (window.COMPLAIS_API_BASE || "/api/v1") + "/enterprise-audit-applications";
  function authHeaders() {
    const t = localStorage.getItem("access_token") || localStorage.getItem("token") || "";
    return { "Content-Type": "application/json", Authorization: t ? "Bearer " + t : "" };
  }
  async function list(cbId) {
    const q = cbId ? ("?cb_id=" + encodeURIComponent(cbId)) : "";
    const r = await fetch(API + q, { headers: authHeaders() });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  async function review(id, body) {
    const r = await fetch(API + "/" + id + "/cb-review", {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  window.ComplaisCbMdReview = { list, review, API };
})();
