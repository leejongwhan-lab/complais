/**
 * Master-DB bridge for certification-audit document HTML pages.
 * Loads /api/v1/demo/audit-docs/context when ?demo=1 or ?contract_id= is present.
 * Replaces hardcoded STANDARDS with standard_masters.standard_key chips
 * and fills field ids from companies / contracts / auditors / CBs.
 */
(function () {
  "use strict";

  var params = new URLSearchParams(location.search);
  var demo = params.get("demo");
  var contractId = params.get("contract_id") || params.get("contract") || "";
  if (!demo && !contractId) {
    // still expose helper for manual use
    window.ComplaisAuditDocMaster = { enabled: false };
    return;
  }
  if (!contractId) contractId = "1";
  if (demo == null) demo = "1";

  var API =
    "/api/v1/demo/audit-docs/context?demo=" +
    encodeURIComponent(demo) +
    "&contract_id=" +
    encodeURIComponent(contractId);

  function setVal(id, value) {
    if (value == null || value === "") return;
    var el = document.getElementById(id);
    if (!el) return;
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT") {
      if (!el.value || params.get("force") === "1") {
        el.value = String(value);
      }
    } else if (!el.textContent || el.textContent === "—" || params.get("force") === "1") {
      el.textContent = String(value);
    }
  }

  function applyStandards(catalog, selectedKeys) {
    if (!Array.isArray(catalog) || !catalog.length) return;
    var mapped = catalog.map(function (s) {
      return {
        k: s.k || s.standard_key,
        standard_key: s.standard_key,
        legacy_k: s.legacy_k,
        label: s.label || s.display_code,
        l: s.l || s.label || s.display_code,
        short: s.short || s.s || s.family_code,
        s: s.s || s.short || s.family_code,
        cls: s.cls || "chip-q",
        c: s.c || s.on || "on-q",
        on: s.on || s.c || "on-q",
        desc: s.desc || s.standard_name || "",
      };
    });
    if (typeof window.STANDARDS !== "undefined") {
      window.STANDARDS = mapped;
    }
    // also assign bare STANDARDS if in global script scope via var — overwrite on window
    try {
      STANDARDS = mapped; // eslint-disable-line no-undef
    } catch (_) {
      /* ignore */
    }

    var keys = Array.isArray(selectedKeys) ? selectedKeys.slice() : [];
    if (typeof window.selectedStds !== "undefined") {
      window.selectedStds = keys;
    }
    try {
      selectedStds = keys; // eslint-disable-line no-undef
    } catch (_) {
      /* ignore */
    }

    ["a1-std-grid", "s1-std-grid", "s2-std-grid"].forEach(function (gid) {
      if (typeof window.buildStdGrid === "function") {
        try {
          window.buildStdGrid(gid);
        } catch (_) {
          /* ignore */
        }
      }
    });
  }

  function banner(ctx) {
    var m = ctx.master || {};
    var bar = document.createElement("div");
    bar.id = "complais-demo-banner";
    bar.setAttribute(
      "style",
      "position:sticky;top:0;z-index:9999;background:#0f172a;color:#e2e8f0;" +
        "padding:8px 14px;font:12px/1.4 Pretendard,system-ui,sans-serif;" +
        "display:flex;flex-wrap:wrap;gap:10px;align-items:center;"
    );
    bar.innerHTML =
      "<strong style='color:#93c5fd'>DEMO · Master DB</strong>" +
      "<span>company_id=" +
      (m.company_id || "") +
      " · " +
      (m.company_name || "") +
      "</span>" +
      "<span>contract_id=" +
      (m.contract_id || "") +
      " · " +
      (m.contract_no || "") +
      "</span>" +
      "<span>" +
      (m.standard_keys || []).join(", ") +
      "</span>" +
      '<a href="/demo/audit-docs?demo=1&contract_id=' +
      encodeURIComponent(m.contract_id || "1") +
      '" style="color:#93c5fd;margin-left:auto">문서 허브</a>';
    document.body.insertBefore(bar, document.body.firstChild);
  }

  fetch(API, { credentials: "same-origin" })
    .then(function (r) {
      if (!r.ok) throw new Error("context " + r.status);
      return r.json();
    })
    .then(function (ctx) {
      window.ComplaisAuditDocMaster = { enabled: true, context: ctx };
      banner(ctx);
      applyStandards(ctx.standards_catalog || [], ctx.selected_standard_keys || []);
      var fields = ctx.fields || {};
      Object.keys(fields).forEach(function (id) {
        setVal(id, fields[id]);
      });
      // Force-fill Stage1/2 sync panel from master (always overwrite empty)
      ["f-org", "f-addr", "f-scope", "f-std", "f-lead", "f-aud", "f-cb", "f-rep"].forEach(
        function (id) {
          var el = document.getElementById(id);
          if (el && fields[id] && !el.value) el.value = String(fields[id]);
        }
      );
      // mirror companyName for PHP-style init
      if (ctx.company && ctx.company.name) {
        window.__SERVER_INIT__ = window.__SERVER_INIT__ || {};
        window.__SERVER_INIT__.companyName = ctx.company.name;
        window.__SERVER_INIT__.contractId = ctx.contract && ctx.contract.id;
        window.__SERVER_INIT__.standardKeys = ctx.selected_standard_keys || [];
      }
      // Stage report re-render hooks
      try {
        if (typeof window.renderAll === "function") window.renderAll();
        if (typeof window.render === "function") window.render();
        if (typeof window.syncData === "function") {
          /* leave optional — may require localStorage */
        }
      } catch (_) {
        /* ignore */
      }
      document.dispatchEvent(
        new CustomEvent("complais-audit-doc-ready", { detail: ctx })
      );
    })
    .catch(function (err) {
      console.warn("[audit_doc_master]", err);
      window.ComplaisAuditDocMaster = { enabled: false, error: String(err) };
    });
})();
