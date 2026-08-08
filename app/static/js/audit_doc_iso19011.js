/**
 * ISO 19011 shared constants / helpers for audit document HTML pages.
 * Keep fixed phrases here — do not scatter string literals across report/plan files.
 */
(function (global) {
  "use strict";

  /** ISO 19011 §6.4.10 a) — sampling nature statement (CB-editable in one place). */
  var SAMPLING_NATURE_TEXT =
    "본 심사는 표본추출(sampling)에 기반하며, 표본 결과는 전체 모집단의 완전성을 " +
    "보장하지 않는다. 발견사항은 심사 시점에 확인된 증거에 한정된다. " +
    "(ISO 19011 §6.4.10 a 참고)";

  var EMPTY_DISAGREEMENT_TEXT = "없음";

  function auditObjectiveFromContext(ctx, stage) {
    ctx = ctx || (global.ComplaisAuditDocMaster && global.ComplaisAuditDocMaster.context) || {};
    var master = ctx.master || {};
    var plan = ctx.audit_plan || {};
    var fromPlan = (plan.audit_objective || master.audit_objective || "").trim();
    if (fromPlan) return fromPlan;
    var at = String(master.audit_type || (ctx.contract && ctx.contract.audit_type) || "").toLowerCase();
    var stageLabel = stage === "stage1" ? "1단계" : stage === "stage2" ? "2단계" : "인증";
    if (at.indexOf("recert") >= 0 || at.indexOf("renew") >= 0 || at.indexOf("갱신") >= 0) {
      return stageLabel + " 심사 — 인증 범위 재확인 및 경영시스템 지속 적합성·유효성 판정";
    }
    if (at.indexOf("surv") >= 0 || at.indexOf("사후") >= 0) {
      return stageLabel + " 심사 — 인증 유지 적합성 확인 및 주요 프로세스 이행 검증";
    }
    if (stage === "stage1") {
      return "1단계 심사 — 문서화된 정보·적용범위 확인 및 2단계 준비상태 평가 (적합성 판정 준비)";
    }
    return "2단계 심사 — 경영시스템 요구사항 적합성 판정 및 인증 범위 확인";
  }

  function displayDisagreement(raw) {
    var t = (raw == null ? "" : String(raw)).trim();
    return t || EMPTY_DISAGREEMENT_TEXT;
  }

  global.ComplaisIso19011 = {
    SAMPLING_NATURE_TEXT: SAMPLING_NATURE_TEXT,
    EMPTY_DISAGREEMENT_TEXT: EMPTY_DISAGREEMENT_TEXT,
    auditObjectiveFromContext: auditObjectiveFromContext,
    displayDisagreement: displayDisagreement,
  };
})(typeof window !== "undefined" ? window : globalThis);
