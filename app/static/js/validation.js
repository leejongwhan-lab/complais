/**
 * ComplAIs 공통 입력 검증 — 사업자번호 / 전화 / 이메일
 * URL: /static/js/validation.js
 */
(function (global) {
  "use strict";

  const BIZ_WEIGHTS = [1, 3, 7, 1, 3, 7, 1, 3, 7];
  const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

  function digitsOnly(value) {
    return String(value || "").replace(/\D/g, "");
  }

  function formatBizNo(value) {
    const d = digitsOnly(value).slice(0, 10);
    if (!d) return "";
    if (d.length <= 3) return d;
    if (d.length <= 5) return `${d.slice(0, 3)}-${d.slice(3)}`;
    return `${d.slice(0, 3)}-${d.slice(3, 5)}-${d.slice(5)}`;
  }

  function isValidBizChecksum(digits10) {
    if (!/^\d{10}$/.test(digits10)) return false;
    const nums = digits10.split("").map(Number);
    let total = 0;
    for (let i = 0; i < 9; i++) total += nums[i] * BIZ_WEIGHTS[i];
    const mid = nums[7] * 3;
    total += Math.floor(mid / 10);
    const check = (10 - (total % 10)) % 10;
    return check === nums[9];
  }

  function validateBizNo(value, { required = false } = {}) {
    const raw = String(value || "").trim();
    if (!raw) {
      return required
        ? { ok: false, value: null, message: "사업자번호는 필수입니다." }
        : { ok: true, value: null, message: "" };
    }
    const d = digitsOnly(raw);
    if (d.length !== 10) {
      return { ok: false, value: formatBizNo(raw), message: "사업자번호는 10자리 숫자여야 합니다. (형식: 000-00-00000)" };
    }
    if (!isValidBizChecksum(d)) {
      return { ok: false, value: formatBizNo(d), message: "유효하지 않은 사업자번호입니다." };
    }
    return { ok: true, value: formatBizNo(d), message: "" };
  }

  function formatPhone(value) {
    const d = digitsOnly(value);
    if (!d) return "";
    if (d.startsWith("02")) {
      const rest = d.slice(2);
      if (rest.length <= 3) return rest ? `02-${rest}` : "02";
      if (d.length === 9) return `02-${rest.slice(0, 3)}-${rest.slice(3)}`;
      return `02-${rest.slice(0, 4)}-${rest.slice(4, 8)}`;
    }
    if (/^01[016789]/.test(d)) {
      if (d.length <= 3) return d;
      if (d.length <= 7) return `${d.slice(0, 3)}-${d.slice(3)}`;
      return `${d.slice(0, 3)}-${d.slice(3, 7)}-${d.slice(7, 11)}`;
    }
    if (d.startsWith("0") && d.length >= 9) {
      if (d.length === 10) return `${d.slice(0, 3)}-${d.slice(3, 6)}-${d.slice(6)}`;
      return `${d.slice(0, 3)}-${d.slice(3, 7)}-${d.slice(7, 11)}`;
    }
    return d;
  }

  function validatePhone(value, { required = false } = {}) {
    const raw = String(value || "").trim();
    if (!raw) {
      return required
        ? { ok: false, value: null, message: "전화번호는 필수입니다." }
        : { ok: true, value: null, message: "" };
    }
    const d = digitsOnly(raw);
    if (d.length < 9 || d.length > 11) {
      return { ok: false, value: formatPhone(raw), message: "전화번호는 9~11자리여야 합니다." };
    }
    if (!d.startsWith("0")) {
      return { ok: false, value: formatPhone(raw), message: "전화번호는 0으로 시작해야 합니다." };
    }
    return { ok: true, value: formatPhone(d), message: "" };
  }

  function validateEmail(value, { required = false } = {}) {
    const raw = String(value || "").trim();
    if (!raw) {
      return required
        ? { ok: false, value: null, message: "이메일은 필수입니다." }
        : { ok: true, value: null, message: "" };
    }
    const email = raw.toLowerCase();
    if (email.length > 200 || !EMAIL_RE.test(email)) {
      return { ok: false, value: email, message: "이메일 형식이 올바르지 않습니다." };
    }
    return { ok: true, value: email, message: "" };
  }

  /** 입력 필드에 blur/input 포맷터 연결 (중복 바인딩 방지) */
  function bindField(el, kind) {
    if (!el || el.dataset.complaisBound === "1") return;
    el.dataset.complaisBound = "1";
    const onFormat = () => {
      if (kind === "biz") el.value = formatBizNo(el.value);
      else if (kind === "phone") el.value = formatPhone(el.value);
      else if (kind === "email") el.value = String(el.value || "").trim().toLowerCase();
    };
    // 사업자번호·전화: 입력 중에도 하이픈 자동 삽입
    if (kind === "biz" || kind === "phone") {
      el.addEventListener("input", onFormat);
    }
    el.addEventListener("blur", onFormat);
    el.addEventListener("change", onFormat);
  }

  /**
   * 여러 필드를 한 번에 검증.
   * fields: [{ el|value, kind: 'biz'|'phone'|'email', required?, label? }]
   * 성공 시 { ok:true, values:{biz,phone,email} }, 실패 시 { ok:false, message }
   */
  function validateFields(fields) {
    const values = {};
    for (const f of fields || []) {
      const raw = f.el ? f.el.value : f.value;
      let result;
      if (f.kind === "biz") result = validateBizNo(raw, { required: !!f.required });
      else if (f.kind === "phone") result = validatePhone(raw, { required: !!f.required });
      else if (f.kind === "email") result = validateEmail(raw, { required: !!f.required });
      else continue;
      if (!result.ok) {
        return { ok: false, message: result.message, field: f };
      }
      if (f.el && result.value != null) f.el.value = result.value;
      values[f.kind] = result.value;
    }
    return { ok: true, values, message: "" };
  }

  global.ComplaisValidation = {
    digitsOnly,
    formatBizNo,
    formatPhone,
    validateBizNo,
    validatePhone,
    validateEmail,
    validateFields,
    bindField,
  };
})(typeof window !== "undefined" ? window : globalThis);
