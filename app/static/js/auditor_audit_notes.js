/* Auditor portal — 심사노트 editor (DB clauses + optional KPI + NC modal + AI formalize)
 * Supports preview mode when no contract/assignment is available.
 */
(function () {
  const API = "/api/v1";
  const DEFAULT_STANDARD = "QMS_2015";

  const state = {
    contractId: null,
    preview: false,
    standardKey: null,
    noteId: null,
    session: null,
    clauseNo: null,
    noteSeq: 1,
    pendingNc: null,
    ncGrade: "minor",
    noteMethod: "process", // clause | process (정렬 방식)
    auditMode: null, // single | integrated (contracts.audit_mode)
    auditorName: "",
    isLead: false,
    teamMeeting: false, // 심사팀장 전체 보기
    view: "clause", // clause | interview | matrix
    interviewEntries: {}, // role_key → entry fields (v15)
    ivPersonIdx: 0,
    dirtyClauses: {}, // clause_no::note_seq → true
    navExpanded: {}, // mainClauseNo → bool (하위 조항 아코디언)
    guideOpen: {}, // clause_no::note_seq → bool (상세 가이드 아코디언)
  };

  function noteKey(clauseNo, noteSeq) {
    return String(clauseNo || "") + "::" + String(noteSeq == null ? 1 : noteSeq);
  }

  function clearDirty() {
    state.dirtyClauses = {};
  }

  function markDirty(clauseNo, noteSeq) {
    if (!clauseNo) return;
    state.dirtyClauses[noteKey(clauseNo, noteSeq != null ? noteSeq : state.noteSeq)] = true;
  }

  function clearDirtyClause(clauseNo, noteSeq) {
    const k = noteKey(clauseNo, noteSeq != null ? noteSeq : state.noteSeq);
    if (clauseNo && state.dirtyClauses[k]) {
      delete state.dirtyClauses[k];
    }
  }

  function isClauseSaved(c) {
    /* Mark saved only after successful save API (saved_at set) or session
       load that already has persisted clause content/verdict. */
    if (!c) return false;
    if (c.saved_at) return true;
    if (c.verdict) return true;
    if ((c.note_text || "").trim()) return true;
    return false;
  }

  function clauseNavClass(c) {
    const parts = ["aud-nav-btn"];
    const seq = c.note_seq || 1;
    if (
      c.clause_no === state.clauseNo &&
      seq === (state.noteSeq || 1) &&
      state.view === "clause"
    )
      parts.push("active");
    if (state.dirtyClauses[noteKey(c.clause_no, seq)]) parts.push("is-dirty");
    else if (isClauseSaved(c)) parts.push("is-saved");
    return parts.join(" ");
  }

  function token() {
    return localStorage.getItem("access_token");
  }

  function authHeaders(json) {
    const h = { Authorization: "Bearer " + (token() || "") };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function $(id) {
    return document.getElementById(id);
  }

  function showEditor(show) {
    const ed = $("audit-note-editor");
    const list = $("reports-list-wrap");
    if (ed) {
      /* flex: portal.css 3-pane shell (sticky sides + center doc-wrap scroll) */
      ed.style.display = show ? "flex" : "none";
      ed.setAttribute("aria-hidden", show ? "false" : "true");
      ed.classList.toggle("is-preview", !!(show && state.preview));
      document.body.classList.toggle("aud-note-open", !!show);
    }
    if (list) list.style.display = show ? "none" : "block";
  }

  function toast(msg) {
    const msgEl = $("aud-save-msg");
    if (msgEl) msgEl.textContent = msg;
    let toastEl = $("aud-preview-toast");
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.id = "aud-preview-toast";
      toastEl.className = "aud-preview-toast";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(() => toastEl.classList.remove("show"), 2600);
  }

  function currentClause() {
    if (!state.session || !state.clauseNo) return null;
    const seq = state.noteSeq || 1;
    return (
      (state.session.clauses || []).find(
        (c) => c.clause_no === state.clauseNo && (c.note_seq || 1) === seq
      ) || null
    );
  }

  function dash(v) {
    const s = v == null ? "" : String(v).trim();
    return s || "—";
  }

  function formatAuditDate(data) {
    if (!data) return "—";
    const start = data.audit_date ? String(data.audit_date).slice(0, 10) : "";
    const end = data.audit_period_end ? String(data.audit_period_end).slice(0, 10) : "";
    if (start && end && end !== start) return start + " ~ " + end;
    return start || "—";
  }

  function standardsLabel(data) {
    if (!data) return "—";
    if (data.standards_label) return data.standards_label;
    const items = data.standards || [];
    const bits = items
      .map((s) => s.display_code || s.standard_code || s.standard_key)
      .filter(Boolean);
    if (bits.length) return bits.join(" · ");
    return data.process_standard_code || data.standard_key || "—";
  }

  function cleanTitle(clauseNo, title) {
    let t = String(title || "").trim();
    const no = String(clauseNo || "").trim();
    if (!t) return "";
    if (!no) return t;
    const esc = no.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp("^\\s*" + esc + "(?:\\s*[:.\\-)\\]]\\s*|\\s+)", "i");
    const stripped = t.replace(re, "").trim();
    return stripped || t;
  }

  function clauseTopic(c) {
    if (!c) return "";
    return cleanTitle(c.clause_no, c.clause_topic || c.clause_title || "");
  }

  function clauseLabel(c) {
    if (!c) return "";
    const title = clauseTopic(c);
    return title ? c.clause_no + " " + title : c.clause_no;
  }

  function processGroupName(c) {
    return (c && (c.process_group_name || c.group_name)) || "";
  }

  function majorChapter(clauseNo) {
    const m = String(clauseNo || "").trim().match(/^(\d+)/);
    return m ? m[1] : "";
  }

  function clauseNoSortKey(clauseNo) {
    const parts = [];
    String(clauseNo || "")
      .split(/[/~\-]/)
      .forEach((token) => {
        String(token)
          .trim()
          .split(/[.\s]+/)
          .forEach((p) => {
            if (!p) return;
            if (/^\d+$/.test(p)) parts.push([0, Number(p)]);
            else {
              const m = p.match(/^(\d+)(.*)$/);
              if (m) {
                parts.push([0, Number(m[1])]);
                if (m[2]) parts.push([1, m[2]]);
              } else parts.push([1, p]);
            }
          });
      });
    return parts;
  }

  function cmpClauseNo(a, b) {
    /* Natural ISO order: 4 → 4.1 → 4.1.1 → 5 → … → 9 → 10 (parents before children). */
    const ka = clauseNoSortKey(a);
    const kb = clauseNoSortKey(b);
    const n = Math.max(ka.length, kb.length);
    for (let i = 0; i < n; i++) {
      if (i >= ka.length) return -1; // a is parent prefix of b
      if (i >= kb.length) return 1;
      const xa = ka[i];
      const xb = kb[i];
      if (xa[0] !== xb[0]) return xa[0] - xb[0];
      if (xa[1] < xb[1]) return -1;
      if (xa[1] > xb[1]) return 1;
    }
    return 0;
  }

  function clauseNumParts(clauseNo) {
    const parts = [];
    String(clauseNo || "")
      .split(/[./\s]+/)
      .forEach((p) => {
        if (/^\d+$/.test(p)) parts.push(p);
      });
    return parts;
  }

  function clauseDepth(clauseNo) {
    return clauseNumParts(clauseNo).length;
  }

  function mainClauseKey(clauseNo) {
    /* HLS-level key: 5.1.2 → 5.1 ; 4.1 → 4.1 ; chapter-only 4 → null */
    const parts = clauseNumParts(clauseNo);
    if (parts.length < 2) return null;
    return parts[0] + "." + parts[1];
  }

  function isMainHlsClause(clauseNo) {
    return clauseDepth(clauseNo) === 2;
  }

  function isChapterClause(clauseNo) {
    return clauseDepth(clauseNo) === 1;
  }

  function sortedClauses(clauses) {
    return (clauses || []).slice().sort((a, b) => {
      const cmp = cmpClauseNo(a.clause_no, b.clause_no);
      if (cmp !== 0) return cmp;
      return (a.note_seq || 1) - (b.note_seq || 1);
    });
  }

  function chapterSortRank(chap) {
    const n = Number(chap);
    return Number.isFinite(n) ? n : 999;
  }

  function navChildKey(mainKey) {
    return String(mainKey || "");
  }

  function isNavExpanded(mainKey) {
    return !!state.navExpanded[navChildKey(mainKey)];
  }

  function toggleNavExpanded(mainKey) {
    const k = navChildKey(mainKey);
    state.navExpanded[k] = !state.navExpanded[k];
  }

  function guideKey(clauseNo, noteSeq) {
    return noteKey(clauseNo, noteSeq);
  }

  function isGuideOpen(clauseNo, noteSeq) {
    return !!state.guideOpen[guideKey(clauseNo, noteSeq)];
  }

  function toggleGuideOpen(clauseNo, noteSeq) {
    const k = guideKey(clauseNo, noteSeq);
    state.guideOpen[k] = !state.guideOpen[k];
  }

  function renderNavBtn(c, extraClass) {
    const seq = c.note_seq || 1;
    const cls =
      clauseNavClass(c) + (extraClass ? " " + extraClass : "");
    const mark = c.verdict
      ? `<span class="v">${esc(verdictLabel(c.verdict))}</span>`
      : "";
    const extra =
      seq > 1 ? `<span class="v">추가 ${esc(seq)}</span>` : "";
    return `<button type="button" class="${cls}" data-clause="${esc(
      c.clause_no
    )}" data-note-seq="${esc(seq)}" data-hls-code="${esc(
      c.hls_code || ""
    )}" data-process-group-id="${esc(
      c.process_group_id || ""
    )}"><span class="cno">${esc(c.clause_no)}</span> <span class="ctitle">${esc(
      clauseTopic(c)
    )}</span>${extra}${mark}</button>`;
  }

  function buildMainClauseTree(clauses) {
    /* Top-level = HLS main (4.1, 5.1…); deeper under parent; chapter rows → headers. */
    const sorted = sortedClauses(clauses);
    const chapterTitles = {};
    sorted.forEach((c) => {
      if (isChapterClause(c.clause_no)) {
        const ch = majorChapter(c.clause_no);
        if (ch && !chapterTitles[ch]) chapterTitles[ch] = clauseTopic(c) || "";
      }
    });
    const mains = [];
    const childrenByMain = {};
    const orphans = [];
    sorted.forEach((c) => {
      if (isChapterClause(c.clause_no)) return;
      const mainKey = mainClauseKey(c.clause_no);
      if (!mainKey) {
        orphans.push(c);
        return;
      }
      if (isMainHlsClause(c.clause_no)) {
        mains.push(c);
        if (!childrenByMain[mainKey]) childrenByMain[mainKey] = [];
      } else {
        if (!childrenByMain[mainKey]) childrenByMain[mainKey] = [];
        childrenByMain[mainKey].push(c);
      }
    });
    /* Ensure parent slot exists when only sub-clauses are in scope */
    Object.keys(childrenByMain).forEach((mk) => {
      if (!mains.some((m) => mainClauseKey(m.clause_no) === mk)) {
        const kids = childrenByMain[mk];
        if (kids && kids.length) {
          /* synthetic nav parent from first child meta */
          const base = kids[0];
          mains.push(
            Object.assign({}, base, {
              clause_no: mk,
              note_seq: 1,
              clause_topic: clauseTopic(base) || mk,
              clause_title: clauseTopic(base) || mk,
              _synthetic_main: true,
            })
          );
        }
      }
    });
    mains.sort((a, b) => {
      const cmp = cmpClauseNo(a.clause_no, b.clause_no);
      if (cmp !== 0) return cmp;
      return (a.note_seq || 1) - (b.note_seq || 1);
    });
    return { mains, childrenByMain, chapterTitles, orphans, sorted };
  }

  function kpiIdOf(k) {
    return (k && (k.kpi_id || k.key)) || "";
  }

  function kpiNameOf(k) {
    return (k && (k.kpi_name || k.label || k.kpi_id || k.key)) || "";
  }

  function renderKpiPanel(title, hint, kpis, values, emptyMsg) {
    const list = kpis || [];
    const body = list.length
      ? `<div class="aud-kpi-list">${list
          .map((k) => {
            const kid = kpiIdOf(k);
            const val = (values && (values[kid] || values[k.key])) || "";
            return `<div class="aud-kpi-row">
              <label>${esc(kpiNameOf(k))}</label>
              <input data-kpi-id="${esc(kid)}" value="${esc(val)}" placeholder="미입력 가능" />
            </div>`;
          })
          .join("")}</div>`
      : `<p class="muted aud-kpi-empty">${esc(emptyMsg || "연관 KPI 없음 — 미입력으로 저장 가능")}</p>`;
    return `<div class="aud-kpi-panel">
      <h4 class="aud-sec-hd">${esc(title)} <span class="muted">${esc(hint || "")}</span></h4>
      ${body}
    </div>`;
  }

  function verdictLabel(v) {
    if (!v) return "";
    if (v === "적합") return "적합";
    if (v.indexOf("중대") >= 0) return "Major";
    if (v.indexOf("경미") >= 0) return "Minor";
    if (v.indexOf("관찰") >= 0) return "OBS";
    return v;
  }

  function syncMethodTabs() {
    document.querySelectorAll(".aud-mode-tab").forEach((btn) => {
      const m = btn.getAttribute("data-method");
      btn.classList.toggle("active", m === state.noteMethod);
    });
  }

  function syncViewButtons() {
    const ivBtn = $("aud-iv-toggle-btn");
    const mxBtn = $("aud-matrix-toggle-btn");
    const tmBtn = $("aud-team-meeting-btn");
    if (ivBtn) {
      ivBtn.textContent = state.view === "interview" ? "심사로 돌아가기" : "면담 작성";
    }
    if (mxBtn) {
      mxBtn.textContent = state.view === "matrix" ? "심사로 돌아가기" : "심사매트릭스";
    }
    if (tmBtn) {
      const show = !state.preview && state.isLead;
      tmBtn.style.display = show ? "" : "none";
      tmBtn.classList.toggle("active", !!state.teamMeeting);
      tmBtn.textContent = state.teamMeeting ? "내 배정으로 돌아가기" : "심사팀회의 (전체)";
    }
  }

  function syncAuditModeBadge() {
    const badge = $("aud-audit-mode-badge");
    if (!badge) return;
    const label =
      state.session && state.session.audit_mode_label
        ? state.session.audit_mode_label
        : state.auditMode === "integrated"
          ? "통합심사"
          : state.auditMode === "single"
            ? "단일심사"
            : "";
    if (!label || state.preview) {
      badge.style.display = "none";
      badge.textContent = "";
      return;
    }
    badge.style.display = "inline-flex";
    badge.textContent = label;
    badge.classList.toggle("is-integrated", state.auditMode === "integrated");
  }

  async function setTeamMeeting(on) {
    if (!state.isLead && on) {
      toast("심사팀장만 심사팀회의 모드를 사용할 수 있습니다.");
      return;
    }
    state.teamMeeting = !!on;
    state.clauseNo = null;
    state.noteSeq = 1;
    clearDirty();
    syncViewButtons();
    if (state.preview || !state.contractId) return;
    await loadSession(state.contractId, state.standardKey, false);
  }

  function interviewTemplates() {
    return (state.session && state.session.interview_templates) || [];
  }

  function emptyIvEntry(tpl) {
    return {
      role_key: tpl.role_key,
      role: tpl.role || "",
      name: "",
      dept: "",
      position: "",
      date: "",
      startTime: "",
      endTime: "",
      place: "",
      qa_content: "",
      overall: "",
    };
  }

  function ensureIvEntry(rk, tpl) {
    if (!state.interviewEntries[rk]) {
      state.interviewEntries[rk] = emptyIvEntry(tpl || { role_key: rk, role: rk });
    }
    return state.interviewEntries[rk];
  }

  function ivIsDone(d) {
    return !!(d && (d.name || "").trim() && ((d.qa_content || "").trim() || (d.overall || "").trim()));
  }

  function hydrateInterviewData(session) {
    state.interviewEntries = {};
    const templates = (session && session.interview_templates) || [];
    const byKey = {};
    ((session && session.interview_entries) || []).forEach((e) => {
      if (e && e.role_key) byKey[e.role_key] = e;
    });
    templates.forEach((tpl) => {
      const saved = byKey[tpl.role_key] || {};
      state.interviewEntries[tpl.role_key] = {
        role_key: tpl.role_key,
        role: tpl.role || saved.role || "",
        name: saved.name || "",
        dept: saved.dept || "",
        position: saved.position || "",
        date: saved.date || "",
        startTime: saved.startTime || "",
        endTime: saved.endTime || "",
        place: saved.place || "",
        qa_content: saved.qa_content || "",
        overall: saved.overall || "",
      };
    });
    // orphan saved entries not in templates
    Object.keys(byKey).forEach((rk) => {
      if (!state.interviewEntries[rk]) {
        const saved = byKey[rk];
        state.interviewEntries[rk] = {
          role_key: rk,
          role: saved.role || rk,
          name: saved.name || "",
          dept: saved.dept || "",
          position: saved.position || "",
          date: saved.date || "",
          startTime: saved.startTime || "",
          endTime: saved.endTime || "",
          place: saved.place || "",
          qa_content: saved.qa_content || "",
          overall: saved.overall || "",
        };
      }
    });
    if (state.ivPersonIdx >= templates.length) state.ivPersonIdx = 0;
  }

  function collectIvFromForm(rk) {
    const d = ensureIvEntry(rk);
    const g = (id) => (($(id) && $(id).value) || "").trim();
    d.name = g("aud-iv-name");
    d.dept = g("aud-iv-dept");
    d.position = g("aud-iv-position");
    d.date = g("aud-iv-date");
    d.startTime = g("aud-iv-start");
    d.endTime = g("aud-iv-end");
    d.place = g("aud-iv-place");
    d.qa_content = (($("aud-iv-qa") && $("aud-iv-qa").value) || "").trim();
    d.overall = (($("aud-iv-overall") && $("aud-iv-overall").value) || "").trim();
    return d;
  }

  function buildIvNavPanel() {
    const body = $("aud-iv-nav-body");
    const countEl = $("aud-iv-nav-count");
    if (!body) return;
    const tpls = interviewTemplates();
    const doneN = tpls.filter((t) => ivIsDone(state.interviewEntries[t.role_key])).length;
    if (countEl) countEl.textContent = tpls.length ? `(${doneN}/${tpls.length})` : "";
    if (!tpls.length) {
      body.innerHTML = '<div class="aud-iv-mini muted">표준 선택 후 면담 목록 표시</div>';
      return;
    }
    body.innerHTML = tpls
      .map((tpl, idx) => {
        const d = ensureIvEntry(tpl.role_key, tpl);
        const done = ivIsDone(d);
        const active = state.view === "interview" && state.ivPersonIdx === idx ? " active" : "";
        const star = tpl.mandatory ? " [필수]" : "";
        return `<div class="aud-iv-mini${done ? " done" : ""}${active}" data-iv-person="${idx}">
          <span style="flex:1">${esc(tpl.role)}${star}${done ? " · 작성" : ""}</span>
        </div>`;
      })
      .join("");
  }

  function entriesPayload() {
    const tpls = interviewTemplates();
    const keys = tpls.length
      ? tpls.map((t) => t.role_key)
      : Object.keys(state.interviewEntries);
    return keys.map((rk) => {
      const d = state.interviewEntries[rk] || { role_key: rk };
      return {
        role_key: rk,
        role: d.role || "",
        name: d.name || "",
        dept: d.dept || "",
        position: d.position || "",
        date: d.date || "",
        startTime: d.startTime || "",
        endTime: d.endTime || "",
        place: d.place || "",
        qa_content: d.qa_content || "",
        overall: d.overall || "",
      };
    });
  }

  async function persistInterviews(opts) {
    const tpls = interviewTemplates();
    const tpl = tpls[state.ivPersonIdx];
    if (tpl) collectIvFromForm(tpl.role_key);
    if (state.preview || !state.contractId) {
      toast("미리보기 — 면담은 DB에 저장되지 않습니다");
      buildIvNavPanel();
      if (opts && opts.next && tpls[state.ivPersonIdx + 1]) {
        state.ivPersonIdx += 1;
        renderIvMain();
      }
      return;
    }
    try {
      const res = await fetch(API + "/auditor/audit-notes/interviews", {
        method: "PUT",
        headers: authHeaders(true),
        body: JSON.stringify({
          contract_id: Number(state.contractId),
          entries: entriesPayload(),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "면담 저장 실패");
      toast(data.message || "면담 저장됨");
      buildIvNavPanel();
      if (opts && opts.next && tpls[state.ivPersonIdx + 1]) {
        state.ivPersonIdx += 1;
        renderIvMain();
      }
    } catch (e) {
      toast(e.message || "면담 저장 실패");
    }
  }

  function renderIvMain() {
    const box = $("aud-note-main");
    if (!box) return;
    const tpls = interviewTemplates();
    if (!tpls.length) {
      box.innerHTML =
        '<div class="aud-empty">표준을 선택하면 필수 면담 목록이 표시됩니다.</div>';
      return;
    }
    if (state.ivPersonIdx >= tpls.length) state.ivPersonIdx = 0;
    const tpl = tpls[state.ivPersonIdx];
    const d = ensureIvEntry(tpl.role_key, tpl);
    const chips = tpls
      .map((t, idx) => {
        const done = ivIsDone(state.interviewEntries[t.role_key]);
        const active = idx === state.ivPersonIdx ? " active" : "";
        return `<button type="button" class="aud-iv-chip${active}${done ? " done" : ""}" data-iv-person="${idx}">${esc(t.role)}${t.mandatory ? " ·필수" : ""}</button>`;
      })
      .join("");
    const guideQs = (tpl.questions || [])
      .map((q, i) => `<li><span class="muted">Q${i + 1}.</span> ${esc(q)}</li>`)
      .join("");
    const hasNext = state.ivPersonIdx + 1 < tpls.length;
    box.innerHTML = `<div class="aud-iv-main-box">
      <div class="aud-iv-main-hd">
        <strong>필수 면담 계획 · 작성 (${tpls.length}명)</strong>
        <span class="muted" style="font-size:0.75rem">면담 대상을 선택하여 작성하세요</span>
      </div>
      <div class="aud-iv-chips">${chips}</div>
      <div class="aud-iv-person-content">
        <div class="aud-iv-role-title">${esc(tpl.role)}${tpl.mandatory ? ' <span class="aud-iv-badge">필수</span>' : ""}</div>
        <div class="aud-iv-meta-grid">
          <label>면담 대상자 성명 <span class="req">*</span>
            <input id="aud-iv-name" class="aud-iv-inp" placeholder="성명" value="${esc(d.name || "")}" />
          </label>
          <label>부서
            <input id="aud-iv-dept" class="aud-iv-inp" placeholder="부서명" value="${esc(d.dept || "")}" />
          </label>
          <label>직급/직책
            <input id="aud-iv-position" class="aud-iv-inp" placeholder="팀장, 과장 등" value="${esc(d.position || "")}" />
          </label>
          <label>면담 일자
            <input id="aud-iv-date" class="aud-iv-inp" type="date" value="${esc(d.date || "")}" />
          </label>
          <label>시작 시간
            <input id="aud-iv-start" class="aud-iv-inp" type="time" value="${esc(d.startTime || "")}" />
          </label>
          <label>종료 시간
            <input id="aud-iv-end" class="aud-iv-inp" type="time" value="${esc(d.endTime || "")}" />
          </label>
          <label class="span-2">면담 장소
            <input id="aud-iv-place" class="aud-iv-inp" placeholder="회의실명 또는 위치" value="${esc(d.place || "")}" />
          </label>
        </div>
        <div class="aud-iv-q-guide">
          <div class="aud-iv-sec-title">권장 질문 (참고)</div>
          <ul>${guideQs || "<li class='muted'>등록된 질문 없음</li>"}</ul>
        </div>
        <div class="aud-iv-q-box">
          <div class="aud-iv-sec-title">면담 질문 및 응답 기록</div>
          <textarea id="aud-iv-qa" class="aud-iv-content" rows="10" placeholder="모든 질문·응답을 이 칸에 기록하세요. (질문별 박스는 하나로 통합)">${esc(d.qa_content || "")}</textarea>
        </div>
        <div class="aud-iv-overall-box">
          <div class="aud-iv-sec-title">종합 면담 의견 / 특이사항</div>
          <textarea id="aud-iv-overall" class="aud-iv-content" rows="4" placeholder="면담 전반에 대한 심사원 의견, 추가 관찰사항, 특이사항 등">${esc(d.overall || "")}</textarea>
        </div>
        <div style="display:flex;justify-content:flex-end;margin-top:10px;gap:8px">
          <button type="button" class="btn" id="aud-iv-save-btn">${hasNext ? "저장 · 다음 면담" : "저장 · 완료"}</button>
        </div>
      </div>
    </div>`;
    ["aud-iv-name", "aud-iv-dept", "aud-iv-position", "aud-iv-date", "aud-iv-start", "aud-iv-end", "aud-iv-place", "aud-iv-qa", "aud-iv-overall"].forEach((id) => {
      $(id)?.addEventListener("input", () => {
        collectIvFromForm(tpl.role_key);
        buildIvNavPanel();
      });
    });
    $("aud-iv-save-btn")?.addEventListener("click", () => persistInterviews({ next: hasNext }));
    buildIvNavPanel();
  }

  async function renderMatrix() {
    const box = $("aud-note-main");
    if (!box) return;
    if (state.preview || !state.contractId) {
      // Local coverage from in-memory session clauses
      const clauses = (state.session && state.session.clauses) || [];
      const written = clauses.filter((c) => c.verdict || (c.note_text || "").trim());
      const missing = clauses.filter((c) => !(c.verdict || (c.note_text || "").trim()));
      const pct = clauses.length ? Math.round((written.length / clauses.length) * 1000) / 10 : 0;
      box.innerHTML = buildMatrixHtml({
        standard_key: state.standardKey,
        required_count: clauses.length,
        written_count: written.length,
        missing_count: missing.length,
        coverage_pct: pct,
        cells: clauses.map((c) => ({
          clause_no: c.clause_no,
          clause_topic: c.clause_topic || c.clause_title,
          clause_title: c.clause_topic || c.clause_title,
          written: !!(c.verdict || (c.note_text || "").trim()),
          verdict: c.verdict,
          missing: !(c.verdict || (c.note_text || "").trim()),
          audit_method: null,
        })),
        missing_clauses: missing.map((c) => c.clause_no),
        preview: true,
      });
      return;
    }
    box.innerHTML = '<div class="aud-empty">심사매트릭스 불러오는 중…</div>';
    try {
      const q =
        "?contract_id=" +
        encodeURIComponent(state.contractId) +
        "&standard_key=" +
        encodeURIComponent(state.standardKey || DEFAULT_STANDARD) +
        (state.teamMeeting ? "&team_meeting=1" : "");
      const res = await fetch(API + "/auditor/audit-notes/matrix" + q, {
        headers: authHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "매트릭스 조회 실패");
      box.innerHTML = buildMatrixHtml(data);
    } catch (e) {
      box.innerHTML = '<div class="aud-empty">' + esc(e.message || "매트릭스 조회 실패") + "</div>";
    }
  }

  function buildMatrixHtml(data) {
    const miss = data.missing_count || 0;
    const pct = data.coverage_pct || 0;
    const multi =
      (data.audit_mode === "integrated" || (data.standards || []).length > 1) &&
      (data.cells || []).some((c) => c.standard_code || c.standard_key);
    const rows = (data.cells || [])
      .map((c) => {
        const cls = c.missing ? "missing" : "written";
        const badge = c.missing
          ? '<span class="aud-matrix-badge miss">빠짐</span>'
          : '<span class="aud-matrix-badge done">작성</span>';
        const method =
          c.audit_method === "clause"
            ? "조항"
            : c.audit_method === "process"
              ? "프로세스"
              : "—";
        const stdCell = multi
          ? `<td>${esc(c.standard_code || c.standard_key || "")}</td>`
          : "";
        return `<tr class="${cls}" data-clause="${esc(c.clause_no)}" data-standard="${esc(c.standard_key || "")}" style="cursor:pointer">
          <td>${badge}</td>
          ${stdCell}
          <td><strong>${esc(c.clause_no)}</strong></td>
          <td>${esc(cleanTitle(c.clause_no, c.clause_topic || c.clause_title || ""))}</td>
          <td>${esc(verdictLabel(c.verdict) || "—")}</td>
          <td>${esc(method)}</td>
        </tr>`;
      })
      .join("");
    const modeBit = data.audit_mode_label ? " · " + data.audit_mode_label : "";
    const teamBit = state.teamMeeting ? " · 심사팀회의(전체)" : "";
    const headCols = multi
      ? "<th>상태</th><th>표준</th><th>조항</th><th>제목</th><th>판정</th><th>방식</th>"
      : "<th>상태</th><th>조항</th><th>제목</th><th>판정</th><th>방식</th>";
    const colSpan = multi ? 6 : 5;
    return `<div class="aud-matrix-box">
      <div class="aud-matrix-hd">
        <div>
          <strong>보고서 심사매트릭스</strong>
          <div class="muted" style="font-size:0.78rem;margin-top:2px">
            ${esc(data.standard_key || "")}${esc(modeBit)}${esc(teamBit)} · 계획서 배정 기준 · 빠짐심사 점검
            ${data.preview ? " (미리보기)" : ""}
          </div>
        </div>
        <div class="aud-matrix-stats">
          <span class="aud-matrix-stat">필수 ${data.required_count || 0}</span>
          <span class="aud-matrix-stat ok">작성 ${data.written_count || 0}</span>
          <span class="aud-matrix-stat ${miss ? "warn" : "ok"}">빠짐 ${miss}</span>
          <span class="aud-matrix-stat ${pct >= 100 ? "ok" : "warn"}">커버리지 ${pct}%</span>
        </div>
      </div>
      <div style="max-height:58vh;overflow:auto">
        <table class="aud-matrix-table">
          <thead><tr>${headCols}</tr></thead>
          <tbody>${rows || '<tr><td colspan="' + colSpan + '" class="muted">계획서 배정 조항 없음</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;
  }

  function renderActiveView() {
    syncViewButtons();
    syncMethodTabs();
    if (state.view === "interview") {
      renderIvMain();
      return;
    }
    if (state.view === "matrix") {
      renderMatrix();
      return;
    }
    renderMain();
  }

  async function setNoteMethod(method) {
    const m = method === "clause" ? "clause" : "process";
    state.noteMethod = m;
    state.view = "clause";
    state.clauseNo = null;
    state.noteSeq = 1;
    clearDirty();
    syncMethodTabs();
    if (state.preview || !state.contractId) {
      await loadSession(null, state.standardKey, true, { forceMethod: true });
      return;
    }
    try {
      await fetch(API + "/auditor/audit-notes/method", {
        method: "PUT",
        headers: authHeaders(true),
        body: JSON.stringify({
          contract_id: Number(state.contractId),
          note_method: m,
        }),
      });
    } catch (_e) {
      /* soft */
    }
    await loadSession(state.contractId, state.standardKey, false, { forceMethod: true });
  }

  function renderMainBranch(mains, childrenByMain, opts) {
    /* Shared accordion branch for clause + process nav (main HLS only). */
    opts = opts || {};
    let html = "";
    let lastChap = null;
    mains.forEach((c) => {
      if (c._synthetic_main && !(childrenByMain[mainClauseKey(c.clause_no)] || []).length) {
        return;
      }
      const chap = majorChapter(c.clause_no) || "기타";
      if (opts.showChapter !== false && chap !== lastChap) {
        const title = (opts.chapterTitles && opts.chapterTitles[chap]) || "";
        html +=
          `<div class="grp grp-chapter">제${esc(chap)}장` +
          (title ? ` <span class="grp-chapter-title">${esc(title)}</span>` : "") +
          `</div>`;
        lastChap = chap;
      }
      const mainKey = mainClauseKey(c.clause_no) || c.clause_no;
      const kids = (childrenByMain[mainKey] || []).slice().sort((a, b) => {
        const cmp = cmpClauseNo(a.clause_no, b.clause_no);
        if (cmp !== 0) return cmp;
        return (a.note_seq || 1) - (b.note_seq || 1);
      });
      const expanded = c._synthetic_main || isNavExpanded(mainKey);
      html += `<div class="aud-nav-main-wrap">`;
      if (!c._synthetic_main) {
        html += renderNavBtn(c, opts.btnClass || "");
      } else {
        html += `<div class="aud-nav-synth-main"><span class="cno">${esc(
          mainKey
        )}</span> <span class="ctitle muted">하위 조항</span></div>`;
      }
      if (kids.length) {
        html +=
          `<button type="button" class="aud-nav-toggle" data-nav-toggle="${esc(
            mainKey
          )}" aria-expanded="${expanded ? "true" : "false"}">` +
          (expanded ? "▲ 하위 조항 접기" : "▼ 하위 조항 펼치기") +
          ` <span class="aud-nav-toggle-n">${kids.length}</span></button>`;
        if (expanded) {
          html += `<div class="aud-nav-children">`;
          kids.forEach((ch) => {
            html += renderNavBtn(ch, "nav-child" + (opts.btnClass ? " " + opts.btnClass : ""));
          });
          html += `</div>`;
        }
      }
      html += `</div>`;
    });
    return html;
  }

  function renderNav() {
    const box = $("aud-note-nav");
    if (!box || !state.session) return;
    const clauses = state.session.clauses || [];
    const isClause = state.noteMethod === "clause";
    box.classList.toggle("aud-note-nav--clause", isClause);
    box.classList.toggle("aud-note-nav--process", !isClause);
    if (!clauses.length) {
      const scopeMsg =
        (state.session && state.session.scope_message) ||
        (state.preview
          ? "이 표준의 조항이 DB에 없습니다."
          : "계획서에 배정된 공정/조항이 없습니다.");
      box.innerHTML =
        '<div class="aud-empty">' +
        esc(scopeMsg) +
        '<br/><span class="muted">' +
        (state.preview
          ? "표준을 바꿔 보거나 마스터 시드를 확인하세요."
          : state.teamMeeting
            ? "팀 전체 계획서 항목이 비어 있습니다."
            : "본인에게 배정된 계획서 항목만 표시됩니다.") +
        "</span></div>";
      return;
    }

    let html =
      '<div class="aud-nav-mode-label">' +
      (isClause ? "조항심사" : "프로세스심사") +
      "</div>";

    if (isClause) {
      const tree = buildMainClauseTree(clauses);
      html += renderMainBranch(tree.mains, tree.childrenByMain, {
        chapterTitles: tree.chapterTitles,
      });
      if (tree.orphans.length) {
        html += `<div class="grp grp-chapter">기타</div>`;
        sortedClauses(tree.orphans).forEach((c) => {
          html += renderNavBtn(c, "");
        });
      }
    } else {
      /* Process: PG groups ordered by earliest ISO chapter (4 first), main-clause accordion inside */
      const byPg = {};
      const pgMeta = {};
      sortedClauses(clauses).forEach((c) => {
        if (isChapterClause(c.clause_no)) return;
        const gid = c.process_group_id || processGroupName(c) || "PG";
        if (!byPg[gid]) byPg[gid] = [];
        byPg[gid].push(c);
        if (!pgMeta[gid]) {
          pgMeta[gid] = {
            id: c.process_group_id || "",
            name: processGroupName(c) || "프로세스그룹",
          };
        }
      });
      const pgOrder = Object.keys(byPg).sort((a, b) => {
        const minA = byPg[a].reduce(
          (m, c) => (cmpClauseNo(c.clause_no, m) < 0 ? c.clause_no : m),
          byPg[a][0].clause_no
        );
        const minB = byPg[b].reduce(
          (m, c) => (cmpClauseNo(c.clause_no, m) < 0 ? c.clause_no : m),
          byPg[b][0].clause_no
        );
        const ca = chapterSortRank(majorChapter(minA));
        const cb = chapterSortRank(majorChapter(minB));
        if (ca !== cb) return ca - cb;
        return cmpClauseNo(minA, minB);
      });
      pgOrder.forEach((gid) => {
        const meta = pgMeta[gid];
        html += `<div class="grp grp-process" data-process-group-id="${esc(
          meta.id
        )}">${esc(meta.name)}</div>`;
        const tree = buildMainClauseTree(byPg[gid]);
        html += renderMainBranch(tree.mains, tree.childrenByMain, {
          showChapter: true,
          chapterTitles: tree.chapterTitles,
          btnClass: "nav-under-process",
        });
      });
    }
    box.innerHTML = html;
  }

  function renderMain() {
    const box = $("aud-note-main");
    if (!box) return;
    if (state.view !== "clause") {
      renderActiveView();
      return;
    }
    const c = currentClause();
    if (!c) {
      box.innerHTML =
        '<div class="aud-empty">좌측에서 조항을 선택하세요.' +
        (state.preview
          ? '<br/><span class="muted">미리보기 모드 — 표준 선택·조항 탐색만 가능합니다.</span>'
          : "") +
        '<br/><span class="muted">심사방식: ' +
        (state.noteMethod === "clause" ? "조항심사" : "프로세스심사") +
        "</span></div>";
      return;
    }
    const noteSeq = c.note_seq || 1;
    const isoKpis =
      c.iso_audit_kpis && c.iso_audit_kpis.length
        ? c.iso_audit_kpis
        : c.default_kpis || [];
    const esgKpis = c.esg_kpis || [];
    const kpiHtml =
      `<div class="aud-kpi-dual">` +
      renderKpiPanel(
        "ISO 심사 KPI",
        "(iso_audit / audit_kpi · 선택)",
        isoKpis,
        c.kpi_values,
        "이 조항에 연결된 ISO 심사 KPI 없음 — 미입력 저장 가능"
      ) +
      renderKpiPanel(
        "ESG KPI",
        "(esg_master · 선택)",
        esgKpis,
        c.kpi_values,
        "이 조항에 연결된 ESG KPI 없음 — 미입력 저장 가능"
      ) +
      `</div>`;

    const cps = c.checkpoints || [];
    const guideOpen = isGuideOpen(c.clause_no, noteSeq);
    const hasGuideBody = !!(c.question && String(c.question).trim()) || cps.length > 0;
    const cpList = cps.length
      ? `<ul class="aud-cp-list">${cps
          .map(
            (x) =>
              `<li>${esc(x.title || "")}${
                x.hint ? ` <span class="muted">— ${esc(x.hint)}</span>` : ""
              }</li>`
          )
          .join("")}</ul>`
      : "";
    const guideInner = `
      <div class="aud-guide-body">
        ${
          c.question && String(c.question).trim()
            ? `<div class="q aud-guide-q">${esc(c.question)}</div>`
            : `<div class="q aud-guide-q muted">등록된 가이드 질문이 없습니다.</div>`
        }
        ${
          cps.length
            ? `<div class="aud-cp-hd">체크포인트 <span class="muted">(참고 · 검증 게이트 아님)</span></div>${cpList}`
            : `<p class="muted aud-cp-empty">연결된 체크포인트 없음</p>`
        }
      </div>`;
    const guideHtml = hasGuideBody
      ? `<div class="aud-guide-acc">
          <button type="button" class="aud-guide-toggle" id="aud-guide-toggle" aria-expanded="${
            guideOpen ? "true" : "false"
          }">${
            guideOpen
              ? "▲ 상세 가이드 및 체크포인트 접기"
              : "▼ 상세 가이드 및 체크포인트 펼치기"
          }</button>
          <div class="aud-guide-panel" id="aud-guide-panel" style="display:${
            guideOpen ? "block" : "none"
          }">${guideInner}</div>
        </div>`
      : `<div class="aud-guide-acc"><p class="muted aud-cp-empty">상세 가이드/체크포인트 없음</p></div>`;

    const previewBanner = state.preview
      ? `<div class="aud-preview-banner">미리보기 (배정 없음) — 저장은 DB에 반영되지 않습니다.</div>`
      : "";
    const teamBanner =
      !state.preview && state.teamMeeting
        ? `<div class="aud-team-banner">심사팀회의 — 팀 전체 배정 공정/조항 (부적합 정도 판정)</div>`
        : "";
    const methodBanner =
      `<div class="aud-method-banner ${
        state.noteMethod === "clause" ? "is-clause" : "is-process"
      }">심사방식: ${
        state.noteMethod === "clause" ? "조항심사" : "프로세스심사"
      }${noteSeq > 1 ? " · 추가 노트 " + noteSeq : ""}</div>`;
    const metaBits = [
      c.standard_code ? "standard_code: " + c.standard_code : "",
      state.noteMethod === "process" && c.process_group_id
        ? "process_group_id: " + c.process_group_id
        : "",
      c.hls_code ? "hls_code: " + c.hls_code : "",
      noteSeq > 1 ? "note_seq: " + noteSeq : "",
      c.plan_dept ? "계획서 부서/공정: " + c.plan_dept : "",
    ]
      .filter(Boolean)
      .join(" · ");
    const addNoteBtn =
      state.noteMethod === "process"
        ? `<button type="button" class="btn ghost" id="aud-btn-add-note">심사노트 추가</button>`
        : "";
    const ncrBadge = c.ncr_grade
      ? `<span class="aud-ncr-badge">${esc(
          c.ncr_grade === "major"
            ? "Major"
            : c.ncr_grade === "observation"
              ? "OBS"
              : "Minor"
        )}</span>`
      : "";

    box.innerHTML = `
      ${previewBanner}
      ${teamBanner}
      ${methodBanner}
      <h3><span class="cno">${esc(c.clause_no)}</span> <span class="ctitle">${esc(clauseTopic(c))}</span>${
        noteSeq > 1 ? ` <span class="muted">(추가 ${esc(noteSeq)})</span>` : ""
      }${ncrBadge}</h3>
      ${metaBits ? `<p class="muted aud-clause-meta">${esc(metaBits)}</p>` : ""}
      ${guideHtml}
      ${kpiHtml}
      <h4 class="aud-sec-hd">심사 노트</h4>
      <textarea id="aud-note-text" rows="7" placeholder="현장 관찰·확인 내용을 자유롭게 기록하세요.">${esc(c.note_text || "")}</textarea>
      <div class="aud-judge">
        <button type="button" class="btn" id="aud-btn-nc" data-clause-no="${esc(
          c.clause_no
        )}">부적합/관찰 작성</button>
        <button type="button" class="btn ghost" id="aud-btn-ok">적합</button>
        <button type="button" class="btn ghost" id="aud-btn-save">저장</button>
        ${addNoteBtn}
      </div>
      <div class="aud-save-msg" id="aud-save-msg"></div>
    `;

    $("aud-note-text")?.addEventListener("input", () => {
      markDirty(c.clause_no, noteSeq);
      renderNav();
    });
    box.querySelectorAll(".aud-kpi-row input").forEach((el) => {
      el.addEventListener("input", () => {
        markDirty(c.clause_no, noteSeq);
        renderNav();
      });
    });
    $("aud-guide-toggle")?.addEventListener("click", () => {
      toggleGuideOpen(c.clause_no, noteSeq);
      renderMain();
    });
    $("aud-btn-nc")?.addEventListener("click", () => openNcModal());
    $("aud-btn-ok")?.addEventListener("click", () => saveClause({ verdict: "적합" }));
    $("aud-btn-save")?.addEventListener("click", () => {
      const v = c.verdict && c.verdict !== "적합" ? c.verdict : "적합";
      const grade =
        c.ncr_grade ||
        (v.indexOf("중대") >= 0
          ? "major"
          : v.indexOf("경미") >= 0
            ? "minor"
            : v.indexOf("관찰") >= 0
              ? "observation"
              : null);
      saveClause({ verdict: v, ncr_grade: grade, ncr_fact: c.ncr_fact || "" });
    });
    $("aud-btn-add-note")?.addEventListener("click", addExtraProcessNote);
  }

  function addExtraProcessNote() {
    if (state.noteMethod !== "process") {
      toast("추가 심사노트는 프로세스심사에서만 사용할 수 있습니다.");
      return;
    }
    const c = currentClause();
    if (!c || !state.session) return;
    const clauses = state.session.clauses || [];
    const same = clauses.filter((x) => x.clause_no === c.clause_no);
    let maxSeq = 1;
    same.forEach((x) => {
      const s = x.note_seq || 1;
      if (s > maxSeq) maxSeq = s;
    });
    const next = maxSeq + 1;
    const clone = {
      id: -(Date.now()),
      standard_key: c.standard_key,
      standard_code: c.standard_code || null,
      family_code: c.family_code || null,
      clause_no: c.clause_no,
      clause_topic: c.clause_topic || c.clause_title || "",
      clause_title: c.clause_topic || c.clause_title || "",
      question: c.question || "",
      default_kpis: (c.default_kpis || []).slice(),
      iso_audit_kpis: (c.iso_audit_kpis || []).slice(),
      esg_kpis: (c.esg_kpis || []).slice(),
      checkpoints: (c.checkpoints || []).slice(),
      process_group_id: c.process_group_id || null,
      process_group_name: c.process_group_name || c.group_name || null,
      group_name: c.process_group_name || c.group_name || null,
      hls_code: c.hls_code || null,
      source: c.source || null,
      sort_order: c.sort_order || 0,
      note_seq: next,
      clause_row_id: null,
      is_extra: true,
      plan_dept: c.plan_dept || null,
      plan_process: c.plan_process || null,
      verdict: null,
      note_text: "",
      kpi_values: {},
      ncr_grade: null,
      ncr_fact: null,
      ncr_requirement: null,
      ncr_root_cause: null,
      ncr_audit_date: null,
      ncr_auditor_name: null,
      ncr_dept: null,
      ncr_request_date: null,
      ncr_due_date: null,
      ncr_esg_tags: [],
      saved_at: null,
    };
    let insertAt = clauses.length;
    for (let i = clauses.length - 1; i >= 0; i--) {
      if (clauses[i].clause_no === c.clause_no) {
        insertAt = i + 1;
        break;
      }
    }
    clauses.splice(insertAt, 0, clone);
    state.session.clauses = clauses;
    state.clauseNo = c.clause_no;
    state.noteSeq = next;
    state.view = "clause";
    renderNav();
    renderMain();
    toast("추가 심사노트를 만들었습니다. 작성 후 저장하세요.");
  }

  function collectKpis() {
    const out = [];
    document.querySelectorAll("#aud-note-main [data-kpi-id], #aud-note-main [data-kpi-key]").forEach((el) => {
      const kid = el.getAttribute("data-kpi-id") || el.getAttribute("data-kpi-key");
      out.push({ kpi_id: kid, key: kid, value: el.value || "" });
    });
    return out;
  }

  async function saveClause(opts) {
    const c = currentClause();
    if (!c) return;

    const noteSeq = c.note_seq || state.noteSeq || 1;

    // Preview / no assignment: soft-save locally + toast (no DB write)
    if (state.preview || !state.contractId) {
      const noteText = ($("aud-note-text") && $("aud-note-text").value) || "";
      c.note_text = noteText;
      c.verdict = opts.verdict || "적합";
      c.ncr_grade = opts.ncr_grade || null;
      c.ncr_fact = opts.ncr_fact || null;
      c.ncr_requirement = opts.ncr_requirement || null;
      c.ncr_root_cause = opts.ncr_root_cause || null;
      c.ncr_audit_date = opts.ncr_audit_date || null;
      c.ncr_auditor_name = opts.ncr_auditor_name || null;
      c.ncr_dept = opts.ncr_dept || null;
      c.ncr_request_date = opts.ncr_request_date || null;
      c.ncr_due_date = opts.ncr_due_date || null;
      c.ncr_esg_tags = opts.ncr_esg_tags || [];
      c.kpi_values = {};
      collectKpis().forEach((k) => {
        c.kpi_values[k.kpi_id || k.key] = k.value || "";
      });
      c.saved_at = c.saved_at || new Date().toISOString();
      clearDirtyClause(c.clause_no, noteSeq);
      renderNav();
      toast("미리보기(배정 없음)");
      return;
    }

    const msg = $("aud-save-msg");
    if (msg) msg.textContent = "저장 중…";
    const noteText = ($("aud-note-text") && $("aud-note-text").value) || "";
    const body = {
      contract_id: Number(state.contractId),
      standard_key: state.standardKey,
      standard_code: c.standard_code || state.session?.process_standard_code || null,
      clause_no: c.clause_no,
      clause_topic: c.clause_topic || c.clause_title || "",
      clause_title: c.clause_topic || c.clause_title || "",
      process_group_id: c.process_group_id || null,
      hls_code: c.hls_code || null,
      note_seq: noteSeq,
      clause_row_id: c.clause_row_id || null,
      note_text: noteText,
      verdict: opts.verdict || "적합",
      ncr_grade: opts.ncr_grade || null,
      ncr_fact: opts.ncr_fact || null,
      ncr_requirement: opts.ncr_requirement || null,
      ncr_root_cause: opts.ncr_root_cause || null,
      ncr_audit_date: opts.ncr_audit_date || null,
      ncr_auditor_name: opts.ncr_auditor_name || null,
      ncr_dept: opts.ncr_dept || null,
      ncr_request_date: opts.ncr_request_date || null,
      ncr_due_date: opts.ncr_due_date || null,
      ncr_esg_tags: opts.ncr_esg_tags || [],
      kpi_values: collectKpis(),
      audit_method: state.noteMethod || "process",
    };
    try {
      const res = await fetch(API + "/auditor/audit-notes/clause", {
        method: "PUT",
        headers: authHeaders(true),
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "저장 실패");
      c.note_text = noteText;
      c.verdict = body.verdict;
      c.ncr_grade = body.ncr_grade;
      c.ncr_fact = body.ncr_fact;
      c.ncr_auditor_name = body.ncr_auditor_name;
      c.ncr_dept = body.ncr_dept;
      c.note_seq = noteSeq;
      if (data.clause_row_id) c.clause_row_id = data.clause_row_id;
      c.saved_at = new Date().toISOString();
      c.kpi_values = {};
      (body.kpi_values || []).forEach((k) => {
        c.kpi_values[k.kpi_id || k.key] = k.value || "";
      });
      clearDirtyClause(c.clause_no, noteSeq);
      renderNav();
      renderMain();
      const msg2 = $("aud-save-msg");
      if (msg2) msg2.textContent = data.message || "저장되었습니다.";
    } catch (e) {
      if (msg) msg.textContent = e.message || "저장 실패";
    }
  }


  function ymd(d) {
    const x = d instanceof Date ? d : new Date(d);
    const m = String(x.getMonth() + 1).padStart(2, "0");
    const day = String(x.getDate()).padStart(2, "0");
    return x.getFullYear() + "-" + m + "-" + day;
  }

  function addDays(d, n) {
    const x = new Date(d.getTime());
    x.setDate(x.getDate() + n);
    return x;
  }

  function standardDisplay(sk) {
    const items = (state.session && state.session.standards) || [];
    const hit = items.find((s) => s.standard_key === sk);
    if (hit) return hit.display_code || hit.standard_key;
    return sk || "";
  }

  // HLS → ESG auto tags (audit_v15 mapping; screenshot 4.1 = G-리스크관리, G-전략수립)
  const ESG_BY_CLAUSE = {
    "4.1": ["G-리스크관리", "G-전략수립"],
    "4.2": ["G-이해관계자", "G-투명성"],
    "4.3": ["G-거버넌스", "E-환경경영"],
    "4.4": ["G-리더십", "G-ESG거버넌스"],
    "5.1": ["G-거버넌스", "G-투명성"],
    "5.2": ["G-거버넌스구조", "G-책임체계"],
    "5.3": ["G-거버넌스", "G-책임체계"],
    "6.1": ["G-리스크관리", "E-기후리스크"],
    "6.2": ["G-전략수립", "G-리스크관리"],
    "6.3": ["G-변경관리"],
    "7.1": ["G-자원관리", "S-근로환경"],
    "7.2": ["S-역량개발", "S-교육투자"],
    "7.3": ["S-직원인식", "G-조직문화"],
    "7.4": ["G-투명성", "G-ESG공시"],
    "7.5": ["G-데이터무결성"],
    "8.1": ["G-운용관리"],
    "9.1": ["G-내부감사", "G-성과관리"],
    "9.2": ["G-내부감사", "G-거버넌스"],
    "9.3": ["G-거버넌스", "G-ESG경영검토"],
    "10.1": ["G-지속개선", "G-ESG성과"],
    "10.2": ["G-리스크관리", "G-지속개선"],
    "10.3": ["G-지속개선"],
  };

  function esgTagsForClause(c) {
    if (c && Array.isArray(c.ncr_esg_tags) && c.ncr_esg_tags.length) {
      return c.ncr_esg_tags.slice();
    }
    const no = String((c && c.clause_no) || "").trim();
    const hls = String((c && (c.hls_code || c.clause_no)) || "").trim();
    const keys = [no, hls, no.split("/")[0], hls.split("/")[0]];
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      if (k && ESG_BY_CLAUSE[k]) return ESG_BY_CLAUSE[k].slice();
    }
    // prefix fallback e.g. 4.1.1 → 4.1
    const prefix = (no || hls).match(/^(\d+\.\d+)/);
    if (prefix && ESG_BY_CLAUSE[prefix[1]]) return ESG_BY_CLAUSE[prefix[1]].slice();
    const head = (no || hls).charAt(0);
    if (head === "4") return ["G-리스크관리", "G-전략수립"];
    if (head === "5") return ["G-리더십", "G-ESG거버넌스"];
    if (head === "6") return ["G-리스크관리", "G-전략수립"];
    if (head === "7") return ["G-자원관리"];
    if (head === "8") return ["G-운용관리"];
    if (head === "9" || head === "1") return ["G-성과평가", "G-개선"];
    return [];
  }

  function setNcGradeUI(grade) {
    state.ncGrade = grade || "minor";
    const title = $("nc-title");
    const saveBtn = $("nc-save");
    const findingLabel = $("nc-finding-label");
    const causeWrap = $("nc-cause-wrap");
    const reqDateWrap = $("nc-req-date-wrap");
    const dueLabel = $("nc-due-label");
    const causeLabel = $("nc-cause-label");
    const cause = $("nc-cause");

    [["nc-g-major", "major", "grade-major"], ["nc-g-minor", "minor", "grade-minor"], ["nc-g-obs", "observation", "grade-obs"]].forEach(
      ([id, g, cls]) => {
        const el = $(id);
        if (!el) return;
        el.className = "grade-btn" + (state.ncGrade === g ? " " + cls : "");
      }
    );

    if (title) {
      title.classList.remove("is-major", "is-obs");
      if (state.ncGrade === "major") {
        title.textContent = "부적합 보고서 (Major — 중부적합)";
        title.classList.add("is-major");
      } else if (state.ncGrade === "observation") {
        title.textContent = "관찰사항 보고서";
        title.classList.add("is-obs");
      } else {
        title.textContent = "부적합 보고서 (Minor — 경부적합)";
      }
    }
    if (saveBtn) {
      saveBtn.classList.remove("is-major", "is-obs");
      saveBtn.textContent = "저장";
      if (state.ncGrade === "major") saveBtn.classList.add("is-major");
      else if (state.ncGrade === "observation") saveBtn.classList.add("is-obs");
    }
    if (findingLabel) {
      findingLabel.textContent =
        state.ncGrade === "observation"
          ? "관찰사항 내용 (객관적 증거 기반)"
          : "부적합 사항 (객관적 증거 기반)";
    }
    if (causeWrap) causeWrap.style.display = state.ncGrade === "observation" ? "none" : "";
    if (reqDateWrap) reqDateWrap.style.display = state.ncGrade === "observation" ? "none" : "";
    if (dueLabel) {
      dueLabel.textContent = state.ncGrade === "observation" ? "권고 기한 (선택)" : "시정조치 기한";
    }
    if (causeLabel) causeLabel.textContent = "근본 원인 분석";
    if (cause && state.ncGrade !== "observation") {
      cause.placeholder = "5Why, 특성요인도 등 적용";
    }
  }

  function openNcModal(preferredGrade) {
    const c = currentClause();
    if (!c) return;
    state.pendingNc = c;
    const grade = preferredGrade || c.ncr_grade || "minor";
    setNcGradeUI(grade);

    const sub = $("nc-sub");
    if (sub) {
      const title = clauseTopic(c);
      sub.textContent = title
        ? "§" + c.clause_no + " — " + c.clause_no + " " + title
        : "§" + c.clause_no;
    }

    const stdRow = $("nc-std-row");
    if (stdRow) {
      const disp = standardDisplay(state.standardKey);
      stdRow.innerHTML =
        '<span class="nc-std-badge">' +
        esc(disp) +
        '</span><span>§' +
        esc(c.clause_no) +
        "</span>";
    }

    const today = new Date();
    const due = addDays(today, 30);
    const setVal = (id, v) => {
      const el = $(id);
      if (el) el.value = v == null ? "" : v;
    };
    // Autofill: 심사원 = session auditor; 부서/공정 = 계획서 plan_dept/process
    const defaultAuditor =
      c.ncr_auditor_name ||
      state.auditorName ||
      (state.session && state.session.auditor_name) ||
      "";
    const defaultDept =
      c.ncr_dept ||
      c.plan_dept ||
      c.plan_process ||
      processGroupName(c) ||
      "";
    setVal("nc-date", c.ncr_audit_date || ymd(today));
    setVal("nc-auditor", defaultAuditor);
    setVal("nc-dept", defaultDept);
    setVal(
      "nc-finding",
      c.ncr_fact || (($("aud-note-text") && $("aud-note-text").value) || "")
    );
    setVal("nc-req", c.ncr_requirement || c.question || "");
    setVal("nc-cause", c.ncr_root_cause || "");
    setVal("nc-req-date", c.ncr_request_date || ymd(today));
    setVal("nc-due", c.ncr_due_date || ymd(due));

    const tags = esgTagsForClause(c);
    const esg = $("nc-esg");
    const wrap = $("nc-esg-wrap");
    if (esg) {
      if (tags.length) {
        esg.innerHTML = tags.map((x) => '<span class="esg-tag">' + esc(x) + "</span>").join("");
        if (wrap) wrap.style.display = "";
      } else {
        esg.innerHTML = '<span class="esg-empty">연계 지표 없음</span>';
        if (wrap) wrap.style.display = "";
      }
    }

    const err = $("nc-error");
    if (err) err.textContent = "";
    const modal = $("ncModal");
    if (modal) {
      modal.classList.add("show");
      modal.setAttribute("aria-hidden", "false");
    }
  }

  function closeNcModal() {
    const modal = $("ncModal");
    if (modal) {
      modal.classList.remove("show");
      modal.setAttribute("aria-hidden", "true");
    }
    state.pendingNc = null;
  }

  async function confirmNcModal() {
    const grade = state.ncGrade || "minor";
    const fact = (($("nc-finding") && $("nc-finding").value) || "").trim();
    const err = $("nc-error");
    if (!fact) {
      if (err) {
        err.textContent =
          grade === "observation"
            ? "관찰사항 내용을 입력하세요."
            : "부적합 사항(객관적 증거)을 입력하세요.";
      }
      return;
    }
    const verdictMap = {
      major: "중대한부적합",
      minor: "경미한부적합",
      observation: "관찰사항",
    };
    const noteEl = $("aud-note-text");
    if (noteEl && !noteEl.value.trim()) noteEl.value = fact;
    const c = currentClause() || state.pendingNc;
    const tags = esgTagsForClause(c);
    await saveClause({
      verdict: verdictMap[grade] || "경미한부적합",
      ncr_grade: grade,
      ncr_fact: fact,
      ncr_requirement: (($("nc-req") && $("nc-req").value) || "").trim(),
      ncr_root_cause:
        grade === "observation"
          ? ""
          : (($("nc-cause") && $("nc-cause").value) || "").trim(),
      ncr_audit_date: (($("nc-date") && $("nc-date").value) || "").trim(),
      ncr_auditor_name: (($("nc-auditor") && $("nc-auditor").value) || "").trim(),
      ncr_dept: (($("nc-dept") && $("nc-dept").value) || "").trim(),
      ncr_request_date:
        grade === "observation"
          ? ""
          : (($("nc-req-date") && $("nc-req-date").value) || "").trim(),
      ncr_due_date: (($("nc-due") && $("nc-due").value) || "").trim(),
      ncr_esg_tags: tags,
    });
    if (c) {
      c.ncr_requirement = (($("nc-req") && $("nc-req").value) || "").trim();
      c.ncr_root_cause = (($("nc-cause") && $("nc-cause").value) || "").trim();
      c.ncr_audit_date = (($("nc-date") && $("nc-date").value) || "").trim();
      c.ncr_auditor_name = (($("nc-auditor") && $("nc-auditor").value) || "").trim();
      c.ncr_dept = (($("nc-dept") && $("nc-dept").value) || "").trim();
      c.ncr_request_date = (($("nc-req-date") && $("nc-req-date").value) || "").trim();
      c.ncr_due_date = (($("nc-due") && $("nc-due").value) || "").trim();
      c.ncr_esg_tags = tags;
    }
    closeNcModal();
  }

  function applySessionMeta(data) {
    state.session = data;
    state.noteId = data.note_id || null;
    state.standardKey = data.standard_key || DEFAULT_STANDARD;
    state.preview = !!data.preview || !data.contract_id;
    state.contractId = data.contract_id || null;
    state.noteMethod = data.note_method === "clause" ? "clause" : "process";
    state.auditMode = data.audit_mode || null;
    state.auditorName = data.auditor_name || state.auditorName || "";
    state.isLead = !!data.is_lead;
    state.teamMeeting = !!data.team_meeting;
    clearDirty();
    hydrateInterviewData(data);

    if (!state.clauseNo && data.clauses && data.clauses.length) {
      const sorted = sortedClauses(data.clauses);
      const first =
        sorted.find((c) => isMainHlsClause(c.clause_no)) ||
        sorted.find((c) => !isChapterClause(c.clause_no)) ||
        sorted[0];
      state.clauseNo = first.clause_no;
      state.noteSeq = first.note_seq || 1;
    } else if (
      state.clauseNo &&
      !(data.clauses || []).some(
        (c) =>
          c.clause_no === state.clauseNo && (c.note_seq || 1) === (state.noteSeq || 1)
      )
    ) {
      const sorted = sortedClauses(data.clauses || []);
      const hit =
        sorted.find((c) => c.clause_no === state.clauseNo) ||
        sorted.find((c) => isMainHlsClause(c.clause_no)) ||
        sorted.find((c) => !isChapterClause(c.clause_no)) ||
        sorted[0] ||
        null;
      state.clauseNo = hit ? hit.clause_no : null;
      state.noteSeq = hit ? hit.note_seq || 1 : 1;
    }

    const companyName = state.preview
      ? dash(data.company_name)
      : dash(data.company_name || (data.contract_id ? "계약 #" + data.contract_id : null));
    const stdLabel = standardsLabel(data);
    const cbLabel = dash(data.cb_name);
    const dateLabel = formatAuditDate(data);
    const typeLabel = dash(
      data.audit_stage_label || data.audit_type_label || data.audit_type
    );

    const setHdr = (id, val) => {
      const el = $(id);
      if (el) el.textContent = val;
    };
    setHdr("aud-hdr-company", companyName);
    setHdr("aud-hdr-standards", stdLabel);
    setHdr("aud-hdr-cb", cbLabel);
    setHdr("aud-hdr-date", dateLabel);
    setHdr("aud-hdr-type", typeLabel);

    const company = $("aud-note-company");
    const sub = $("aud-note-sub");
    if (company) company.textContent = companyName;
    const methodLabel = state.noteMethod === "clause" ? "조항심사" : "프로세스심사";
    const modeLabel = data.audit_mode_label || "";
    if (sub) {
      const src =
        data.clause_source === "standard_clause_masters"
          ? "표준조항마스터"
          : data.clause_source === "process_group"
            ? "프로세스그룹"
            : data.clause_source === "iso_clauses"
              ? "iso_clauses"
              : "";
      const bits = [];
      if (state.preview) {
        bits.push("미리보기 · DB 미저장");
      } else {
        bits.push("노트 #" + (data.note_id || "—"));
        bits.push(data.status || "draft");
      }
      if (modeLabel) bits.push(modeLabel);
      bits.push(methodLabel);
      if (state.teamMeeting) bits.push("심사팀회의");
      else if (data.scope_mode === "assigned") bits.push("계획서 배정");
      if (src) bits.push(src);
      sub.textContent = bits.join(" · ");
    }

    const navCo = $("aud-note-nav-company");
    const navMeta = $("aud-note-nav-meta");
    if (navCo) navCo.textContent = companyName;
    if (navMeta) {
      let src = state.noteMethod === "clause" ? "조항심사" : "프로세스심사";
      if (state.teamMeeting) src = "팀 전체 배정 · " + src;
      else if (!state.preview && data.scope_mode === "assigned")
        src = "내 배정 · " + src;
      else if (!state.preview && (data.plan_empty || data.scope_mode === "no_plan"))
        src = "계획서 없음 · " + src;
      const pg = data.process_standard_code ? data.process_standard_code : "";
      const n = data.plan_item_count != null ? " · 계획 " + data.plan_item_count + "건" : "";
      navMeta.textContent = (pg ? src + " · " + pg : src) + (state.preview ? "" : n);
    }

    const badge = $("aud-note-preview-badge");
    if (badge) badge.style.display = state.preview ? "inline-flex" : "none";
    const rptBtn = $("aud-open-result-report");
    if (rptBtn) {
      rptBtn.style.display = state.preview || !state.contractId ? "none" : "";
    }
    syncAuditModeBadge();

    const filterHint = $("aud-std-filter-hint");
    if (filterHint) {
      const fm = data.standards_filter || "";
      if (state.preview || fm === "preview") filterHint.textContent = "(미리보기·전체)";
      else if (fm === "intersection") filterHint.textContent = "(계약∩보유/신청)";
      else if (fm === "contract") filterHint.textContent = "(계약/신청표준)";
      else if (fm === "company") filterHint.textContent = "(보유/신청표준)";
      else if (fm === "none") filterHint.textContent = "(표준 없음)";
      else filterHint.textContent = "";
    }

    const sel = $("aud-note-standard");
    if (sel) {
      const items = data.standards || [];
      if (items.length) {
        sel.innerHTML = items
          .map(
            (s) =>
              `<option value="${esc(s.standard_key)}" ${
                s.standard_key === data.standard_key ? "selected" : ""
              }>${esc(s.standard_code || s.family_code || s.standard_key)} · ${esc(s.display_code)} (${s.clause_count || 0})</option>`
          )
          .join("");
      } else {
        sel.innerHTML = `<option value="${esc(state.standardKey)}">${esc(state.standardKey)}</option>`;
      }
    }
    syncMethodTabs();
    syncViewButtons();
    buildIvNavPanel();
  }

  async function loadSession(contractId, standardKey, forcePreview, opts) {
    const preview = forcePreview || !contractId;
    state.preview = preview;
    state.contractId = preview ? null : contractId;
    showEditor(true);
    const nav = $("aud-note-nav");
    const main = $("aud-note-main");
    if (nav) nav.innerHTML = '<div class="aud-empty">불러오는 중…</div>';
    if (main) main.innerHTML = '<div class="aud-empty">불러오는 중…</div>';

    // Only send note_method when explicitly switching — otherwise keep DB value
    const forceMethod = opts && opts.forceMethod;
    const methodQ = forceMethod
      ? "&note_method=" + encodeURIComponent(state.noteMethod || "process")
      : "";
    const teamQ = state.teamMeeting ? "&team_meeting=1" : "";
    let q;
    if (preview) {
      q =
        "?preview=1" +
        (standardKey
          ? "&standard_key=" + encodeURIComponent(standardKey)
          : "&standard_key=" + encodeURIComponent(DEFAULT_STANDARD)) +
        // preview has no DB — always send current UI method
        "&note_method=" +
        encodeURIComponent(state.noteMethod || "process");
    } else {
      q =
        "?contract_id=" +
        encodeURIComponent(contractId) +
        (standardKey ? "&standard_key=" + encodeURIComponent(standardKey) : "") +
        methodQ +
        teamQ;
    }

    const res = await fetch(API + "/auditor/audit-notes/session" + q, {
      headers: authHeaders(),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "심사노트 세션 조회 실패");
    applySessionMeta(data);
    showEditor(true);
    renderNav();
    renderActiveView();
  }

  async function openAuditNoteEditor(contractId, standardKey) {
    try {
      const cid = contractId && String(contractId).trim() ? String(contractId).trim() : null;
      await loadSession(cid, standardKey || null, !cid);
      const url = new URL(location.href);
      url.searchParams.set("tab", "reports");
      if (cid) {
        url.searchParams.set("contract", cid);
        url.searchParams.delete("preview");
      } else {
        url.searchParams.delete("contract");
        url.searchParams.set("preview", "1");
      }
      if (standardKey || state.standardKey) {
        url.searchParams.set("standard", standardKey || state.standardKey);
      }
      history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
    } catch (e) {
      // Last resort: still show shell so UI is reviewable
      state.preview = true;
      state.contractId = null;
      state.session = {
        preview: true,
        company_name: null,
        cb_name: null,
        standards_label: "ISO 9001:2015",
        audit_date: null,
        audit_type: null,
        audit_stage_label: null,
        standard_key: standardKey || DEFAULT_STANDARD,
        standards: [
          {
            standard_key: DEFAULT_STANDARD,
            family_code: "QMS",
            display_code: "ISO 9001:2015",
            clause_count: 0,
          },
        ],
        clauses: [],
        status: "preview",
      };
      state.standardKey = standardKey || DEFAULT_STANDARD;
      applySessionMeta(state.session);
      showEditor(true);
      renderNav();
      renderActiveView();
      toast(e.message || "미리보기(배정 없음)");
    }
  }

  function openPreview(standardKey) {
    return openAuditNoteEditor(null, standardKey || DEFAULT_STANDARD);
  }

  function closeEditor() {
    showEditor(false);
    state.contractId = null;
    state.preview = false;
    state.session = null;
    state.clauseNo = null;
    state.noteSeq = 1;
    const url = new URL(location.href);
    url.searchParams.set("tab", "reports");
    url.searchParams.delete("contract");
    url.searchParams.delete("standard");
    url.searchParams.delete("preview");
    history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
    if (window.AuditorPortal && typeof window.AuditorPortal.reloadReports === "function") {
      window.AuditorPortal.reloadReports();
    }
  }

  async function runFormalize() {
    const c = currentClause();
    const input = $("aud-ai-input");
    const output = $("aud-ai-output");
    const msg = $("aud-ai-msg");
    const rough = ((input && input.value) || "").trim();
    if (!rough) {
      if (msg) msg.textContent = "정형화할 원문을 입력하세요.";
      return;
    }
    if (msg) msg.textContent = "정형화 중…";
    if (output) output.value = "";
    try {
      const res = await fetch(API + "/auditor/audit-notes/formalize", {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({
          standard_key: state.standardKey,
          clause_no: c ? c.clause_no : null,
          clause_topic: c ? c.clause_topic || c.clause_title : null,
          clause_title: c ? c.clause_topic || c.clause_title : null,
          question: c ? c.question : null,
          rough_text: rough,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "정형화 실패");
      if (output) output.value = data.formalized_text || "";
      if (msg) msg.textContent = data.message || (data.configured ? "완료" : "AI 미설정");
    } catch (e) {
      if (msg) msg.textContent = e.message || "정형화 실패";
    }
  }

  function applyFormalize() {
    const output = $("aud-ai-output");
    const note = $("aud-note-text");
    if (!output || !note) return;
    const text = (output.value || "").trim();
    if (!text) return;
    note.value = text;
    const msg = $("aud-ai-msg");
    if (msg) {
      msg.textContent = state.preview
        ? "노트에 반영했습니다. (미리보기 — DB 미저장)"
        : "노트에 반영했습니다. [저장] 또는 [적합]을 눌러 주세요.";
    }
  }

  // events
  document.addEventListener("click", (evt) => {
    const modeBtn = evt.target.closest(".aud-mode-tab[data-method]");
    if (modeBtn) {
      evt.preventDefault();
      setNoteMethod(modeBtn.getAttribute("data-method"));
      return;
    }
    const navToggle = evt.target.closest("#aud-note-nav [data-nav-toggle]");
    if (navToggle) {
      evt.preventDefault();
      toggleNavExpanded(navToggle.getAttribute("data-nav-toggle"));
      renderNav();
      return;
    }
    const navBtn = evt.target.closest("#aud-note-nav [data-clause]");
    if (navBtn) {
      state.clauseNo = navBtn.getAttribute("data-clause");
      const seqRaw = navBtn.getAttribute("data-note-seq");
      state.noteSeq = seqRaw ? Number(seqRaw) || 1 : 1;
      state.view = "clause";
      renderNav();
      renderActiveView();
      const c = currentClause();
      const aiIn = $("aud-ai-input");
      if (aiIn && c && c.note_text && !aiIn.value) aiIn.value = c.note_text;
      return;
    }
    const mxRow = evt.target.closest(".aud-matrix-table tr[data-clause]");
    if (mxRow) {
      const sk = mxRow.getAttribute("data-standard");
      const cno = mxRow.getAttribute("data-clause");
      if (sk && sk !== state.standardKey && state.contractId && !state.preview) {
        state.clauseNo = cno;
        clearDirty();
        loadSession(state.contractId, sk, false).then(() => {
          state.view = "clause";
          renderNav();
          renderActiveView();
        });
        return;
      }
      state.clauseNo = cno;
      state.view = "clause";
      renderNav();
      renderActiveView();
      return;
    }
    const ivPerson = evt.target.closest("[data-iv-person]");
    if (ivPerson) {
      const tpls = interviewTemplates();
      const cur = tpls[state.ivPersonIdx];
      if (cur && state.view === "interview") collectIvFromForm(cur.role_key);
      const idx = Number(ivPerson.getAttribute("data-iv-person") || 0);
      state.ivPersonIdx = Number.isFinite(idx) ? idx : 0;
      state.view = "interview";
      renderActiveView();
      return;
    }
    const ivOpen = evt.target.closest("[data-iv-open]");
    if (ivOpen) {
      state.view = "interview";
      renderActiveView();
      return;
    }
    const previewBtn = evt.target.closest("[data-open-preview-note]");
    if (previewBtn) {
      evt.preventDefault();
      openPreview(previewBtn.getAttribute("data-standard") || DEFAULT_STANDARD);
    }
  });

  $("aud-note-back")?.addEventListener("click", closeEditor);
  $("aud-note-standard")?.addEventListener("change", (e) => {
    state.clauseNo = null;
    state.view = "clause";
    clearDirty();
    if (state.preview || !state.contractId) {
      openPreview(e.target.value);
    } else {
      openAuditNoteEditor(state.contractId, e.target.value);
    }
  });
  $("aud-iv-toggle-btn")?.addEventListener("click", () => {
    state.view = state.view === "interview" ? "clause" : "interview";
    renderActiveView();
  });
  $("aud-matrix-toggle-btn")?.addEventListener("click", () => {
    state.view = state.view === "matrix" ? "clause" : "matrix";
    renderActiveView();
  });
  $("aud-open-result-report")?.addEventListener("click", () => {
    if (!state.contractId || state.preview) return;
    if (window.AuditorPortal && typeof window.AuditorPortal.openResultReport === "function") {
      window.AuditorPortal.openResultReport(state.contractId);
    } else {
      location.href =
        "/auditor-portal?tab=reports&view=report&contract=" +
        encodeURIComponent(state.contractId);
    }
  });
  $("aud-team-meeting-btn")?.addEventListener("click", () => {
    setTeamMeeting(!state.teamMeeting);
  });
  $("aud-iv-nav-hd")?.addEventListener("click", () => {
    const body = $("aud-iv-nav-body");
    const arrow = $("aud-iv-nav-arrow");
    if (!body) return;
    const open = body.style.display !== "none";
    body.style.display = open ? "none" : "block";
    if (arrow) arrow.textContent = open ? "▶" : "▼";
  });
  $("aud-ai-run")?.addEventListener("click", runFormalize);
  $("aud-ai-apply")?.addEventListener("click", applyFormalize);
  $("nc-cancel")?.addEventListener("click", closeNcModal);
  $("nc-close")?.addEventListener("click", closeNcModal);
  $("nc-save")?.addEventListener("click", confirmNcModal);
  ["nc-g-major", "nc-g-minor", "nc-g-obs"].forEach((id) => {
    $(id)?.addEventListener("click", () => {
      const g = $(id).getAttribute("data-grade");
      setNcGradeUI(g);
    });
  });
  $("ncModal")?.addEventListener("click", (e) => {
    if (e.target.id === "ncModal") closeNcModal();
  });

  window.AuditorAuditNotes = {
    open: openAuditNoteEditor,
    openPreview: openPreview,
    close: closeEditor,
    setMethod: setNoteMethod,
    setTeamMeeting: setTeamMeeting,
  };

  // Deep link: ?tab=reports[&contract=123|&preview=1|&view=report]
  // view=report is handled by AuditorPortal; notes open only when not report view
  document.addEventListener("DOMContentLoaded", () => {
    const url = new URL(location.href);
    const tab = url.searchParams.get("tab") || "";
    if (tab !== "reports") return;
    if (url.searchParams.get("view") === "report") return;
    const contract = url.searchParams.get("contract");
    const standard = url.searchParams.get("standard");
    const wantPreview = url.searchParams.get("preview") === "1" || !contract;
    setTimeout(() => {
      if (contract && !wantPreview) {
        openAuditNoteEditor(contract, standard);
      } else {
        openPreview(standard || DEFAULT_STANDARD);
      }
    }, 200);
  });
})();
