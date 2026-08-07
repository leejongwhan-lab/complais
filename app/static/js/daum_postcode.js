/**
 * Daum/Kakao Postcode — shared helper for address forms.
 * Requires: //t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js
 *
 * Usage:
 *   execDaumPostcode('zipId', 'addrId', 'detailId'[, 'enId'])
 *   <button type="button" data-postcode-zip="..." data-postcode-addr="..."
 *           data-postcode-detail="..." data-postcode-en="...">주소 검색</button>
 *   wireDaumPostcodeButtons(root?)  // for dynamically rendered rows
 */
(function (global) {
  "use strict";

  function setVal(id, value) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    el.value = value == null ? "" : String(value);
    try {
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (_) {}
  }

  function focusEl(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (el && typeof el.focus === "function") el.focus();
  }

  function execDaumPostcode(zipId, addrId, detailId, enId) {
    if (typeof daum === "undefined" || !daum.Postcode) {
      alert("우편번호 검색 스크립트를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
      return;
    }
    new daum.Postcode({
      oncomplete: function (data) {
        var addr =
          data.userSelectedType === "R" ? data.roadAddress : data.jibunAddress;
        if (data.buildingName !== "") {
          addr += " (" + data.buildingName + ")";
        }
        setVal(zipId, data.zonecode);
        setVal(addrId, addr);
        if (enId && data.addressEnglish) {
          setVal(enId, data.addressEnglish);
        }
        focusEl(detailId);
      },
    }).open();
  }

  function wireDaumPostcodeButtons(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll("[data-postcode-addr]").forEach(function (btn) {
      if (btn.dataset.postcodeBound === "1") return;
      btn.dataset.postcodeBound = "1";
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        execDaumPostcode(
          btn.getAttribute("data-postcode-zip"),
          btn.getAttribute("data-postcode-addr"),
          btn.getAttribute("data-postcode-detail"),
          btn.getAttribute("data-postcode-en")
        );
      });
    });
  }

  global.execDaumPostcode = execDaumPostcode;
  global.wireDaumPostcodeButtons = wireDaumPostcodeButtons;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      wireDaumPostcodeButtons(document);
    });
  } else {
    wireDaumPostcodeButtons(document);
  }
})(typeof window !== "undefined" ? window : this);
