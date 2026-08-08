/* Auditor portal — dashboard + panels + CB membership apply */
(function () {
  const API = "/api/v1";
  const TAB_META = {
    dashboard: { title: "대시보드", sub: "배정 일정 · 보고서 · NCR · 소속 현황" },
    schedules: { title: "심사 일정 관리", sub: "월간 캘린더 · 배정 · 불가일정" },
    reports: { title: "심사 보고서 · 심사노트", sub: "조항별 심사노트 · 작성 중인 보고서" },
    docs: { title: "인증심사 문서", sub: "최초·사후·갱신·전환·특별 문서세트 · Master DB 데모" },
    ncrs: { title: "시정조치(NCR) 검토", sub: "기업 제출 시정조치 검토" },
    mypage: { title: "마이페이지", sub: "기본 정보 · 자격 · 소속 · 학력/경력" },
    profile: { title: "자격 및 소속 관리", sub: "자격 이력 · 멀티 CB 소속 · 신규 신청" },
  };

  const calState = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    events: [],
    selectedDate: null,
  };

  function token() {
    return localStorage.getItem("access_token");
  }

  function role() {
    return localStorage.getItem("role") || "";
  }

  function authHeaders(json) {
    const h = { Authorization: "Bearer " + (token() || "") };
    if (json) h["Content-Type"] = "application/json";
    return h;
  }

  function redirectLogin(msg) {
    if (msg) {
      try { alert(msg); } catch (_) { /* ignore */ }
    }
    location.replace("/login?next=/auditor-portal");
  }

  if (!token() || (role() && role() !== "auditor" && role() !== "platform_admin")) {
    redirectLogin(
      role() && role() !== "auditor" && role() !== "platform_admin"
        ? "심사원 포털 접근 권한이 없습니다."
        : "로그인이 필요합니다."
    );
    return;
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtDate(d) {
    if (!d) return "—";
    return String(d).slice(0, 10);
  }

  function setError(msg) {
    const el = document.getElementById("global-error");
    if (el) el.textContent = msg || "";
  }

  /* ── tab switching ── */
  function switchTab(name, opts) {
    const tab = TAB_META[name] ? name : "dashboard";
    document.querySelectorAll(".tab-panel").forEach((el) => {
      el.classList.toggle("active", el.id === "tab-" + tab);
    });
    document.querySelectorAll(".sidebar-menu-item[data-tab]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-tab") === tab);
    });
    /* leave 심사노트 viewport lock when navigating away from reports */
    if (tab !== "reports") {
      document.body.classList.remove("aud-note-open");
    } else {
      const ed = document.getElementById("audit-note-editor");
      const open =
        ed &&
        ed.style.display !== "none" &&
        ed.getAttribute("aria-hidden") !== "true";
      document.body.classList.toggle("aud-note-open", !!open);
    }
    const meta = TAB_META[tab];
    const title = document.getElementById("page-title");
    const sub = document.getElementById("page-subtitle");
    if (title) title.textContent = meta.title;
    if (sub) sub.textContent = meta.sub;
    const url = new URL(location.href);
    url.searchParams.set("tab", tab);
    history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
    if (opts && opts.focus) {
      const target = document.getElementById(
        opts.focus === "quals" ? "profile-quals"
          : opts.focus === "cb-apply" ? "profile-cb-apply"
          : opts.focus
      );
      if (target) setTimeout(() => target.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
    if (tab === "schedules") loadSchedulesPanel();
    if (tab === "docs") loadDocsPanel();
    if (tab === "reports") {
      loadReportsPanel();
      const contract = url.searchParams.get("contract");
      const standard = url.searchParams.get("standard");
      const view = url.searchParams.get("view") || "";
      const rptPanel = document.getElementById("audit-result-report");
      const reportVisible =
        rptPanel &&
        rptPanel.style.display !== "none" &&
        rptPanel.getAttribute("aria-hidden") !== "true";
      if (view === "report" && contract) {
        openResultReport(contract);
      } else if (!reportVisible) {
        // Surface 심사노트 3-pane shell (preview if no contract)
        const ed = document.getElementById("audit-note-editor");
        const editorVisible =
          ed && ed.style.display !== "none" && ed.getAttribute("aria-hidden") !== "true";
        if (!editorVisible && window.AuditorAuditNotes) {
          if (contract) window.AuditorAuditNotes.open(contract, standard);
          else window.AuditorAuditNotes.openPreview(standard);
        }
      }
    }
    if (tab === "ncrs") loadNcrsPanel();
    if (tab === "mypage") loadMypagePanel();
    if (tab === "profile") loadProfilePanel();
  }

  function dash(v) {
    return v == null || v === "" ? "—" : String(v);
  }

  function isUnavailability(item) {
    return (item && item.item_type) === "unavailability";
  }

  function scheduleCoversDate(item, iso) {
    const start = item.audit_date ? String(item.audit_date).slice(0, 10) : null;
    const end = item.audit_period_end
      ? String(item.audit_period_end).slice(0, 10)
      : start;
    if (!start) return false;
    return start <= iso && iso <= (end || start);
  }

  function eventChipLabel(ev) {
    if (isUnavailability(ev)) {
      const note = (ev.note || "").trim();
      return note ? "불가 · " + note : "불가일정";
    }
    return ev.company_name || "일정";
  }

  function renderCalendar() {
    const box = document.getElementById("aud-calendar");
    const title = document.getElementById("aud-cal-title");
    if (!box) return;
    if (title) title.textContent = calState.year + "년 " + calState.month + "월";

    const first = new Date(calState.year, calState.month - 1, 1);
    const startPad = first.getDay();
    const daysInMonth = new Date(calState.year, calState.month, 0).getDate();
    const today = new Date();
    const todayIso =
      today.getFullYear() +
      "-" +
      String(today.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(today.getDate()).padStart(2, "0");

    const byDate = {};
    const monthStart =
      calState.year +
      "-" +
      String(calState.month).padStart(2, "0") +
      "-01";
    const monthEnd =
      calState.year +
      "-" +
      String(calState.month).padStart(2, "0") +
      "-" +
      String(daysInMonth).padStart(2, "0");
    (calState.events || []).forEach((ev) => {
      const start = ev.audit_date ? String(ev.audit_date).slice(0, 10) : null;
      if (!start) return;
      const end = ev.audit_period_end
        ? String(ev.audit_period_end).slice(0, 10)
        : start;
      let cur = start < monthStart ? monthStart : start;
      const last = end > monthEnd ? monthEnd : end;
      while (cur <= last) {
        if (!byDate[cur]) byDate[cur] = [];
        byDate[cur].push(ev);
        const d = new Date(cur + "T12:00:00");
        d.setDate(d.getDate() + 1);
        cur =
          d.getFullYear() +
          "-" +
          String(d.getMonth() + 1).padStart(2, "0") +
          "-" +
          String(d.getDate()).padStart(2, "0");
      }
    });

    const weekLabels = ["일", "월", "화", "수", "목", "금", "토"];
    const heads = weekLabels
      .map((h, i) => {
        const wk =
          i === 0 ? " is-sun" : i === 6 ? " is-sat" : "";
        return '<div class="cal-head' + wk + '">' + h + "</div>";
      })
      .join("");
    let cells = "";
    for (let i = 0; i < startPad; i++) {
      cells += '<div class="cal-cell is-empty" aria-hidden="true"></div>';
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const iso =
        calState.year +
        "-" +
        String(calState.month).padStart(2, "0") +
        "-" +
        String(d).padStart(2, "0");
      const dow = (startPad + d - 1) % 7;
      const list = byDate[iso] || [];
      const names = list
        .slice(0, 3)
        .map((ev) => {
          const cls =
            "cal-event" + (isUnavailability(ev) ? " is-unavailability" : "");
          return '<span class="' + cls + '">' + esc(eventChipLabel(ev)) + "</span>";
        })
        .join("");
      const more =
        list.length > 3
          ? '<span class="cal-more">+' + (list.length - 3) + "</span>"
          : "";
      const cls = [
        "cal-cell",
        list.length ? "has-events" : "",
        iso === todayIso ? "is-today" : "",
        iso === calState.selectedDate ? "is-selected" : "",
        dow === 0 ? "is-sun" : "",
        dow === 6 ? "is-sat" : "",
      ]
        .filter(Boolean)
        .join(" ");
      cells +=
        '<button type="button" class="' +
        cls +
        '" data-cal-date="' +
        iso +
        '" aria-label="' +
        iso +
        (list.length ? ", 일정 " + list.length + "건" : "") +
        '"><span class="cal-day">' +
        d +
        '</span><span class="cal-events">' +
        names +
        more +
        "</span></button>";
    }
    box.innerHTML = '<div class="cal-grid">' + heads + cells + "</div>";
  }

  function renderDayDetail(iso) {
    const title = document.getElementById("aud-day-detail-title");
    const list = document.getElementById("aud-day-detail-list");
    if (!list) return;
    calState.selectedDate = iso || null;
    if (!iso) {
      if (title) title.textContent = "날짜를 선택하세요";
      list.innerHTML =
        '<div class="aud-empty">캘린더에서 날짜를 클릭하면 상세가 표시됩니다.</div>';
      return;
    }
    if (title) title.textContent = iso + " 일정";
    const dayItems = (calState.events || []).filter((ev) =>
      scheduleCoversDate(ev, iso)
    );
    if (!dayItems.length) {
      list.innerHTML =
        '<div class="aud-empty">이 날짜에 등록된 일정이 없습니다.</div>';
      return;
    }
    list.innerHTML = dayItems
      .map((r) => {
        const period =
          fmtDate(r.audit_date) +
          (r.audit_period_end && r.audit_period_end !== r.audit_date
            ? " ~ " + fmtDate(r.audit_period_end)
            : "");
        if (isUnavailability(r)) {
          const uid = r.unavailability_id || "";
          return `<article class="aud-detail-card is-unavailability">
          <h4>불가일정</h4>
          <dl class="aud-dl">
            <dt>기간</dt><dd>${esc(period)}</dd>
            <dt>사유</dt><dd>${esc(dash(r.note))}</dd>
            <dt>구분</dt><dd>불가일정</dd>
          </dl>
          <div style="margin-top:10px;">
            <button type="button" class="btn ghost" data-del-unavail="${esc(uid)}">삭제</button>
          </div>
        </article>`;
        }
        return `<article class="aud-detail-card">
          <h4>${esc(r.company_name || (r.company_id ? "#" + r.company_id : "기업"))}</h4>
          <dl class="aud-dl">
            <dt>기업명</dt><dd>${esc(dash(r.company_name))}</dd>
            <dt>심사표준</dt><dd>${esc(dash(r.standards_label))}</dd>
            <dt>심사유형</dt><dd>${esc(dash(r.audit_type_label || r.audit_type))}</dd>
            <dt>심사방식</dt><dd>${esc(dash(r.audit_mode_label || r.audit_mode))}</dd>
            <dt>심사기간</dt><dd>${esc(period)}</dd>
            <dt>심사팀</dt><dd>${esc(dash(r.team_label))}</dd>
            <dt>기업주소</dt><dd>${esc(dash(r.company_address))}</dd>
            <dt>담당자</dt><dd>${esc(dash(r.contact_name))}</dd>
            <dt>담당자연락처</dt><dd>${esc(dash(r.contact_phone))}</dd>
            <dt>진행 상태</dt><dd>${esc(dash(r.status_label || r.status))}</dd>
          </dl>
          <div style="margin-top:10px;">
            <button type="button" class="btn ghost" data-goto="reports" data-contract="${esc(r.contract_id || "")}">심사노트/보고서 작성</button>
          </div>
        </article>`;
      })
      .join("");
  }

  function setUnavailFormOpen(open) {
    const form = document.getElementById("aud-unavail-form");
    const err = document.getElementById("aud-unavail-err");
    if (!form) return;
    form.hidden = !open;
    if (err) err.textContent = "";
    if (open) {
      const start = document.getElementById("aud-unavail-start");
      const end = document.getElementById("aud-unavail-end");
      const note = document.getElementById("aud-unavail-note");
      const preset = calState.selectedDate || "";
      if (start && !start.value) start.value = preset;
      if (end && !end.value) end.value = preset || (start && start.value) || "";
      if (note) note.value = note.value || "";
      if (start) start.focus();
    }
  }

  async function submitUnavailability() {
    const err = document.getElementById("aud-unavail-err");
    const startEl = document.getElementById("aud-unavail-start");
    const endEl = document.getElementById("aud-unavail-end");
    const noteEl = document.getElementById("aud-unavail-note");
    const start = startEl && startEl.value;
    const end = endEl && endEl.value;
    const note = ((noteEl && noteEl.value) || "").trim();
    if (err) err.textContent = "";
    if (!start || !end) {
      if (err) err.textContent = "시작일과 종료일을 입력해 주세요.";
      return;
    }
    if (end < start) {
      if (err) err.textContent = "종료일은 시작일 이후여야 합니다.";
      return;
    }
    try {
      const res = await fetch(API + "/auditor/unavailability", {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({
          start_date: start,
          end_date: end,
          note: note || null,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401) return redirectLogin("세션이 만료되었습니다.");
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          typeof detail === "string" ? detail : "불가일정 등록 실패 (" + res.status + ")"
        );
      }
      if (startEl) startEl.value = "";
      if (endEl) endEl.value = "";
      if (noteEl) noteEl.value = "";
      setUnavailFormOpen(false);
      await loadSchedulesPanel();
    } catch (e) {
      if (err) err.textContent = e.message || "불가일정 등록 실패";
    }
  }

  async function deleteUnavailability(rowId) {
    if (!rowId) return;
    if (!confirm("이 불가일정을 삭제할까요?")) return;
    try {
      const res = await fetch(API + "/auditor/unavailability/" + encodeURIComponent(rowId), {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (res.status === 401) return redirectLogin("세션이 만료되었습니다.");
      if (!res.ok && res.status !== 204) {
        const data = await res.json().catch(() => ({}));
        const detail = data.detail;
        throw new Error(
          typeof detail === "string" ? detail : "삭제 실패 (" + res.status + ")"
        );
      }
      await loadSchedulesPanel();
    } catch (e) {
      alert(e.message || "삭제 실패");
    }
  }

  /* ── rendering helpers ── */
  function scheduleRows(list, emptyMsg) {
    if (!list || !list.length) {
      return `<tr><td colspan="6" class="aud-empty">${esc(emptyMsg || "배정된 일정이 없습니다.")}</td></tr>`;
    }
    return list.map((r) => {
      const cid = r.contract_id || "";
      return `<tr>
        <td>${esc(r.company_name || (r.company_id ? "#" + r.company_id : "—"))}</td>
        <td>${esc(r.standards_label || "—")}</td>
        <td>${esc(r.audit_type_label || r.audit_type || "—")}</td>
        <td>${esc(fmtDate(r.audit_date))}${r.audit_period_end && r.audit_period_end !== r.audit_date ? " ~ " + esc(fmtDate(r.audit_period_end)) : ""}</td>
        <td>${esc(r.status_label || r.status || "—")}</td>
        <td><button type="button" class="btn ghost" data-goto="reports" data-contract="${esc(cid)}">심사노트/보고서 작성</button></td>
      </tr>`;
    }).join("");
  }

  function ncrListHtml(list, emptyMsg) {
    if (!list || !list.length) {
      return `<div class="aud-empty">${esc(emptyMsg || "검토 대기 NCR이 없습니다.")}</div>`;
    }
    return list.map((n) => {
      return `<div class="aud-list-item">
        <a href="#" data-goto="ncrs" data-ncr="${n.id}">${esc(n.company_name || "기업")} · ${esc(n.std_label || n.std_code || "")} ${esc(n.clause_id || "")}</a>
        <small>${esc(n.status_label || n.status || "")}${n.due_date ? " · 기한 " + esc(fmtDate(n.due_date)) : ""}${n.finding ? " — " + esc(n.finding) : ""}</small>
      </div>`;
    }).join("");
  }

  function reportListHtml(list) {
    const previewBtn =
      `<div style="margin-top:12px;">
        <button type="button" class="btn" data-open-preview-note>심사노트 미리보기 열기</button>
        <p class="muted" style="margin:8px 0 0;font-size:0.85rem;">배정/계약이 없어도 조항 UI를 확인할 수 있습니다. (미리보기 · DB 미저장)</p>
      </div>`;
    if (!list || !list.length) {
      return `<div class="aud-empty">작성 중인 보고서가 없습니다. 배정이 없어도 미리보기로 심사노트 UI를 열 수 있습니다.</div>${previewBtn}`;
    }
    return (
      list
        .map((r) => {
          const cid = r.contract_id || "";
          return `<div class="aud-list-item">
        <strong>${esc(r.company_name || ("계약 #" + (r.contract_id || r.id)))}</strong>
        <small>${esc(r.report_type || "report")} · ${esc(r.status_label || r.status || "")}${r.report_no ? " · " + esc(r.report_no) : ""}${r.updated_at ? " · 갱신 " + esc(String(r.updated_at).slice(0, 16).replace("T", " ")) : ""}</small>
        <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;">
          ${
            cid
              ? `<button type="button" class="btn ghost" data-open-note="${esc(cid)}">심사노트 열기</button>
                 <button type="button" class="btn" data-open-report="${esc(cid)}">결과보고서</button>
                 <a class="btn ghost" href="/auditor-portal?tab=reports&contract=${encodeURIComponent(cid)}" title="딥링크">노트 딥링크</a>`
              : `<button type="button" class="btn ghost" data-open-preview-note>심사노트 열기 (미리보기)</button>`
          }
        </div>
      </div>`;
        })
        .join("") + previewBtn
    );
  }

  /* ── 심사결과보고서 (② 조항 / ③ NCR / ⑤ 매트릭스) — live from notes ── */
  let reportState = { contractId: null, data: null, tab: "clauses" };

  function showReportPanel(show) {
    const list = document.getElementById("reports-list-wrap");
    const panel = document.getElementById("audit-result-report");
    const noteEd = document.getElementById("audit-note-editor");
    if (list) list.style.display = show ? "none" : "";
    if (panel) {
      panel.style.display = show ? "" : "none";
      panel.setAttribute("aria-hidden", show ? "false" : "true");
    }
    if (show && noteEd) {
      noteEd.style.display = "none";
      noteEd.setAttribute("aria-hidden", "true");
    }
  }

  function renderReportBody() {
    const box = document.getElementById("aud-report-body");
    const data = reportState.data;
    if (!box || !data) return;
    const tab = reportState.tab || "clauses";
    document.querySelectorAll(".aud-rpt-tab").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-rpt-tab") === tab);
    });

    if (tab === "ncrs") {
      const cards = (data.ncrs || [])
        .map((n) => {
          const g = String(n.grade || "").toLowerCase();
          let label = "관찰사항 (Observation)";
          let border = "#1a5fa8";
          if (g.includes("major") || g.includes("중대") || g === "중부적합") {
            label = "중부적합 (Major Nonconformity)";
            border = "#b71c1c";
          } else if (g.includes("minor") || g.includes("경미") || g === "경부적합") {
            label = "경부적합 (Minor Nonconformity)";
            border = "#8a5c00";
          }
          return `<article style="border:1px solid #e3ebe4;border-left:4px solid ${border};border-radius:8px;padding:12px 14px;margin-bottom:10px;">
            <div style="font-size:0.8rem;font-weight:700;margin-bottom:6px;">${esc(label)} · §${esc(n.clause || "—")} ${esc(n.standard || "")}</div>
            <div style="font-weight:700;margin-bottom:4px;">${esc(n.title || "")}</div>
            <div style="font-size:0.9rem;line-height:1.5;">${esc(n.description || "")}</div>
            ${n.requirement ? `<div class="muted" style="margin-top:6px;font-size:0.82rem;">요구사항: ${esc(n.requirement)}</div>` : ""}
            ${n.due_date ? `<div class="muted" style="margin-top:4px;font-size:0.82rem;">시정 기한: ${esc(n.due_date)}</div>` : ""}
          </article>`;
        })
        .join("");
      box.innerHTML = `
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">
          <span class="aud-matrix-stat warn">중부적합 ${data.ncr_major || 0}</span>
          <span class="aud-matrix-stat">경부적합 ${data.ncr_minor || 0}</span>
          <span class="aud-matrix-stat">관찰사항 ${data.ncr_obs || 0}</span>
        </div>
        ${cards || '<div class="aud-empty">부적합 사항 없음 (심사노트 NCR 기준)</div>'}`;
      return;
    }

    if (tab === "matrix") {
      const rows = (data.matrix_cells || [])
        .map((c) => {
          const badge = c.missing
            ? '<span class="aud-matrix-badge miss">빠짐</span>'
            : '<span class="aud-matrix-badge done">작성</span>';
          return `<tr class="${c.missing ? "missing" : "written"}">
            <td>${esc(c.standard_code || c.standard_key || "")}</td>
            <td>${esc(c.clause_no)}</td>
            <td>${esc(c.clause_topic || "")}</td>
            <td>${esc(c.verdict || "—")}</td>
            <td>${badge}</td>
          </tr>`;
        })
        .join("");
      box.innerHTML = `<div class="aud-matrix-box">
        <div class="aud-matrix-hd">
          <div>
            <strong>심사 매트릭스</strong>
            <div class="muted" style="font-size:0.82rem;">ISO/IEC 17021-1 §9.1.3 · 계약 표준 × standard_clause_masters · 심사노트 작성 여부</div>
          </div>
          <div class="aud-matrix-stats">
            <span class="aud-matrix-stat">필수 ${data.matrix_required || 0}</span>
            <span class="aud-matrix-stat ok">작성 ${data.matrix_written || 0}</span>
            <span class="aud-matrix-stat warn">빠짐 ${data.matrix_missing || 0}</span>
            <span class="aud-matrix-stat">커버리지 ${data.matrix_coverage_pct || 0}%</span>
          </div>
        </div>
        <table class="aud-matrix-table">
          <thead><tr><th>표준</th><th>조항</th><th>조항명</th><th>판정</th><th>상태</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="5" class="muted">매트릭스 데이터 없음</td></tr>'}</tbody>
        </table>
      </div>`;
      return;
    }

    // clauses (② 조항별 심사 결과)
    const rows = (data.clauses || [])
      .map((c) => {
        return `<tr>
          <td style="font-weight:700;text-align:center;">${esc(c.clause_no)}<br><span class="muted" style="font-size:0.75rem;">${esc(c.standard_code || c.standard || "")}</span></td>
          <td>${esc(c.clause_label || "")}</td>
          <td>${esc(c.verdict || "—")}</td>
          <td style="font-size:0.85rem;">${esc((c.note || "").slice(0, 160))}</td>
        </tr>`;
      })
      .join("");
    box.innerHTML = `
      <p class="muted" style="margin:0 0 10px;font-size:0.85rem;">심사노트(audit_note_clauses)에서 실시간 수집 · 조항명/판정/심사 요약</p>
      <table class="aud-matrix-table">
        <thead><tr><th style="width:90px">조항</th><th>조항명</th><th style="width:100px">판정</th><th>심사 요약</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="4" class="muted">심사노트 조항 데이터 없음 — 노트를 먼저 저장하세요</td></tr>'}</tbody>
      </table>`;
  }

  async function openResultReport(contractId) {
    const cid = String(contractId || "").trim();
    if (!cid) return;
    showReportPanel(true);
    reportState.contractId = cid;
    reportState.tab = "clauses";
    const body = document.getElementById("aud-report-body");
    if (body) body.innerHTML = '<div class="aud-empty">불러오는 중…</div>';
    const title = document.getElementById("aud-report-title");
    const sub = document.getElementById("aud-report-sub");
    const planA = document.getElementById("aud-report-open-plan");
    if (planA) {
      // Deep-link to plan UI (PHP) when available; JSON plan API as fallback
      planA.href = "/audit-docs/plan?demo=1&contract_id=" + encodeURIComponent(cid);
      planA.onclick = null;
    }
    try {
      const res = await fetch(API + "/auditor/audit-reports/" + encodeURIComponent(cid), {
        headers: authHeaders(),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "결과보고서 조회 실패");
      reportState.data = data;
      if (title) title.textContent = "심사결과보고서 · " + (data.company_name || ("계약 #" + cid));
      if (sub) {
        sub.textContent =
          (data.standards_label || "") +
          (data.team_label ? " · " + data.team_label : "") +
          (data.plan_id ? " · 계획서 #" + data.plan_id : " · 계획서 없음");
      }
      renderReportBody();
      const url = new URL(location.href);
      url.searchParams.set("tab", "reports");
      url.searchParams.set("contract", cid);
      url.searchParams.set("view", "report");
      history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
    } catch (e) {
      if (body) body.innerHTML = `<div class="aud-empty">${esc(e.message || "조회 실패")}</div>`;
    }
  }

  function closeResultReport() {
    showReportPanel(false);
    reportState = { contractId: null, data: null, tab: "clauses" };
    const url = new URL(location.href);
    url.searchParams.set("tab", "reports");
    url.searchParams.delete("view");
    history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
  }

  function statusClass(st) {
    if (st === "approved") return "status-ok";
    if (st === "rejected" || st === "terminated" || st === "expired") return "status-no";
    return "status-wait";
  }

  /* ── data loaders ── */
  let dashCache = null;

  function docsQuery() {
    const urlParams = new URLSearchParams(location.search);
    const cid = urlParams.get("contract_id") || urlParams.get("contract") || "1";
    return {
      cid: String(cid),
      q: "demo=1&contract_id=" + encodeURIComponent(cid),
    };
  }

  function closeDocsViewer() {
    const list = document.getElementById("docs-list-wrap");
    const viewer = document.getElementById("audit-doc-viewer");
    const frame = document.getElementById("aud-doc-frame");
    if (list) list.style.display = "";
    if (viewer) {
      viewer.style.display = "none";
      viewer.setAttribute("aria-hidden", "true");
    }
    if (frame) frame.src = "about:blank";
    const url = new URL(location.href);
    url.searchParams.set("tab", "docs");
    url.searchParams.delete("doc");
    history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
  }

  function openDocsViewer(slug, title, path) {
    const { cid, q } = docsQuery();
    const list = document.getElementById("docs-list-wrap");
    const viewer = document.getElementById("audit-doc-viewer");
    const frame = document.getElementById("aud-doc-frame");
    const titleEl = document.getElementById("aud-doc-title");
    const subEl = document.getElementById("aud-doc-sub");
    const ext = document.getElementById("aud-doc-external");
    const notes = document.getElementById("aud-doc-open-notes");
    const report = document.getElementById("aud-doc-open-report");
    const plan = document.getElementById("aud-doc-open-plan");
    const src = (path || "/audit-docs/" + slug) + "?" + q;
    if (list) list.style.display = "none";
    if (viewer) {
      viewer.style.display = "";
      viewer.setAttribute("aria-hidden", "false");
    }
    if (titleEl) titleEl.textContent = title || slug;
    if (subEl) subEl.textContent = "contract #" + cid + " · Master DB";
    if (frame) frame.src = src;
    if (ext) ext.href = src;
    if (notes) notes.href = "/auditor-portal?tab=reports&" + q;
    if (report) report.href = "/auditor-portal?tab=reports&view=report&" + q;
    if (plan) {
      plan.href = "#";
      plan.onclick = (e) => {
        e.preventDefault();
        openDocsViewer("plan", "심사계획서", "/audit-docs/plan");
      };
    }
    const url = new URL(location.href);
    url.searchParams.set("tab", "docs");
    url.searchParams.set("doc", slug);
    url.searchParams.set("demo", "1");
    url.searchParams.set("contract_id", cid);
    history.replaceState(null, "", url.pathname + "?" + url.searchParams.toString());
  }

  async function loadDocsPanel() {
    const box = document.getElementById("docs-hub-list");
    if (!box) return;
    const { cid, q } = docsQuery();
    const urlParams = new URLSearchParams(location.search);
    const openDoc = urlParams.get("doc") || "";
    box.innerHTML = '<div class="aud-empty">불러오는 중…</div>';
    try {
      const res = await fetch(API + "/demo/audit-docs/context?" + q);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "문서 컨텍스트 조회 실패");
      const m = data.master || {};
      const groups = {};
      const order = [];
      const bySlug = {};
      (data.pages || []).forEach((p) => {
        bySlug[p.slug] = p;
        const g = p.group || "other";
        if (!groups[g]) {
          groups[g] = { label: p.group_label || g, pages: [] };
          order.push(g);
        }
        groups[g].pages.push(p);
      });
      let html =
        '<p class="muted" style="margin:0 0 12px;">company #' +
        esc(m.company_id) +
        " " +
        esc(m.company_name) +
        " · contract #" +
        esc(m.contract_id) +
        " " +
        esc(m.contract_no) +
        " · " +
        esc((m.standard_keys || []).join(", ")) +
        (data.audit_plan_id ? " · audit_plan #" + esc(data.audit_plan_id) : "") +
        '</p><div class="aud-quick" style="margin-bottom:14px;">' +
        '<button type="button" class="btn ghost" data-goto="reports">심사노트</button>' +
        '<a class="btn ghost" href="/auditor-portal?tab=reports&view=report&' +
        q +
        '">결과보고서</a>' +
        '<a class="btn ghost" href="/auditor-portal?tab=schedules&demo=1">일정</a>' +
        '<a class="btn ghost" href="/demo/audit-docs?' +
        q +
        '">데모 허브</a></div>';
      order.forEach((g) => {
        html +=
          "<h4 style='margin:16px 0 8px;'>" +
          esc(groups[g].label) +
          "</h4><div class='aud-quick'>";
        groups[g].pages.forEach((p) => {
          html +=
            '<button type="button" class="btn ghost" data-open-doc="' +
            esc(p.slug) +
            '" data-doc-title="' +
            esc(p.title) +
            '" data-doc-path="' +
            esc(p.path) +
            '">' +
            esc(p.title) +
            "</button>";
        });
        html += "</div>";
      });
      // portal-native deep links (노트/보고서는 기존 reports 패널)
      html +=
        "<h4 style='margin:16px 0 8px;'>포털 연동</h4><div class='aud-quick'>" +
        '<button type="button" class="btn" data-goto="reports">심사노트 (reports)</button>' +
        '<a class="btn ghost" href="/auditor-portal?tab=reports&view=report&' +
        q +
        '">결과보고서</a></div>';
      box.innerHTML = html;
      box.querySelectorAll("[data-open-doc]").forEach((btn) => {
        btn.addEventListener("click", () => {
          openDocsViewer(
            btn.getAttribute("data-open-doc"),
            btn.getAttribute("data-doc-title"),
            btn.getAttribute("data-doc-path")
          );
        });
      });
      if (openDoc && bySlug[openDoc]) {
        openDocsViewer(openDoc, bySlug[openDoc].title, bySlug[openDoc].path);
      } else if (openDoc === "notes") {
        switchTab("reports");
      } else if (openDoc === "report") {
        switchTab("reports");
        openResultReport(cid);
      } else {
        closeDocsViewer();
      }
    } catch (e) {
      box.innerHTML =
        '<div class="aud-empty">' +
        esc(e.message || "문서 목록 로드 실패") +
        ' · <a href="/demo/audit-docs?demo=1&contract_id=1">데모 허브</a></div>';
    }
  }

  async function loadDashboard() {
    setError("");
    try {
      const res = await fetch(API + "/auditor/dashboard-summary", { headers: authHeaders() });
      if (res.status === 401) return redirectLogin("세션이 만료되었습니다.");
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "대시보드 조회 실패 (" + res.status + ")");
      dashCache = data;

      const nameEl = document.getElementById("sidebar-auditor-name");
      const metaEl = document.getElementById("sidebar-auditor-meta");
      if (nameEl) nameEl.textContent = data.auditor_name || localStorage.getItem("user_name") || "심사원";
      if (metaEl) metaEl.textContent = data.auditor_id ? "auditor #" + data.auditor_id : "";

      const k = data.kpis || {};
      document.getElementById("kpi-schedules").textContent = String(k.scheduled_this_month ?? 0);
      document.getElementById("kpi-drafts").textContent = String(k.draft_reports ?? 0);
      document.getElementById("kpi-ncrs").textContent = String(k.ncr_review_pending ?? 0);
      document.getElementById("kpi-affiliation").textContent = k.affiliation_status || "—";
      const sub = document.getElementById("kpi-affiliation-sub");
      if (sub) sub.textContent = k.affiliation_detail || "";

      document.getElementById("dash-schedule-tbody").innerHTML = scheduleRows(
        data.schedules,
        "배정·확정된 심사 일정이 없습니다."
      );
      document.getElementById("dash-ncr-list").innerHTML = ncrListHtml(
        data.ncrs_pending,
        "검토 대기 NCR이 없습니다."
      );
      if (data.warnings && data.warnings.length) {
        setError(data.warnings.join(" · "));
      }
    } catch (e) {
      setError(e.message || "대시보드 오류");
      document.getElementById("dash-schedule-tbody").innerHTML =
        `<tr><td colspan="6" class="aud-empty">조회 실패</td></tr>`;
      document.getElementById("dash-ncr-list").innerHTML =
        `<div class="aud-empty">조회 실패</div>`;
    }
  }

  async function loadSchedulesPanel() {
    const box = document.getElementById("aud-calendar");
    const detail = document.getElementById("aud-day-detail-list");
    try {
      const q =
        "?year=" +
        encodeURIComponent(calState.year) +
        "&month=" +
        encodeURIComponent(calState.month);
      const res = await fetch(API + "/auditor/schedules" + q, {
        headers: authHeaders(),
      });
      const data = await res.json().catch(() => []);
      if (!res.ok) throw new Error((data && data.detail) || "일정 조회 실패");
      calState.events = Array.isArray(data) ? data : [];
      if (!calState.selectedDate) {
        const today = new Date();
        if (
          today.getFullYear() === calState.year &&
          today.getMonth() + 1 === calState.month
        ) {
          calState.selectedDate =
            calState.year +
            "-" +
            String(calState.month).padStart(2, "0") +
            "-" +
            String(today.getDate()).padStart(2, "0");
        }
      }
      renderCalendar();
      renderDayDetail(calState.selectedDate);
    } catch (e) {
      calState.events = [];
      if (box) {
        box.innerHTML =
          '<div class="aud-empty">' + esc(e.message || "일정 조회 실패") + "</div>";
      }
      if (detail) {
        detail.innerHTML =
          '<div class="aud-empty">' + esc(e.message || "일정 조회 실패") + "</div>";
      }
    }
  }

  function mypageFieldRows(pairs) {
    return pairs
      .map(
        ([label, value]) =>
          `<div><dt>${esc(label)}</dt><dd>${esc(dash(value))}</dd></div>`
      )
      .join("");
  }

  async function loadMypagePanel() {
    const basic = document.getElementById("mypage-basic");
    const qualsBox = document.getElementById("mypage-quals");
    const memBox = document.getElementById("mypage-memberships");
    const eduBox = document.getElementById("mypage-educations");
    const careerBox = document.getElementById("mypage-careers");
    const extBox = document.getElementById("mypage-external");
    try {
      const res = await fetch(API + "/auditor/mypage", { headers: authHeaders() });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "마이페이지 조회 실패");

      const addr = [data.address, data.detail_address].filter(Boolean).join(" ");
      if (basic) {
        basic.innerHTML = mypageFieldRows([
          ["이름", data.name],
          ["영문명", data.name_en],
          ["이메일", data.email],
          ["연락처", data.phone],
          ["생년월일", data.birth_date],
          ["성별", data.gender],
          ["주소", addr || null],
          ["ComplAIs 번호", data.complais_no],
          ["등록번호", data.registration_no],
          ["등급", data.grade],
          ["고용형태", data.employment_type],
          ["프리랜서", data.is_freelance == null ? null : data.is_freelance ? "예" : "아니오"],
          ["상태", data.status],
          ["프로필 상태", data.profile_status],
          ["주 소속 CB", data.primary_cb_name || (data.primary_cb_id ? "#" + data.primary_cb_id : null)],
          ["소속 표기", data.cb_affiliation],
          ["IAF 코드", data.iaf_codes],
          ["학력", data.education_level],
          ["학교", data.school_name],
          ["전공", data.major],
          ["경력 요약", data.career_summary],
          ["본인인증(CI)", data.has_ci ? "등록됨" : "미등록"],
        ]);
      }

      const quals = data.qualifications || [];
      if (qualsBox) {
        qualsBox.innerHTML = !quals.length
          ? '<div class="aud-empty">등록된 자격 이력이 없습니다.</div>'
          : quals
              .map((q) => {
                const dday =
                  q.dday == null
                    ? ""
                    : q.dday < 0
                      ? `만료 D+${Math.abs(q.dday)}`
                      : `D-${q.dday}`;
                return `<div class="mem-item"><div>
                  <strong>${esc(q.standard_label || q.standard_code || "—")}</strong>
                  <small style="display:block;color:#64748b;margin-top:4px;">
                    ${esc(q.grade || "")}${q.cert_body_name ? " · " + esc(q.cert_body_name) : ""}${q.cert_no ? " · " + esc(q.cert_no) : ""}
                    ${q.iaf_codes ? " · IAF " + esc(q.iaf_codes) : ""}${q.major_name ? " · " + esc(q.major_name) : ""}
                    ${q.expires_at ? " · 만료 " + esc(fmtDate(q.expires_at)) : ""}${dday ? " · " + esc(dday) : ""}
                  </small></div>
                  <span class="${q.is_active ? "status-ok" : "status-wait"}">${q.is_active ? "활성" : "비활성"}</span>
                </div>`;
              })
              .join("");
      }

      const mems = data.memberships || [];
      if (memBox) {
        memBox.innerHTML = !mems.length
          ? '<div class="aud-empty">소속 CB가 없습니다.</div>'
          : mems
              .map((m) => {
                const dday =
                  m.qual_dday == null
                    ? ""
                    : m.qual_dday < 0
                      ? `만료 D+${Math.abs(m.qual_dday)}`
                      : `D-${m.qual_dday}`;
                return `<div class="mem-item"><div>
                  <strong>${esc(m.cb_name || ("CB #" + m.cb_id))}${m.is_primary ? " (주 소속)" : ""}</strong>
                  <small style="display:block;color:#64748b;margin-top:4px;">
                    ${esc(m.cb_code || "")}${m.employment_type ? " · " + esc(m.employment_type) : ""}
                    · 신청 ${esc(m.apply_grade || "—")} · 승인 ${esc(m.approved_grade || "—")}
                    ${m.cert_standards ? " · " + esc(m.cert_standards) : ""}
                    ${m.approved_iaf_codes ? " · IAF " + esc(m.approved_iaf_codes) : ""}
                    ${m.kar_no ? " · KAR " + esc(m.kar_no) : ""}
                    ${m.qualification_expires_at ? " · 자격만료 " + esc(fmtDate(m.qualification_expires_at)) : ""}
                    ${dday ? " · " + esc(dday) : ""}
                  </small></div>
                  <span class="${statusClass(m.status)}">${esc(m.status_label || m.status)}</span>
                </div>`;
              })
              .join("");
      }

      const edus = data.educations || [];
      if (eduBox) {
        eduBox.innerHTML = !edus.length
          ? '<div class="aud-empty">등록된 학력이 없습니다.</div>'
          : edus
              .map(
                (e) => `<div class="aud-list-item">
                  <strong>${esc(e.school_name || "—")}</strong>
                  <small>${esc(e.degree || "")}${e.major ? " · " + esc(e.major) : ""}
                  ${e.entered_at || e.graduated_at ? " · " + esc(fmtDate(e.entered_at)) + " ~ " + esc(fmtDate(e.graduated_at)) : ""}</small>
                </div>`
              )
              .join("");
      }

      const careers = data.careers || [];
      if (careerBox) {
        careerBox.innerHTML = !careers.length
          ? '<div class="aud-empty">등록된 경력이 없습니다.</div>'
          : careers
              .map(
                (c) => `<div class="aud-list-item">
                  <strong>${esc(c.company_name || "—")}</strong>
                  <small>${esc(c.position || "")}${c.department ? " · " + esc(c.department) : ""}
                  ${c.iaf_code ? " · IAF " + esc(c.iaf_code) : ""}${c.ksic_code ? " · KSIC " + esc(c.ksic_code) : ""}
                  · ${esc(fmtDate(c.start_date))} ~ ${c.is_current ? "재직중" : esc(fmtDate(c.end_date))}
                  ${c.duties ? " — " + esc(c.duties) : ""}</small>
                </div>`
              )
              .join("");
      }

      const exts = data.external_certs || [];
      if (extBox) {
        extBox.innerHTML = !exts.length
          ? '<div class="aud-empty">등록된 외부 자격이 없습니다.</div>'
          : exts
              .map(
                (x) => `<div class="aud-list-item">
                  <strong>${esc(x.cert_name || "—")}</strong>
                  <small>${esc(x.issuer || "")}${x.cert_no ? " · " + esc(x.cert_no) : ""}${x.grade ? " · " + esc(x.grade) : ""}
                  ${x.issued_date ? " · 발급 " + esc(fmtDate(x.issued_date)) : ""}${x.expiry_date ? " · 만료 " + esc(fmtDate(x.expiry_date)) : ""}</small>
                </div>`
              )
              .join("");
      }
    } catch (e) {
      const msg = '<div class="aud-empty">' + esc(e.message) + "</div>";
      if (basic) basic.innerHTML = msg;
      if (qualsBox) qualsBox.innerHTML = msg;
      if (memBox) memBox.innerHTML = "";
      if (eduBox) eduBox.innerHTML = "";
      if (careerBox) careerBox.innerHTML = "";
      if (extBox) extBox.innerHTML = "";
    }
  }

  async function loadReportsPanel() {
    const box = document.getElementById("reports-list");
    try {
      const res = await fetch(API + "/auditor/reports", { headers: authHeaders() });
      const data = await res.json().catch(() => []);
      if (!res.ok) throw new Error((data && data.detail) || "보고서 조회 실패");
      box.innerHTML = reportListHtml(data);
    } catch (e) {
      box.innerHTML = `<div class="aud-empty">${esc(e.message)}</div>`;
    }
  }

  async function loadNcrsPanel() {
    const box = document.getElementById("ncrs-list");
    try {
      const res = await fetch(API + "/auditor/ncrs", { headers: authHeaders() });
      const data = await res.json().catch(() => []);
      if (!res.ok) throw new Error((data && data.detail) || "NCR 조회 실패");
      box.innerHTML = ncrListHtml(data, "검토 대기 NCR이 없습니다.");
    } catch (e) {
      box.innerHTML = `<div class="aud-empty">${esc(e.message)}</div>`;
    }
  }

  async function loadProfilePanel() {
    const qualsBox = document.getElementById("quals-list");
    const memBox = document.getElementById("memberships-list");
    try {
      const res = await fetch(API + "/auditor/profile-summary", { headers: authHeaders() });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "프로필 조회 실패");

      const quals = data.qualifications || [];
      if (!quals.length) {
        qualsBox.innerHTML = `<div class="aud-empty">등록된 자격 이력이 없습니다.</div>`;
      } else {
        qualsBox.innerHTML = quals.map((q) => {
          const dday = q.dday == null ? "" : (q.dday < 0 ? `만료 D+${Math.abs(q.dday)}` : `D-${q.dday}`);
          return `<div class="mem-item">
            <div>
              <strong>${esc(q.standard_label || q.standard_code || "—")}</strong>
              <small style="display:block;color:#64748b;margin-top:4px;">
                ${esc(q.grade || "")}${q.cert_body_name ? " · " + esc(q.cert_body_name) : ""}${q.cert_no ? " · " + esc(q.cert_no) : ""}
                ${q.expires_at ? " · 만료 " + esc(fmtDate(q.expires_at)) : ""}${dday ? " · " + esc(dday) : ""}
              </small>
            </div>
            <span class="${q.is_active ? "status-ok" : "status-wait"}">${q.is_active ? "활성" : "비활성"}</span>
          </div>`;
        }).join("");
      }

      const mems = data.memberships || [];
      if (!mems.length) {
        memBox.innerHTML = `<div class="aud-empty">소속 CB가 없습니다. 아래에서 신청하세요.</div>`;
      } else {
        memBox.innerHTML = mems.map((m) => {
          const dday = m.qual_dday == null ? "" : (m.qual_dday < 0 ? `만료 D+${Math.abs(m.qual_dday)}` : `D-${m.qual_dday}`);
          return `<div class="mem-item">
            <div>
              <strong>${esc(m.cb_name || ("CB #" + m.cb_id))}${m.is_primary ? " (주 소속)" : ""}</strong>
              <small style="display:block;color:#64748b;margin-top:4px;">
                ${esc(m.cb_code || "")} · 신청 ${esc(m.apply_grade || "—")} · 승인 ${esc(m.approved_grade || "—")}
                ${m.cert_standards ? " · " + esc(m.cert_standards) : ""}
                ${m.qualification_expires_at ? " · 자격만료 " + esc(fmtDate(m.qualification_expires_at)) : ""}
                ${dday ? " · " + esc(dday) : ""}
              </small>
            </div>
            <span class="${statusClass(m.status)}">${esc(m.status_label || m.status)}</span>
          </div>`;
        }).join("");
      }
    } catch (e) {
      qualsBox.innerHTML = `<div class="aud-empty">${esc(e.message)}</div>`;
      memBox.innerHTML = "";
    }
  }

  async function loadSession() {
    const meta = document.getElementById("session-meta");
    try {
      const res = await fetch(API + "/auth/me", { headers: authHeaders() });
      if (res.status === 401) return redirectLogin("세션이 만료되었습니다.");
      const me = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error("세션 확인 실패");
      if (me.role && me.role !== "auditor" && me.role !== "platform_admin") {
        return redirectLogin("심사원 포털 접근 권한이 없습니다.");
      }
      if (meta) {
        meta.textContent = (me.name || localStorage.getItem("user_name") || "심사원") + " · " + (me.role || "auditor");
      }
      if (me.name) localStorage.setItem("user_name", me.name);
      if (me.role) localStorage.setItem("role", me.role);
    } catch (e) {
      if (meta) meta.textContent = e.message || "세션 오류";
    }
  }

  /* ── membership apply (profile) — multi-row edu/career/qual (v7) ── */
  const DEGREE_OPTS = [
    ["high_school", "고졸"],
    ["associate", "전문학사"],
    ["bachelor", "학사"],
    ["master", "석사"],
    ["doctor", "박사"],
    ["other", "기타"],
  ];
  const CERT_BODY_OPTS = ["", "KAR", "IRCA", "Exemplar Global", "Other"];

  const state = {
    cbId: null,
    cbName: "",
    careers: [], // {companyId, companyName, bizNo, ksicCode, isTemporary, start, end, duties, mappedIaf}
    companyIaf: [],
    majorIaf: [],
    allIaf: {},
  };

  function degreeSelectHtml(selected) {
    return DEGREE_OPTS.map(([v, label]) =>
      `<option value="${v}"${v === (selected || "bachelor") ? " selected" : ""}>${label}</option>`
    ).join("");
  }

  function certBodySelectHtml(selected) {
    return CERT_BODY_OPTS.map((v) =>
      `<option value="${esc(v)}"${v === (selected || "") ? " selected" : ""}>${v || "선택"}</option>`
    ).join("");
  }

  function applyModalEl() {
    return document.getElementById("applyModal");
  }

  function firstMajorFromDom() {
    const majors = [...(applyModalEl()?.querySelectorAll(".apply-edu-card .edu-major") || [])]
      .map((el) => (el.value || "").trim())
      .filter((m) => m.length >= 2);
    return majors[0] || "";
  }

  function firstCompanyIdFromState() {
    syncCareerFromDom();
    const hit = state.careers.find((c) => c.companyId);
    return hit ? hit.companyId : null;
  }

  function collectCompanyIafFromState() {
    syncCareerFromDom();
    const map = {};
    state.careers.forEach((c) => {
      (c.mappedIaf || []).forEach((r) => {
        if (r && r.iaf_code) map[r.iaf_code] = r;
      });
    });
    return Object.values(map);
  }

  async function loadIafDatalist() {
    try {
      const res = await fetch(API + "/meta/iaf-codes");
      const list = await res.json().catch(() => []);
      const dl = document.getElementById("iaf-datalist");
      if (dl) {
        dl.innerHTML = (list || []).map((r) =>
          `<option value="${esc(r.iaf_code)}">${esc(r.iaf_code)} — ${esc(r.industry_name_ko || "")}</option>`
        ).join("");
      }
    } catch (_) { /* ignore */ }
  }

  async function searchCb() {
    const keyword = (document.getElementById("cb-keyword").value || "").trim();
    const err = document.getElementById("search-error");
    const box = document.getElementById("cb-search-results");
    err.textContent = "";
    box.innerHTML = "";
    if (keyword.length < 2) {
      err.textContent = "검색어를 2자 이상 입력하세요.";
      return;
    }
    try {
      const res = await fetch(API + "/cb-entities?q=" + encodeURIComponent(keyword) + "&limit=20");
      const list = await res.json().catch(() => []);
      if (!res.ok) throw new Error(list.detail || "검색 실패 (" + res.status + ")");
      if (!list.length) {
        box.innerHTML = "<p class='aud-empty'>검색 결과가 없습니다.</p>";
        return;
      }
      box.innerHTML = list.map((cb) => `
        <div class="mem-item">
          <div>
            <strong>${esc(cb.name)}</strong>
            <small style="display:block;color:#64748b;margin-top:4px;">${esc(cb.code || "")} · ${esc(cb.address || "주소 없음")}</small>
          </div>
          <button type="button" class="btn" data-open-apply="${cb.id}" data-cb-name="${esc(cb.name)}">소속 신청</button>
        </div>`).join("");
    } catch (e) {
      err.textContent = e.message;
    }
  }

  async function searchMajorsInto(inputEl, box) {
    const q = inputEl.value.trim();
    if (q.length < 1) { box.style.display = "none"; box.innerHTML = ""; return; }
    try {
      const res = await fetch(API + "/meta/majors?q=" + encodeURIComponent(q));
      const list = await res.json().catch(() => []);
      if (!list.length) { box.style.display = "none"; return; }
      box.style.display = "block";
      box.innerHTML = list.map((m) =>
        `<button type="button" data-name="${esc(m.name)}">${esc(m.name)}</button>`
      ).join("");
      box.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          inputEl.value = btn.dataset.name;
          box.style.display = "none";
          scheduleMajorRecommend();
        });
      });
    } catch (_) {
      box.style.display = "none";
    }
  }

  function addEduRow(prefill) {
    const p = prefill || {};
    const list = document.getElementById("apply-edu-list");
    if (!list) return;
    const card = document.createElement("div");
    card.className = "repeat-card apply-edu-card";
    card.innerHTML = `
      <div class="card-head"><span>학력</span><button type="button" class="btn-remove">삭제</button></div>
      <div class="grid-2">
        <div class="form-row">
          <label>학위</label>
          <select class="edu-degree">${degreeSelectHtml(p.degree)}</select>
        </div>
        <div class="form-row">
          <label>학교명</label>
          <input class="edu-school" placeholder="예: ○○대학교" value="${esc(p.school_name || "")}" />
        </div>
      </div>
      <div class="form-row">
        <label>전공학과명</label>
        <input class="edu-major" placeholder="예: 화학공학" autocomplete="off" value="${esc(p.major || "")}" />
        <div class="suggest-box edu-major-suggest"></div>
      </div>
      <div class="grid-2">
        <div class="form-row">
          <label>입학</label>
          <input class="edu-entered" type="date" value="${esc((p.entered_at || "").toString().slice(0, 10))}" />
        </div>
        <div class="form-row">
          <label>졸업</label>
          <input class="edu-graduated" type="date" value="${esc((p.graduated_at || "").toString().slice(0, 10))}" />
        </div>
      </div>`;
    card.querySelector(".btn-remove").addEventListener("click", () => {
      if (list.querySelectorAll(".apply-edu-card").length <= 1) return;
      card.remove();
      scheduleMajorRecommend();
    });
    const majorInput = card.querySelector(".edu-major");
    const box = card.querySelector(".edu-major-suggest");
    let t = null;
    majorInput.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => searchMajorsInto(majorInput, box), 250);
      scheduleMajorRecommend();
    });
    list.appendChild(card);
  }

  function collectEducations() {
    return [...(applyModalEl()?.querySelectorAll(".apply-edu-card") || [])].map((card) => ({
      degree: card.querySelector(".edu-degree").value,
      school_name: card.querySelector(".edu-school").value.trim(),
      major: card.querySelector(".edu-major").value.trim() || null,
      entered_at: card.querySelector(".edu-entered").value || null,
      graduated_at: card.querySelector(".edu-graduated").value || null,
    })).filter((e) => e.school_name || e.major);
  }

  function renderCareers() {
    const list = document.getElementById("apply-career-list");
    if (!list) return;
    list.innerHTML = "";
    state.careers.forEach((c, idx) => {
      const card = document.createElement("div");
      card.className = "repeat-card apply-career-card";
      card.dataset.idx = String(idx);
      card.innerHTML = `
        <div class="card-head"><span>경력 ${idx + 1}</span>
          <button type="button" class="btn-remove">삭제</button></div>
        <div class="form-row">
          <label>경력 기업</label>
          <div class="addr-row">
            <input class="career-keyword" placeholder="기업명 또는 사업자번호 (2자 이상)" value="${esc(c.companyName || "")}" />
            <button type="button" class="btn-ghost btn-career-search">기업 검색</button>
          </div>
          <div class="suggest-box career-results" style="display:block;margin-top:8px;"></div>
          <div class="hint career-selected">${c.companyId ? `선택됨 #${c.companyId}` : (c.isTemporary ? "직접입력" : "")}</div>
        </div>
        <div class="grid-2">
          <div class="form-row">
            <label>기업명</label>
            <input class="career-name" value="${esc(c.companyName || "")}" />
          </div>
          <div class="form-row">
            <label>사업자번호</label>
            <input class="career-biz" value="${esc(c.bizNo || "")}" />
          </div>
        </div>
        <div class="grid-2">
          <div class="form-row">
            <label>근무 시작일</label>
            <input class="career-start" type="date" value="${esc(c.start || "")}" />
          </div>
          <div class="form-row">
            <label>근무 종료일</label>
            <input class="career-end" type="date" value="${esc(c.end || "")}" />
          </div>
        </div>
        <div class="form-row">
          <label>담당 업무</label>
          <input class="career-duties" placeholder="주요 담당 업무" value="${esc(c.duties || "")}" />
        </div>`;
      card.querySelector(".btn-remove").addEventListener("click", () => {
        syncCareerFromDom();
        if (state.careers.length <= 1) return;
        state.careers.splice(idx, 1);
        renderCareers();
        refreshCombinedScopes();
      });
      card.querySelector(".btn-career-search").addEventListener("click", () => searchCompanyForCard(card, idx));
      card.querySelector(".career-keyword").addEventListener("keyup", (e) => {
        if (e.key === "Enter") { e.preventDefault(); searchCompanyForCard(card, idx); }
      });
      ["career-name", "career-biz", "career-start", "career-end", "career-duties"].forEach((cls) => {
        card.querySelector("." + cls).addEventListener("change", () => syncCareerFromDom());
      });
      list.appendChild(card);
    });
  }

  function syncCareerFromDom() {
    const cards = [...(applyModalEl()?.querySelectorAll(".apply-career-card") || [])];
    cards.forEach((card, idx) => {
      if (!state.careers[idx]) state.careers[idx] = {};
      const c = state.careers[idx];
      c.companyName = card.querySelector(".career-name").value.trim();
      c.bizNo = card.querySelector(".career-biz").value.trim();
      c.start = card.querySelector(".career-start").value || "";
      c.end = card.querySelector(".career-end").value || "";
      c.duties = card.querySelector(".career-duties").value.trim();
    });
  }

  function addCareer(prefill) {
    syncCareerFromDom();
    state.careers.push(Object.assign({
      companyId: null, companyName: "", bizNo: "", ksicCode: "",
      isTemporary: false, start: "", end: "", duties: "", mappedIaf: [],
    }, prefill || {}));
    renderCareers();
  }

  function collectCareers() {
    syncCareerFromDom();
    return state.careers
      .filter((c) => (c.companyName || "").trim())
      .map((c) => ({
        company_id: c.companyId || null,
        company_name: c.companyName.trim(),
        biz_no: c.bizNo || null,
        ksic_code: c.ksicCode || null,
        is_temporary: !!c.isTemporary || !c.companyId,
        start_date: c.start || null,
        end_date: c.end || null,
        is_current: !c.end,
        duties: c.duties || null,
        note: c.duties || null,
      }));
  }

  async function searchCompanyForCard(card, idx) {
    const q = card.querySelector(".career-keyword").value.trim();
    const box = card.querySelector(".career-results");
    const err = document.getElementById("company-error");
    if (err) err.textContent = "";
    box.innerHTML = "";
    if (q.length < 2) {
      box.innerHTML = "<p class='hint'>검색어를 2자 이상 입력하세요.</p>";
      return;
    }
    try {
      const res = await fetch(API + "/companies/search?q=" + encodeURIComponent(q));
      const list = await res.json().catch(() => []);
      if (!res.ok) throw new Error(list.detail || "검색 실패");
      if (!list.length) {
        if (confirm("등록된 기업이 없습니다. 직접 입력하시겠습니까?")) {
          state.careers[idx].companyId = null;
          state.careers[idx].companyName = q;
          state.careers[idx].isTemporary = true;
          state.careers[idx].mappedIaf = [];
          card.querySelector(".career-name").value = q;
          card.querySelector(".career-selected").textContent = "직접입력 모드";
          syncCareerFromDom();
          refreshCombinedScopes();
        }
        return;
      }
      window._companyCache = window._companyCache || {};
      box.innerHTML = list.map((c) => {
        window._companyCache[c.id] = c;
        return `<button type="button" data-id="${c.id}"><strong>${esc(c.name)}</strong> · ${esc(c.biz_no || "-")}</button>`;
      }).join("");
      box.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          const c = window._companyCache[Number(btn.dataset.id)];
          if (!c) return;
          state.careers[idx].companyId = c.id;
          state.careers[idx].companyName = c.name;
          state.careers[idx].bizNo = c.biz_no || "";
          state.careers[idx].ksicCode = c.ksic_code || "";
          state.careers[idx].isTemporary = false;
          state.careers[idx].mappedIaf = c.mapped_iaf_codes || [];
          card.querySelector(".career-keyword").value = c.name;
          card.querySelector(".career-name").value = c.name;
          card.querySelector(".career-biz").value = c.biz_no || "";
          card.querySelector(".career-selected").textContent =
            `선택: ${c.name} (${c.biz_no || "-"}) · KSIC ${c.ksic_code || "-"}`;
          box.innerHTML = "";
          syncCareerFromDom();
          refreshCombinedScopes();
        });
      });
    } catch (e) {
      box.innerHTML = `<p class='hint'>${esc(e.message || "검색 실패")}</p>`;
    }
  }

  function syncQualRows() {
    const wrap = document.getElementById("apply-qual-rows");
    if (!wrap) return;
    const checked = [...document.querySelectorAll("input[name=apply-std]:checked")].map((el) => el.value);
    const existing = {};
    wrap.querySelectorAll(".qual-std-row").forEach((row) => {
      existing[row.dataset.std] = {
        cert_body: row.querySelector(".qual-body").value,
        cert_no: row.querySelector(".qual-no").value.trim(),
      };
    });
    wrap.innerHTML = "";
    checked.forEach((std) => {
      const prev = existing[std] || {};
      const row = document.createElement("div");
      row.className = "qual-std-row";
      row.dataset.std = std;
      row.innerHTML = `
        <div class="std-label">${esc(std)}</div>
        <div class="grid-2">
          <div class="form-row">
            <label>자격 발급기관</label>
            <select class="qual-body">${certBodySelectHtml(prev.cert_body)}</select>
          </div>
          <div class="form-row">
            <label>자격증 번호</label>
            <input class="qual-no" placeholder="자격증 번호" value="${esc(prev.cert_no || "")}" />
          </div>
        </div>`;
      wrap.appendChild(row);
    });
  }

  function collectQualifications(majorFallback, requestedIaf, grade) {
    const qualGrade = document.getElementById("qual-grade").value || grade;
    return [...(applyModalEl()?.querySelectorAll(".qual-std-row") || [])].map((row) => ({
      standard_code: row.dataset.std,
      cert_body_name: row.querySelector(".qual-body").value || null,
      cert_no: row.querySelector(".qual-no").value.trim() || null,
      auditor_grade: qualGrade,
      iaf_codes: requestedIaf,
      major_name: majorFallback || null,
    }));
  }

  function resetApplyRows() {
    const eduList = document.getElementById("apply-edu-list");
    if (eduList) eduList.innerHTML = "";
    state.careers = [];
    addEduRow();
    addCareer();
    document.querySelectorAll("input[name=apply-std]").forEach((el) => { el.checked = false; });
    syncQualRows();
  }

  function openApplyModal(cbId, cbName) {
    state.cbId = cbId;
    state.cbName = cbName;
    state.companyIaf = [];
    state.majorIaf = [];
    state.allIaf = {};
    document.getElementById("apply-cb-name").textContent = cbName;
    document.getElementById("apply-grade").value = "auditor";
    document.getElementById("company-error").textContent = "";
    document.getElementById("apply-error").textContent = "";
    document.getElementById("qual-grade").value = "auditor";
    resetApplyRows();
    document.getElementById("major-iaf-badges").innerHTML =
      '<span class="muted" style="font-size:0.85rem;">전공 입력 후 추천 IAF가 표시됩니다.</span>';
    document.getElementById("scope-checkboxes").innerHTML =
      '<span class="muted" style="font-size:0.85rem;">전공 또는 기업을 입력하면 Scope가 채워집니다.</span>';
    document.getElementById("applyModal").classList.add("show");
    document.getElementById("applyModal").setAttribute("aria-hidden", "false");
  }

  function closeApplyModal() {
    document.getElementById("applyModal").classList.remove("show");
    document.getElementById("applyModal").setAttribute("aria-hidden", "true");
  }

  let majorTimer = null;
  function scheduleMajorRecommend() {
    clearTimeout(majorTimer);
    majorTimer = setTimeout(refreshMajorRecommend, 400);
  }

  async function refreshMajorRecommend() {
    const major = firstMajorFromDom();
    const box = document.getElementById("major-iaf-badges");
    if (major.length < 2) {
      state.majorIaf = [];
      box.innerHTML = '<span class="muted" style="font-size:0.85rem;">전공 입력 후 추천 IAF가 표시됩니다.</span>';
      await refreshCombinedScopes();
      return;
    }
    try {
      const res = await fetch(API + "/meta/recommend-iaf?major=" + encodeURIComponent(major));
      const data = await res.json().catch(() => ({}));
      state.majorIaf = res.ok ? (data.recommendations || []) : [];
      box.innerHTML = state.majorIaf.length
        ? `<span class="status-wait">전공 추천 IAF: ${state.majorIaf.map((r) => "IAF " + r.iaf_code).join(", ")}</span>`
        : '<span class="muted" style="font-size:0.85rem;">전공 추천 IAF가 없습니다.</span>';
      await refreshCombinedScopes();
    } catch (e) {
      box.innerHTML = `<span class="muted">${esc(e.message)}</span>`;
    }
  }

  async function refreshCombinedScopes() {
    const box = document.getElementById("scope-checkboxes");
    const major = firstMajorFromDom();
    const companyId = firstCompanyIdFromState();
    state.companyIaf = collectCompanyIafFromState();
    const params = new URLSearchParams();
    if (major.length >= 2) params.set("major", major);
    if (companyId) params.set("company_id", String(companyId));
    if (![...params.keys()].length) {
      mergeLocalScopes(box);
      return;
    }
    try {
      const res = await fetch(API + "/meta/recommend-iaf?" + params);
      const data = await res.json().catch(() => ({}));
      const list = res.ok ? (data.recommendations || []) : [];
      if (!list.length) { mergeLocalScopes(box); return; }
      state.allIaf = {};
      list.forEach((r) => { state.allIaf[r.iaf_code] = r; });
      // merge extra company IAF from other career rows
      state.companyIaf.forEach((r) => { if (r && r.iaf_code) state.allIaf[r.iaf_code] = r; });
      renderScopeCheckboxes(box, Object.values(state.allIaf), true);
    } catch (_) {
      mergeLocalScopes(box);
    }
  }

  function mergeLocalScopes(box) {
    const map = {};
    [...state.majorIaf, ...state.companyIaf].forEach((r) => {
      map[r.iaf_code] = r;
    });
    const list = Object.values(map);
    state.allIaf = {};
    list.forEach((r) => { state.allIaf[r.iaf_code] = r; });
    if (!list.length) {
      box.innerHTML = '<span class="muted" style="font-size:0.85rem;">전공 또는 기업을 입력하면 Scope가 채워집니다.</span>';
      return;
    }
    renderScopeCheckboxes(box, list, true);
  }

  function renderScopeCheckboxes(box, list, checkedDefault) {
    const prevChecked = new Set(
      [...document.querySelectorAll("#scope-checkboxes input[type=checkbox]:checked")].map((el) => el.value)
    );
    box.innerHTML = list.map((r) => {
      const checked = prevChecked.size ? prevChecked.has(r.iaf_code) : checkedDefault;
      return `<div class="scope-item">
        <input type="checkbox" id="iaf-${esc(r.iaf_code)}" value="${esc(r.iaf_code)}" ${checked ? "checked" : ""} />
        <label for="iaf-${esc(r.iaf_code)}">
          <strong>IAF ${esc(r.iaf_code)}</strong> — ${esc(r.industry_name_ko || r.name_en || "")}
        </label>
      </div>`;
    }).join("");
  }

  function addManualIaf() {
    const code = (document.getElementById("iaf-manual").value || "").trim();
    if (!code) return;
    const box = document.getElementById("scope-checkboxes");
    if (!state.allIaf[code]) {
      state.allIaf[code] = { iaf_code: code, industry_name_ko: "", source: "manual" };
    }
    renderScopeCheckboxes(box, Object.values(state.allIaf), true);
    const el = document.getElementById("iaf-" + code);
    if (el) el.checked = true;
    document.getElementById("iaf-manual").value = "";
  }

  async function submitApply() {
    const err = document.getElementById("apply-error");
    err.textContent = "";
    const grade = document.getElementById("apply-grade").value;
    const requested = [...document.querySelectorAll("#scope-checkboxes input[type=checkbox]:checked")].map((el) => el.value);
    const educations = collectEducations().map((e) => ({
      ...e,
      school_name: e.school_name || (e.major ? "미입력" : ""),
    })).filter((e) => e.school_name);
    const work_experiences = collectCareers();
    const majorFallback = (educations.find((ed) => ed.major) || {}).major || null;
    const standards = [...document.querySelectorAll("input[name=apply-std]:checked")].map((el) => el.value);
    const qualifications = collectQualifications(majorFallback, requested, grade);

    if (!state.cbId) { err.textContent = "신청할 CB가 없습니다."; return; }
    if (!requested.length) { err.textContent = "신청할 IAF Scope를 1개 이상 선택하세요."; return; }

    try {
      const res = await fetch(API + "/auditor/memberships/request", {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({
          cb_id: state.cbId,
          apply_grade: grade,
          employment_type: "parttime",
          educations,
          work_experiences,
          major: majorFallback,
          requested_iaf_codes: requested,
          qualifications,
          cert_standards: standards,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(typeof detail === "string" ? detail : "신청 실패 (" + res.status + ")");
      }
      alert(data.message || "신청이 접수되었습니다.");
      closeApplyModal();
      loadProfilePanel();
      loadDashboard();
    } catch (e) {
      err.textContent = e.message;
    }
  }

  /* ── events ── */
  document.addEventListener("click", (evt) => {
    const nav = evt.target.closest(".sidebar-menu-item[data-tab]");
    if (nav) {
      evt.preventDefault();
      switchTab(nav.getAttribute("data-tab"));
      return;
    }
    const calDay = evt.target.closest("[data-cal-date]");
    if (calDay) {
      evt.preventDefault();
      renderDayDetail(calDay.getAttribute("data-cal-date"));
      renderCalendar();
      return;
    }
    const delUnavail = evt.target.closest("[data-del-unavail]");
    if (delUnavail) {
      evt.preventDefault();
      deleteUnavailability(delUnavail.getAttribute("data-del-unavail"));
      return;
    }
    const openReport = evt.target.closest("[data-open-report]");
    if (openReport) {
      evt.preventDefault();
      const cid = openReport.getAttribute("data-open-report");
      switchTab("reports");
      if (cid) openResultReport(cid);
      return;
    }
    const rptTab = evt.target.closest(".aud-rpt-tab[data-rpt-tab]");
    if (rptTab) {
      evt.preventDefault();
      reportState.tab = rptTab.getAttribute("data-rpt-tab") || "clauses";
      renderReportBody();
      return;
    }
    if (evt.target.closest("#aud-report-back")) {
      evt.preventDefault();
      closeResultReport();
      return;
    }
    if (evt.target.closest("#aud-report-open-notes")) {
      evt.preventDefault();
      const cid = reportState.contractId;
      closeResultReport();
      if (cid && window.AuditorAuditNotes) window.AuditorAuditNotes.open(cid);
      return;
    }
    const openNote = evt.target.closest("[data-open-note]");
    if (openNote) {
      evt.preventDefault();
      const cid = openNote.getAttribute("data-open-note");
      closeResultReport();
      switchTab("reports");
      if (window.AuditorAuditNotes) {
        if (cid) window.AuditorAuditNotes.open(cid);
        else window.AuditorAuditNotes.openPreview();
      }
      return;
    }
    const openPreview = evt.target.closest("[data-open-preview-note]");
    if (openPreview) {
      evt.preventDefault();
      closeResultReport();
      switchTab("reports");
      if (window.AuditorAuditNotes) {
        window.AuditorAuditNotes.openPreview(
          openPreview.getAttribute("data-standard") || null
        );
      }
      return;
    }
    const goto = evt.target.closest("[data-goto]");
    if (goto) {
      evt.preventDefault();
      const tab = goto.getAttribute("data-goto");
      const contract = goto.getAttribute("data-contract");
      switchTab(tab, { focus: goto.getAttribute("data-focus") });
      if (tab === "reports" && window.AuditorAuditNotes) {
        if (contract) window.AuditorAuditNotes.open(contract);
        else window.AuditorAuditNotes.openPreview();
      }
      return;
    }
    const openApply = evt.target.closest("[data-open-apply]");
    if (openApply) {
      evt.preventDefault();
      openApplyModal(
        Number(openApply.getAttribute("data-open-apply")),
        openApply.getAttribute("data-cb-name") || ""
      );
      return;
    }
  });

  document.getElementById("logout-btn")?.addEventListener("click", (e) => {
    e.preventDefault();
    ["access_token", "user_id", "user_name", "role", "cb_id", "company_id", "client_company_id", "membership_status"]
      .forEach((k) => localStorage.removeItem(k));
    location.href = "/login";
  });

  document.getElementById("reload-btn")?.addEventListener("click", () => {
    loadDashboard();
    const tab = new URL(location.href).searchParams.get("tab") || "dashboard";
    if (tab === "schedules") loadSchedulesPanel();
    if (tab === "reports") loadReportsPanel();
    if (tab === "ncrs") loadNcrsPanel();
    if (tab === "mypage") loadMypagePanel();
    if (tab === "profile") loadProfilePanel();
  });

  document.getElementById("aud-cal-prev")?.addEventListener("click", () => {
    calState.month -= 1;
    if (calState.month < 1) {
      calState.month = 12;
      calState.year -= 1;
    }
    calState.selectedDate = null;
    loadSchedulesPanel();
  });
  document.getElementById("aud-cal-next")?.addEventListener("click", () => {
    calState.month += 1;
    if (calState.month > 12) {
      calState.month = 1;
      calState.year += 1;
    }
    calState.selectedDate = null;
    loadSchedulesPanel();
  });
  document.getElementById("aud-unavail-open")?.addEventListener("click", () => {
    setUnavailFormOpen(true);
  });
  document.getElementById("aud-unavail-cancel")?.addEventListener("click", () => {
    setUnavailFormOpen(false);
  });
  document.getElementById("aud-unavail-submit")?.addEventListener("click", () => {
    submitUnavailability();
  });

  document.getElementById("apply-cancel")?.addEventListener("click", closeApplyModal);
  document.getElementById("applyModal")?.addEventListener("click", (e) => {
    if (e.target.id === "applyModal") closeApplyModal();
  });
  document.getElementById("apply-btn-add-edu")?.addEventListener("click", () => addEduRow());
  document.getElementById("apply-btn-add-career")?.addEventListener("click", () => addCareer());
  document.querySelectorAll("input[name=apply-std]").forEach((el) => {
    el.addEventListener("change", syncQualRows);
  });
  document.getElementById("apply-submit")?.addEventListener("click", submitApply);

  // expose for inline handlers
  window.searchCb = searchCb;
  window.addManualIaf = addManualIaf;
  document.getElementById("aud-doc-back")?.addEventListener("click", () => {
    closeDocsViewer();
    loadDocsPanel();
  });

  window.AuditorPortal = {
    switchTab,
    loadDashboard,
    reloadReports: loadReportsPanel,
    openResultReport,
    closeResultReport,
    openDocsViewer,
    closeDocsViewer,
    loadDocsPanel,
  };

  loadIafDatalist();
  loadSession().then(() => {
    const tab = new URL(location.href).searchParams.get("tab") || "dashboard";
    switchTab(tab);
    loadDashboard();
  });
})();
