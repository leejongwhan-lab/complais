/** Minimal enterprise MD apply + yearly recompute UI helper */
(function () {
  const API = (window.COMPLAIS_API_BASE || "/api/v1") + "/enterprise-audit-applications";
  function authHeaders() {
    const t = localStorage.getItem("access_token") || localStorage.getItem("token") || "";
    return { "Content-Type": "application/json", Authorization: t ? "Bearer " + t : "" };
  }
  async function preview(body) {
    const r = await fetch(API + "/preview", { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  async function submit(body) {
    const r = await fetch(API, { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  async function yearly(body) {
    const r = await fetch(API + "/yearly", { method: "POST", headers: authHeaders(), body: JSON.stringify(body) });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  window.ComplaisMdApply = { preview, submit, yearly, API };
})();
