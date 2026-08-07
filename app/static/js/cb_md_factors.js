/* CB application-review MD factor chips + design exclusion helpers */
(function (global) {
  "use strict";

  const INCREASE = {
    공통: [
      { ref: "추가요소 공통", label: "현장이 2개 이상의 건물 또는 장소와 관련된 복잡한 물류인가?" },
      { ref: "추가요소 공통", label: "2개 이상의 언어를 사용하는 직원이 포함되어 통역이 요구되는가?" },
      { ref: "2.1", label: "종업원 수에 비하여 광범위한 사업장인가?" },
      { ref: "2.7", label: "매우 복잡한 프로세스를 포함하거나 고유활동이 상대적으로 다수 포함된 시스템" },
      { ref: "3.4.1", label: "임시사업장(건설현장 등)의 확인이 요구되는 경우 이동시간" },
      { ref: "2.8", label: "외주처리하는 기능 또는 프로세스가 있는가? (있는 경우 이동시간)" },
      { ref: "고위험", label: "높은 리스크에 해당하는 활동" },
    ],
    EMS: [
      { ref: "5.2.2", label: "주변환경의 민감도가 높은 경우(특별대책지역이나 상수도 보호구역 등)인가?" },
      { ref: "5.2.2", label: "이해관계자의 의견이 있는가?" },
      { ref: "5.2.2", label: "심사시간의 증가를 필요로 하는 간접적인 측면" },
      { ref: "5.2.2", label: "산업분야별 부가적/특이한 환경측면 또는 환경 허가/규제기관의 조건이 있는가?" },
      { ref: "5.2.2", label: "환경사고나 영향이 증가되는 리스크(지리적, 계절적 요인 포함)가 있는가?" },
    ],
    "OH&S": [
      { ref: "6.1", label: "이해관계자의 견해" },
      { ref: "6.2", label: "산업분야 평균보다 높은 사고 및 질병 발생률" },
      { ref: "6.3", label: "일반 대중의 일원이 조직의 현장에 존재하는 경우" },
      { ref: "6.4", label: "법적 소송에 처한 경우" },
      { ref: "6.5", label: "다수의 협력사 및 관련 인원이 있는 경우" },
      { ref: "6.6", label: "위험물질이 대량으로 존재하는 경우" },
      { ref: "6.7", label: "모국 이외의 다른 국가에 사이트가 있는 경우" },
    ],
    ISMS: [
      { ref: "추가요소 ISMS", label: "다수 시스템·클라우드·하이브리드 인프라가 심사 범위에 포함되는가?" },
      { ref: "추가요소 ISMS", label: "개인정보·민감정보 처리 규모가 크거나 규제 산업(금융·의료 등)인가?" },
      { ref: "추가요소 ISMS", label: "자체 소프트웨어 개발·DevOps 파이프라인이 범위에 포함되는가?" },
      { ref: "추가요소 ISMS", label: "IT 운영/개발의 광범위한 외주 및 다수 공급자 관리가 요구되는가?" },
    ],
    FSMS: [
      { ref: "추가요소 FSMS", label: "다수 품목(SKU)·다수 라인의 식품 제조/가공을 수행하는가?" },
      { ref: "추가요소 FSMS", label: "냉장/냉동 콜드체인 또는 고위험 공정(가열살균 등)이 있는가?" },
      { ref: "추가요소 FSMS", label: "알레르기 유발물질(알러젠) 교차오염 관리가 복잡한가?" },
      { ref: "추가요소 FSMS", label: "HACCP 지정/인증 대상이거나 법적 요건이 강화된 경우인가?" },
    ],
    EnMS: [
      { ref: "추가요소 EnMS", label: "에너지 사용처·계측점이 다수이거나 SEU가 복잡한가?" },
      { ref: "추가요소 EnMS", label: "다수 사업장·유틸리티에 걸친 에너지 성과 확인이 요구되는가?" },
      { ref: "추가요소 EnMS", label: "대규모 에너지 효율 투자/개선 프로젝트가 심사 범위에 포함되는가?" },
    ],
    ABMS: [
      { ref: "추가요소 ABMS", label: "공공조달·고위험 거래·다수 중개상이 포함된 사업인가?" },
      { ref: "추가요소 ABMS", label: "해외 사업·다국가 컴플라이언스 요구가 있는가?" },
      { ref: "추가요소 ABMS", label: "뇌물·부패 관련 과거 이슈 또는 규제 조사가 있는가?" },
    ],
    CMS: [
      { ref: "추가요소 CMS", label: "규제·의무 요구사항의 범위가 넓고 다수 법규를 다루는가?" },
      { ref: "추가요소 CMS", label: "준법 리스크가 높은 산업·거래 형태인가?" },
      { ref: "추가요소 CMS", label: "다수 계열사·해외법인의 준법체계 확인이 요구되는가?" },
    ],
    BCMS: [
      { ref: "추가요소 BCMS", label: "핵심 서비스 24시간 운영 또는 짧은 RTO가 요구되는가?" },
      { ref: "추가요소 BCMS", label: "데이터센터·핵심 인프라를 직접 운영하는가?" },
      { ref: "추가요소 BCMS", label: "다수 사업장·공급망에 걸친 연속성 전략 검증이 필요한가?" },
    ],
    MDMS: [
      { ref: "추가요소 MDMS", label: "고위험 등급 의료기기 또는 멸균·클린룸 공정이 있는가?" },
      { ref: "추가요소 MDMS", label: "다수 품목·다수 제조공정이 범위에 포함되는가?" },
      { ref: "추가요소 MDMS", label: "설계/개발·임상평가·시판후감시 활동이 범위에 포함되는가?" },
      { ref: "추가요소 MDMS", label: "규제당국(식약처 등) 요구사항 검증 범위가 넓은가?" },
    ],
  };

  const DECREASE = {
    공통: [
      { ref: "2.5 / 2.6", label: "종업원 수에 비하여 매우 작은 사업장인가? (사무소만 있는 경우)" },
      { ref: "감소요소 공통", label: "경영시스템 성숙도" },
      { ref: "감소요소 공통", label: "경영시스템에 대한 사전지식(SMI의 타 경영시스템 인증 보유시)" },
      { ref: "감소요소 공통", label: "경영체제 인증 준비상태(다른 인증을 유지하고 있는 경우)" },
      { ref: "저위험", label: "낮은 리스크로 간주할 수 있는 활동(복잡도 낮음)" },
    ],
    QMS: [
      { ref: "2.5 / 2.6", label: "다수의 종업원이 외근직이고 동일한 업무를 수행하며 기록을 통해 확인 가능한 경우" },
      { ref: "감소요소 QMS", label: "높은 자동화 수준" },
    ],
    EMS: [
      { ref: "감소요소 EMS", label: "다수의 종업원이 외근직이고 동일한 업무를 수행하며 기록을 통해 확인 가능한 경우" },
      { ref: "감소요소 EMS", label: "높은 자동화 수준 및 낮은 환경적 중요성" },
    ],
    ISMS: [
      { ref: "감소요소 ISMS", label: "범위가 단순 사무·단일 시스템에 한정되고 외주가 최소인 경우" },
      { ref: "감소요소 ISMS", label: "기존 인증(ISMS/PIMS 등) 유지로 사전 지식·성숙도가 높은 경우" },
    ],
    FSMS: [
      { ref: "감소요소 FSMS", label: "단순 유통·보관 중심으로 제조공정이 없거나 매우 단순한 경우" },
      { ref: "감소요소 FSMS", label: "기존 HACCP/FSMS 유지로 준비상태가 높은 경우" },
    ],
    EnMS: [
      { ref: "감소요소 EnMS", label: "에너지 사용처가 소수이고 SEU 구조가 단순한 경우" },
      { ref: "감소요소 EnMS", label: "기존 EnMS 인증 유지로 성숙도가 높은 경우" },
    ],
    ABMS: [
      { ref: "감소요소 ABMS", label: "부패 리스크가 낮고 거래·조달 구조가 단순한 경우" },
      { ref: "감소요소 ABMS", label: "기존 ABMS/CMS 인증 유지로 준비상태가 높은 경우" },
    ],
    CMS: [
      { ref: "감소요소 CMS", label: "적용 법규·의무 범위가 좁고 조직 구조가 단순한 경우" },
      { ref: "감소요소 CMS", label: "기존 CMS/ABMS 인증 유지로 성숙도가 높은 경우" },
    ],
    BCMS: [
      { ref: "감소요소 BCMS", label: "단일 사업장·단순 복구 전략으로 복잡도가 낮은 경우" },
      { ref: "감소요소 BCMS", label: "기존 BCMS 인증 유지로 준비상태가 높은 경우" },
    ],
    MDMS: [
      { ref: "감소요소 MDMS", label: "저위험 등급·단순 공정에 한정된 경우" },
      { ref: "감소요소 MDMS", label: "설계 제외(적용제외) 및 외주 최소로 범위가 축소된 경우" },
    ],
  };

  const INTEGRATED = [
    { ref: "통합수준", label: "적절하게 개발된 업무지침 등을 포함한 통합 문서세트" },
    { ref: "통합수준", label: "전체적인 사업전략 및 계획을 고려하는 경영검토" },
    { ref: "통합수준", label: "내부심사 통합 접근" },
    { ref: "통합수준", label: "방침 및 목표에 대한 통합 접근" },
    { ref: "통합수준", label: "시스템 프로세스에 대한 통합 접근" },
    { ref: "통합수준", label: "개선 메커니즘에 대한 통합 접근(시정조치, 개선)" },
    { ref: "통합수준", label: "통합된 경영지원 및 지침" },
  ];

  const GROUP_MATCH = {
    QMS: ["9001", "QMS"],
    EMS: ["14001", "EMS"],
    "OH&S": ["45001", "OHSMS", "OHS", "OH&S"],
    ISMS: ["27001", "ISMS"],
    FSMS: ["22000", "FSMS"],
    EnMS: ["50001", "EnMS", "ENMS"],
    ABMS: ["37001", "ABMS"],
    CMS: ["37301", "CMS"],
    BCMS: ["22301", "BCMS"],
    MDMS: ["13485", "MDMS", "MDQMS"],
  };

  function standardsTokens(standards) {
    const tokens = new Set();
    (standards || []).forEach((s) => {
      if (!s) return;
      if (typeof s === "object") {
        ["code", "initial", "iso_code", "label"].forEach((k) => {
          if (s[k]) tokens.add(String(s[k]).toUpperCase());
        });
      } else {
        tokens.add(String(s).toUpperCase());
      }
    });
    return tokens;
  }

  function groupPresent(group, tokens) {
    if (group === "공통") return true;
    const keys = GROUP_MATCH[group] || [group];
    for (const t of tokens) {
      for (const k of keys) {
        if (t.includes(String(k).toUpperCase())) return true;
      }
    }
    return false;
  }

  function appendMdFactor(kind, group, ref, label) {
    const note = document.getElementById("md-note");
    if (!note) return;
    const parts = ["[" + kind + "]", "[" + group + (ref ? " " + ref : "") + "]", label];
    const line = parts.join(" ");
    const current = (note.value || "").trim();
    const rows = current ? current.split("\n").map((v) => v.trim()).filter(Boolean) : [];
    if (rows.includes(line)) return;
    note.value = current ? current + "\n" + line : line;
    note.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function designExclusionLine(standards) {
    const tokens = standardsTokens(standards);
    const has13485 = groupPresent("MDMS", tokens);
    const has9001 = groupPresent("QMS", tokens);
    if (has13485 && !has9001) {
      return "[적용제외] [MDMS / ISO 13485 7.3] 제품/서비스 설계 및 개발 프로세스 적용 제외 (MD 감축 요인)";
    }
    if (has13485 && has9001) {
      return "[적용제외] [QMS·MDMS / ISO 9001 8.3 · ISO 13485 7.3] 제품/서비스 설계 및 개발 프로세스 적용 제외 (MD 감축 요인)";
    }
    return "[적용제외] [QMS / ISO 9001 8.3] 제품/서비스 설계 및 개발 프로세스 적용 제외 (MD 감축 요인)";
  }

  function syncDesignExclusionNote(checked, standards) {
    const note = document.getElementById("md-note");
    if (!note) return;
    const line = designExclusionLine(standards);
    const rows = (note.value || "")
      .split("\n")
      .map((v) => v.trim())
      .filter((v) => v && !v.startsWith("[적용제외]"));
    if (checked) rows.unshift(line);
    note.value = rows.join("\n");
    note.dispatchEvent(new Event("input", { bubbles: true }));
  }

  function canShowDesignExclusion(standards) {
    const tokens = standardsTokens(standards);
    return groupPresent("QMS", tokens) || groupPresent("MDMS", tokens);
  }

  function renderFactorList(container, kind, catalog, tokens) {
    if (!container) return;
    const blocks = [];
    Object.keys(catalog).forEach((group) => {
      if (!groupPresent(group, tokens)) return;
      const items = catalog[group] || [];
      if (!items.length) return;
      blocks.push('<div class="md-factor-group"><div class="md-factor-group-title">' + group + "</div>");
      items.forEach((item) => {
        const ref = item.ref || "";
        const label = item.label || "";
        blocks.push(
          '<div class="md-factor-item">' +
            '<div class="md-factor-text"><span class="md-factor-meta">' +
            group +
            " / " +
            ref +
            "</span>" +
            label +
            "</div>" +
            '<button type="button" class="md-factor-btn" data-md-kind="' +
            kind +
            '" data-md-group="' +
            group +
            '" data-md-ref="' +
            ref.replace(/"/g, "&quot;") +
            '" data-md-label="' +
            label.replace(/"/g, "&quot;") +
            '">추가</button></div>'
        );
      });
      blocks.push("</div>");
    });
    container.innerHTML = blocks.join("") || '<p class="hint">해당 표준의 가감 요소가 없습니다.</p>';
  }

  function renderMdFactorPanels(standards, auditMode) {
    const tokens = standardsTokens(standards);
    renderFactorList(document.getElementById("md-increase-factors"), "추가요소", INCREASE, tokens);
    renderFactorList(document.getElementById("md-decrease-factors"), "감소요소", DECREASE, tokens);
    const intgBox = document.getElementById("md-integrated-factors");
    const intgWrap = document.getElementById("md-integrated-wrap");
    if (intgWrap) {
      intgWrap.style.display = auditMode === "integrated" ? "block" : "none";
    }
    if (intgBox && auditMode === "integrated") {
      intgBox.innerHTML = INTEGRATED.map((item) => {
        return (
          '<div class="md-factor-item">' +
          '<div class="md-factor-text"><span class="md-factor-meta">' +
          item.ref +
          "</span>" +
          item.label +
          "</div>" +
          '<button type="button" class="md-factor-btn" data-md-kind="통합심사" data-md-group="통합수준" data-md-ref="' +
          item.ref +
          '" data-md-label="' +
          item.label.replace(/"/g, "&quot;") +
          '">추가</button></div>'
        );
      }).join("");
    }
  }

  function bindFactorClicks(root) {
    (root || document).addEventListener("click", (e) => {
      const btn = e.target.closest(".md-factor-btn");
      if (!btn) return;
      appendMdFactor(
        btn.getAttribute("data-md-kind") || "추가요소",
        btn.getAttribute("data-md-group") || "",
        btn.getAttribute("data-md-ref") || "",
        btn.getAttribute("data-md-label") || ""
      );
    });
  }

  global.CbMdFactors = {
    INCREASE,
    DECREASE,
    INTEGRATED,
    appendMdFactor,
    designExclusionLine,
    syncDesignExclusionNote,
    canShowDesignExclusion,
    renderMdFactorPanels,
    bindFactorClicks,
  };
})(window);
