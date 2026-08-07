/* Shared EMS / OHS / EnMS characteristic form helpers */
(function (global) {
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function checkedSet(arr) {
    const s = new Set((arr || []).map(String));
    return (v) => (s.has(String(v)) ? " checked" : "");
  }

  function yn(name, val) {
    const v = String(val || "");
    return (
      `<label><input type="radio" name="${esc(name)}" value="yes"${v === "yes" ? " checked" : ""}> 예</label>` +
      `<label><input type="radio" name="${esc(name)}" value="no"${v === "no" ? " checked" : ""}> 아니오</label>`
    );
  }

  function chips(name, options, selected) {
    const ck = checkedSet(selected);
    return (
      `<div class="aspect-chips">` +
      (options || [])
        .map(
          (o) =>
            `<label class="aspect-chip"><input type="checkbox" name="${esc(name)}" value="${esc(o)}"${ck(o)}> ${esc(o)}</label>`
        )
        .join("") +
      `</div>`
    );
  }

  function renderEms(box, catalog, data) {
    const c = catalog || {};
    const d = data || c.empty || {};
    const permits = d.permits || {};
    const haz = d.hazardous || {};
    const eia = d.eia || {};
    const rec = d.records || {};
    box.innerHTML = `
      <h4 class="aspect-sub">입지조건</h4>
      ${chips("ems_location", c.location_options, d.location)}
      <h4 class="aspect-sub">환경 인허가</h4>
      <div class="aspect-grid">
        <div class="ff"><label>대기</label>${chips("ems_air", c.permit_classes, permits.air)}</div>
        <div class="ff"><label>수질</label>${chips("ems_water", c.permit_classes, permits.water)}</div>
        <div class="ff"><label>소음진동</label>
          <label><input type="checkbox" id="ems_noise" ${permits.noise_vibration ? "checked" : ""}> 유</label>
        </div>
      </div>
      <h4 class="aspect-sub">위험물질 / 방지시설</h4>
      <div class="aspect-grid">
        <div class="ff"><label>위험물질 종류</label><input class="form-input" id="ems_materials" value="${esc(haz.materials || "")}"></div>
        <div class="ff"><label>배출·방지시설명</label><input class="form-input" id="ems_facilities" value="${esc(haz.facilities || "")}"></div>
      </div>
      <h4 class="aspect-sub">환경영향평가 / 사고</h4>
      <div class="aspect-grid">
        <div class="ff"><label>환경영향평가 실시</label><div class="radios">${yn("ems_eia_done", eia.done)}</div></div>
        <div class="ff"><label>실시일</label><input class="form-input" type="date" id="ems_eia_date" value="${esc(eia.date || "")}"></div>
        <div class="ff"><label>절차명/번호</label><input class="form-input" id="ems_eia_proc" value="${esc(eia.procedure || "")}"></div>
        <div class="ff"><label>최근 3년 환경사고</label><div class="radios">${yn("ems_acc", eia.accident_3y)}</div></div>
        <div class="ff" style="grid-column:1/-1"><label>사고 내용</label><input class="form-input" id="ems_acc_detail" value="${esc(eia.accident_detail || "")}"></div>
      </div>
      <h4 class="aspect-sub">환경 세부측면</h4>
      ${chips("ems_aspects", c.aspect_options, d.aspects)}
      <h4 class="aspect-sub">이행기록</h4>
      <div class="aspect-grid">
        <div class="ff"><label>준수평가 실시일</label><input class="form-input" type="date" id="ems_comp_date" value="${esc(rec.compliance_date || "")}"></div>
        <div class="ff"><label>준수평가 절차명/번호</label><input class="form-input" id="ems_comp_proc" value="${esc(rec.compliance_procedure || "")}"></div>
        <div class="ff"><label>비상훈련 일자</label><input class="form-input" type="date" id="ems_em_date" value="${esc(rec.emergency_date || "")}"></div>
        <div class="ff"><label>비상훈련 절차명/번호</label><input class="form-input" id="ems_em_proc" value="${esc(rec.emergency_procedure || "")}"></div>
      </div>`;
  }

  function renderOhs(box, catalog, data) {
    const c = catalog || {};
    const d = data || c.empty || {};
    const risk = d.risk || {};
    const rec = d.records || {};
    box.innerHTML = `
      <h4 class="aspect-sub">위험성평가 / 사고</h4>
      <div class="aspect-grid">
        <div class="ff"><label>클라이언트 프로파일 작성</label><div class="radios">${yn("ohs_profile", risk.client_profile)}</div></div>
        <div class="ff"><label>위험성평가 실시</label><div class="radios">${yn("ohs_assess", risk.assessment_done)}</div></div>
        <div class="ff"><label>실시일</label><input class="form-input" type="date" id="ohs_assess_date" value="${esc(risk.assessment_date || "")}"></div>
        <div class="ff"><label>절차명/번호</label><input class="form-input" id="ohs_assess_proc" value="${esc(risk.assessment_procedure || "")}"></div>
        <div class="ff" style="grid-column:1/-1"><label>주요 시설명</label><input class="form-input" id="ohs_facilities" value="${esc(risk.facilities || "")}" placeholder="CNC, MCT, 콤프레샤 등"></div>
        <div class="ff"><label>최근 안전사고</label><div class="radios">${yn("ohs_acc", risk.accident_recent)}</div></div>
        <div class="ff"><label>사고 내용</label><input class="form-input" id="ohs_acc_detail" value="${esc(risk.accident_detail || "")}"></div>
      </div>
      <h4 class="aspect-sub">위험요인 세부</h4>
      ${chips("ohs_hazards", c.hazard_options, d.hazards)}
      <h4 class="aspect-sub">이행기록</h4>
      <div class="aspect-grid">
        <div class="ff"><label>준수평가 실시일</label><input class="form-input" type="date" id="ohs_comp_date" value="${esc(rec.compliance_date || "")}"></div>
        <div class="ff"><label>준수평가 절차명/번호</label><input class="form-input" id="ohs_comp_proc" value="${esc(rec.compliance_procedure || "")}"></div>
        <div class="ff"><label>비상훈련 일자</label><input class="form-input" type="date" id="ohs_em_date" value="${esc(rec.emergency_date || "")}"></div>
        <div class="ff"><label>비상훈련 절차명/번호</label><input class="form-input" id="ohs_em_proc" value="${esc(rec.emergency_procedure || "")}"></div>
      </div>`;
  }

  function renderEnms(box, catalog, data) {
    const c = catalog || {};
    const d = data || c.empty || {};
    const en = d.energy || {};
    const rec = d.records || {};
    box.innerHTML = `
      <h4 class="aspect-sub">에너지검토 / 시설</h4>
      <div class="aspect-grid">
        <div class="ff"><label>에너지경영질문서 작성</label><div class="radios">${yn("enms_q", en.questionnaire_done)}</div></div>
        <div class="ff"><label>에너지검토 실시</label><div class="radios">${yn("enms_review", en.review_done)}</div></div>
        <div class="ff"><label>실시일</label><input class="form-input" type="date" id="enms_review_date" value="${esc(en.review_date || "")}"></div>
        <div class="ff"><label>절차명/번호</label><input class="form-input" id="enms_review_proc" value="${esc(en.review_procedure || "")}"></div>
        <div class="ff" style="grid-column:1/-1"><label>주요 시설명</label><input class="form-input" id="enms_facilities" value="${esc(en.facilities || "")}"></div>
      </div>
      <h4 class="aspect-sub">중요 에너지원</h4>
      ${chips("enms_sources", c.source_options, d.sources)}
      <h4 class="aspect-sub">이행기록</h4>
      <div class="aspect-grid">
        <div class="ff"><label>에너지베이스라인 평가일</label><input class="form-input" type="date" id="enms_base_date" value="${esc(rec.baseline_date || "")}"></div>
        <div class="ff"><label>베이스라인 절차명/번호</label><input class="form-input" id="enms_base_proc" value="${esc(rec.baseline_procedure || "")}"></div>
        <div class="ff"><label>에너지성과 평가일</label><input class="form-input" type="date" id="enms_perf_date" value="${esc(rec.performance_date || "")}"></div>
        <div class="ff"><label>성과평가 절차명/번호</label><input class="form-input" id="enms_perf_proc" value="${esc(rec.performance_procedure || "")}"></div>
      </div>`;
  }

  function collectChecked(name) {
    return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
  }
  function radioVal(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : "";
  }
  function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  function collectEms() {
    return {
      location: collectChecked("ems_location"),
      permits: {
        air: collectChecked("ems_air"),
        water: collectChecked("ems_water"),
        noise_vibration: !!(document.getElementById("ems_noise") || {}).checked,
      },
      hazardous: { materials: val("ems_materials"), facilities: val("ems_facilities") },
      eia: {
        done: radioVal("ems_eia_done"),
        date: val("ems_eia_date"),
        procedure: val("ems_eia_proc"),
        accident_3y: radioVal("ems_acc"),
        accident_detail: val("ems_acc_detail"),
      },
      aspects: collectChecked("ems_aspects"),
      records: {
        compliance_date: val("ems_comp_date"),
        compliance_procedure: val("ems_comp_proc"),
        emergency_date: val("ems_em_date"),
        emergency_procedure: val("ems_em_proc"),
      },
    };
  }

  function collectOhs() {
    return {
      risk: {
        client_profile: radioVal("ohs_profile"),
        assessment_done: radioVal("ohs_assess"),
        assessment_date: val("ohs_assess_date"),
        assessment_procedure: val("ohs_assess_proc"),
        facilities: val("ohs_facilities"),
        accident_recent: radioVal("ohs_acc"),
        accident_detail: val("ohs_acc_detail"),
      },
      hazards: collectChecked("ohs_hazards"),
      records: {
        compliance_date: val("ohs_comp_date"),
        compliance_procedure: val("ohs_comp_proc"),
        emergency_date: val("ohs_em_date"),
        emergency_procedure: val("ohs_em_proc"),
      },
    };
  }

  function collectEnms() {
    return {
      energy: {
        questionnaire_done: radioVal("enms_q"),
        review_done: radioVal("enms_review"),
        review_date: val("enms_review_date"),
        review_procedure: val("enms_review_proc"),
        facilities: val("enms_facilities"),
      },
      sources: collectChecked("enms_sources"),
      records: {
        baseline_date: val("enms_base_date"),
        baseline_procedure: val("enms_base_proc"),
        performance_date: val("enms_perf_date"),
        performance_procedure: val("enms_perf_proc"),
      },
    };
  }

  function formatAspectsHtml(aspects) {
    if (!aspects) return '<p class="hint">특성 정보 없음</p>';
    const parts = [];
    function block(title, obj) {
      if (!obj) return;
      parts.push(`<h4 class="aspect-sub">${esc(title)}</h4><pre class="aspect-pre">${esc(JSON.stringify(obj, null, 2))}</pre>`);
    }
    block("EMS (ISO 14001)", aspects.ems);
    block("OHS (ISO 45001)", aspects.ohs);
    block("EnMS (ISO 50001)", aspects.enms);
    return parts.join("") || '<p class="hint">특성 정보 없음</p>';
  }

  global.CompanyAspectsForm = {
    renderEms,
    renderOhs,
    renderEnms,
    collectEms,
    collectOhs,
    collectEnms,
    formatAspectsHtml,
  };
})(window);
