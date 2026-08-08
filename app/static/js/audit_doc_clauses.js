/**
 * Shared clause catalog loader for audit document pages.
 * Prefer master API (standard_clause_masters); cache in sessionStorage;
 * fall back to audit_doc_clauses_fallback.js (last sync date in that file).
 */
(function (global) {
  "use strict";

  var CACHE_KEY = "complais_clause_catalog_v1";
  var API = "/api/v1/demo/audit-docs/clauses";
  var NOTES_CLAUSES = "/api/v1/auditor/audit-notes/clauses";

  function authHeaders() {
    var t = localStorage.getItem("access_token") || "";
    return t ? { Authorization: "Bearer " + t } : {};
  }

  function normalizeList(rows) {
    if (!Array.isArray(rows)) return [];
    return rows
      .map(function (r) {
        var cno = String(r.clause_no || r.id || "").trim();
        if (!cno) return null;
        var topic = String(r.clause_topic || r.clause_title || r.label || "").trim();
        var std = r.standard_key || r.std || "";
        var g =
          r.process_group_name ||
          r.group_name ||
          r.g ||
          (cno.split(".")[0] ? cno.split(".")[0] + "항" : "조항");
        return {
          id: cno,
          std: std,
          g: g,
          label: topic ? (topic.indexOf(cno) === 0 ? topic : cno + " " + topic) : cno,
          family_code: r.family_code || "",
        };
      })
      .filter(Boolean);
  }

  function applyCatalog(clauses, meta) {
    if (!clauses || !clauses.length) return false;
    global.CLAUSES = clauses;
    try {
      CLAUSES = clauses; // eslint-disable-line no-undef
    } catch (e) {
      /* ignore */
    }
    global.ComplaisClauseCatalog = global.ComplaisClauseCatalog || {};
    global.ComplaisClauseCatalog.clauses = clauses;
    global.ComplaisClauseCatalog.meta = meta || {};
    global.ComplaisClauseCatalog.ready = true;
    try {
      document.dispatchEvent(
        new CustomEvent("complais-clauses-ready", {
          detail: { clauses: clauses, meta: meta || {} },
        })
      );
    } catch (e2) {
      /* ignore */
    }
    return true;
  }

  function readCache() {
    try {
      var raw = sessionStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.clauses) && parsed.clauses.length) return parsed;
    } catch (e) {
      /* ignore */
    }
    return null;
  }

  function writeCache(payload) {
    try {
      sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload));
    } catch (e) {
      /* ignore quota */
    }
  }

  function fallbackClauses() {
    var fb = global.ComplaisClauseFallback;
    if (fb && Array.isArray(fb.clauses) && fb.clauses.length) return fb.clauses;
    if (Array.isArray(global.CLAUSES) && global.CLAUSES.length) return global.CLAUSES;
    return [];
  }

  async function fetchDemoCatalog(standardKeys) {
    var qs = "";
    if (standardKeys && standardKeys.length) {
      qs =
        "?" +
        standardKeys
          .map(function (k) {
            return "standard_key=" + encodeURIComponent(k);
          })
          .join("&");
    }
    var res = await fetch(API + qs, { credentials: "same-origin" });
    if (!res.ok) throw new Error("demo clauses " + res.status);
    return res.json();
  }

  async function fetchNotesCatalog(standardKey) {
    var res = await fetch(
      NOTES_CLAUSES + "?standard_key=" + encodeURIComponent(standardKey),
      { credentials: "same-origin", headers: authHeaders() }
    );
    if (!res.ok) throw new Error("notes clauses " + res.status);
    return res.json();
  }

  async function fetch(opts) {
    opts = opts || {};
    var keys = opts.standardKeys || [];
    var cached = readCache();
    if (cached && !opts.force) {
      applyCatalog(cached.clauses, cached.meta);
      return cached.clauses;
    }

    try {
      var data = await fetchDemoCatalog(keys);
      var clauses = normalizeList(data.clauses || data);
      if (clauses.length) {
        var meta = {
          source: data.source || "standard_clause_masters",
          syncDate: data.sync_date || data.synced_at || null,
          counts: data.counts || null,
        };
        writeCache({ clauses: clauses, meta: meta });
        applyCatalog(clauses, meta);
        return clauses;
      }
    } catch (err) {
      console.warn("[audit_doc_clauses] demo catalog failed", err);
    }

    // Authenticated per-standard fallback (existing audit-notes API)
    if (keys.length && (localStorage.getItem("access_token") || "").trim()) {
      try {
        var merged = [];
        var seen = {};
        for (var i = 0; i < keys.length; i++) {
          var rows = await fetchNotesCatalog(keys[i]);
          normalizeList(rows).forEach(function (c) {
            var u = c.std + "|" + c.id;
            if (seen[u]) return;
            seen[u] = 1;
            merged.push(c);
          });
        }
        if (merged.length) {
          var meta2 = { source: "audit-notes/clauses" };
          writeCache({ clauses: merged, meta: meta2 });
          applyCatalog(merged, meta2);
          return merged;
        }
      } catch (err2) {
        console.warn("[audit_doc_clauses] notes catalog failed", err2);
      }
    }

    var fb = fallbackClauses();
    applyCatalog(fb, {
      source: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.source) || "fallback",
      syncDate: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.syncDate) || null,
      counts: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.counts) || null,
    });
    return fb;
  }

  // Seed from embedded fallback immediately (sync)
  applyCatalog(fallbackClauses(), {
    source: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.source) || "fallback",
    syncDate: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.syncDate) || null,
    counts: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.counts) || null,
  });

  global.ComplaisClauseCatalog = {
    fetch: fetch,
    normalizeList: normalizeList,
    cacheKey: CACHE_KEY,
    ready: !!(global.CLAUSES && global.CLAUSES.length),
    clauses: global.CLAUSES || [],
    meta: {
      source: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.source) || "fallback",
      syncDate: (global.ComplaisClauseFallback && global.ComplaisClauseFallback.syncDate) || null,
    },
  };

  document.addEventListener("complais-audit-doc-ready", function (ev) {
    var ctx = (ev && ev.detail) || {};
    var keys = ctx.selected_standard_keys || (ctx.master && ctx.master.standard_keys) || [];
    fetch({ standardKeys: keys }).then(function () {
      try {
        if (typeof global.render === "function") global.render();
        if (typeof global.renderAll === "function") global.renderAll();
      } catch (e) {
        /* ignore */
      }
    });
  });
})(typeof window !== "undefined" ? window : globalThis);
