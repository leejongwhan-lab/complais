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

  function hasKeys(arr) {
    return Array.isArray(arr) && arr.length > 0;
  }

  function stdLabel(k) {
    var list = window.STANDARDS || [];
    for (var i = 0; i < list.length; i++) {
      var x = list[i];
      if (x.k === k || x.standard_key === k || x.legacy_k === k) {
        return x.label || x.l || x.display_code || k;
      }
    }
    return k;
  }

  function syncCriteria(ids, keys) {
    if (!hasKeys(keys)) return;
    var text = keys.map(stdLabel).join(", ");
    (ids || []).forEach(function (id) {
      var el = document.getElementById(id);
      if (el && (!el.value || params.get("force") === "1")) el.value = text;
    });
  }

  /** Prefer non-empty current selection; otherwise take master keys. */
  function mergeKeys(current, keys) {
    if (hasKeys(current)) return current.slice();
    if (hasKeys(keys)) return keys.slice();
    return Array.isArray(current) ? current.slice() : [];
  }

  function rebuildStdGrids(selected, s1, s2) {
    if (typeof window.buildStdGrid !== "function") return;

    // plan.html: buildStdGrid(gridId, stdsVar, criteriaId)
    try {
      if (document.getElementById("s1-std-grid") && s1) {
        window.buildStdGrid("s1-std-grid", s1, "s1-criteria");
        syncCriteria(["s1-criteria"], s1);
      }
      if (document.getElementById("s2-std-grid") && s2) {
        window.buildStdGrid("s2-std-grid", s2, "s2-criteria");
        syncCriteria(["s2-criteria"], s2);
      }
    } catch (_) {
      /* ignore */
    }

    // Single-grid docs: buildStdGrid(gridId) reading selectedStds
    ["a1-std-grid", "d1-std-grid", "p1-std-grid"].forEach(function (gid) {
      if (!document.getElementById(gid)) return;
      try {
        window.buildStdGrid(gid);
      } catch (_) {
        try {
          window.buildStdGrid(gid, selected || [], null);
        } catch (_2) {
          /* ignore */
        }
      }
    });
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
    try {
      STANDARDS = mapped; // eslint-disable-line no-undef
    } catch (_) {
      /* ignore */
    }

    var keys = Array.isArray(selectedKeys) ? selectedKeys.slice() : [];
    var selected = [];
    var s1 = [];
    var s2 = [];

    // selectedStds (recert / application / transfer / special)
    try {
      selected = mergeKeys(
        typeof selectedStds !== "undefined" ? selectedStds : window.selectedStds,
        keys
      );
      selectedStds = selected; // eslint-disable-line no-undef
    } catch (_) {
      selected = mergeKeys(window.selectedStds, keys);
    }
    window.selectedStds = selected;

    // plan.html dual arrays
    try {
      s1 = mergeKeys(typeof s1Stds !== "undefined" ? s1Stds : window.s1Stds, keys);
      s1Stds = s1; // eslint-disable-line no-undef
    } catch (_) {
      s1 = mergeKeys(window.s1Stds, keys);
    }
    window.s1Stds = s1;

    try {
      s2 = mergeKeys(typeof s2Stds !== "undefined" ? s2Stds : window.s2Stds, keys);
      s2Stds = s2; // eslint-disable-line no-undef
    } catch (_) {
      s2 = mergeKeys(window.s2Stds, keys);
    }
    window.s2Stds = s2;

    rebuildStdGrids(selected, s1, s2);

    var active = hasKeys(selected) ? selected : hasKeys(s1) ? s1 : keys;
    syncCriteria(
      ["a1-std", "d1-stds", "p1-std", "c1-criteria", "c1-std", "cert-std"],
      active
    );
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
      ["f-org", "f-addr", "f-scope", "f-std", "f-lead", "f-aud", "f-cb", "f-rep", "f-objective"].forEach(
        function (id) {
          var el = document.getElementById(id);
          if (el && fields[id] && !el.value) el.value = String(fields[id]);
        }
      );
      if (
        window.ComplaisIso19011 &&
        document.getElementById("f-objective") &&
        !document.getElementById("f-objective").value
      ) {
        var stageHint = location.pathname.indexOf("stage1") >= 0 ? "stage1" : "stage2";
        document.getElementById("f-objective").value =
          window.ComplaisIso19011.auditObjectiveFromContext(ctx, stageHint);
      }
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
