<?php
require_once __DIR__ . '/DB.php';
require_once __DIR__ . '/Auth.php';
require_once __DIR__ . '/md_calc_config.php';
Auth::start();
if (!Auth::check()) { header('Location: index.php?err=login_required'); exit; }

// 신청서(certification_applications) 기준으로 불러오기 — 검토서(cb_application_review.php)와 동일한 키(application id) 사용.
// (예전엔 contracts 테이블 기준이었는데, 검토서는 certification_applications를 쓰고 있어서 서로 연결이 안 됐음 — 통일함)
$app_id = (int)($_GET['app_id'] ?? 0);
$prefill = [];
if ($app_id > 0) {
    $a = DB::row("SELECT a.id, a.standards_json, a.audit_mode, a.audit_type,
                         co.name AS co_name, co.employee_count, co.iaf_code, co.ksic_code
                  FROM certification_applications a
                  JOIN companies co ON co.id = a.company_id
                  WHERE a.id = $app_id LIMIT 1");
    if ($a) {
        $stds_arr = json_decode($a['standards_json'] ?? '[]', true) ?: [];
        $atype_map = ['initial'=>'initial','surveillance'=>'surv12','recertification'=>'recert','special'=>'initial','transfer'=>'transfer_surv12'];
        // standards_json은 두 형식을 다 받는다:
        //   구형(하위호환): ["9001","14001"]                          — 신청서 전체에 audit_type 하나
        //   신형: [{"code":"9001","audit_type":"surveillance"}, ...]  — 표준마다 심사유형이 다를 수 있음
        $stds_pairs = array_map(function ($s) use ($atype_map, $a) {
            $code = is_array($s) ? ($s['code'] ?? '') : $s;
            $code = strtolower(preg_replace('/[^0-9a-z-]/i', '', (string)$code));
            $rawAtype = is_array($s) ? ($s['audit_type'] ?? null) : null;
            $atype = $atype_map[$rawAtype ?? $a['audit_type']] ?? 'initial';
            return $code === '' ? null : "$code:$atype";
        }, $stds_arr);
        $site_count = (int)DB::val("SELECT COUNT(*) FROM certification_application_sites WHERE application_id = {$a['id']}");
        $prefill = [
            'app_id' => $a['id'],
            'co'     => $a['co_name'],
            'emp'    => (int)($a['employee_count'] ?? 50),
            'stds'   => implode(',', array_filter($stds_pairs)),
            'atype'  => $atype_map[$a['audit_type']] ?? 'initial',
            'sites'  => max(1, $site_count),
            'ksic'   => $a['ksic_code'] ?? '',
            'iaf'    => $a['iaf_code'] ?? '',
        ];
    }
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>KAB 심사일수 산정 v8</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<link rel="stylesheet" href="/assets/css/kab_audit_days.css">
<style>
/* 이 페이지가 company_main.php와 같은 대시보드 셸(assets/css/dashboard.css) 안에서 열릴 때는
   거기서 정의한 --text/--surface/--blue 등 값이 우선 적용되고, 이 블록은 기본값(fallback)이다. */
:root{
  --bg:#f5f6f8; --surface:#ffffff; --surface2:#f7f8fa;
  --text:#1a1a1a; --text2:#555555; --text3:#8a8f98; --text4:#b0b4bb;
  --border:#e5e7eb; --border2:#d1d5db;
  --blue:#185fa5; --blue2:#e6f1fb;
  --green:#047a5a; --green2:#e3f5ef; --green3:#0a9d76;
  --amber:#c97820; --amber2:#fff5e0; --amber3:#e0941a;
  --red:#dc2626; --red2:#fcebeb;
}
body{font-family:'Pretendard',var(--font-sans,'Apple SD Gothic Neo',sans-serif)}
</style>
</head>
<body>
<div style="color:var(--text,#1a1a1a)">

<!-- ── Step 1: 표준 선택 ── -->
<div class="card">
  <div class="step">Step 1 — 표준 선택</div>
  <div class="mode-tabs">
    <button class="mtab on" id="tab-s" onclick="setMode('single')">단일 심사</button>
    <button class="mtab"    id="tab-i" onclick="setMode('integrated')">통합 심사</button>
  </div>
  <div style="font-size:11px;color:var(--text2,#666);margin-bottom:5px" id="std-hint">표준을 선택하세요</div>
  <div class="std-grid" id="std-grid"></div>

  <!-- 통합심사 수준 (IAF MD11 Figure 1 — 2축 조회 방법론) -->
  <div class="panel" id="intg-panel" style="border-left-color:#7B3FAF">
    <div class="panel-title"><span class="pbadge" style="background:#7B3FAF">통합심사</span>MD11 Figure 1 — 통합수준 × 심사팀 자격비율</div>
    <div class="row2">
      <div class="field">
        <label>세로축 — 시스템 통합수준(%)</label>
        <select id="intg-level" onchange="calc()">
          <option value="0">0% — 병행 심사(통합 요소 없음)</option>
          <option value="20">20% — 일부 문서·회의 공유</option>
          <option value="40" selected>40% — 내부심사/방침·목표 일부 통합</option>
          <option value="60">60% — 대부분 통합(문서/개선체계 등)</option>
          <option value="80">80% — 거의 완전 통합</option>
          <option value="100">100% — 완전 통합경영시스템</option>
        </select>
        <div style="font-size:9px;color:var(--text3,#888);margin-top:3px">
          판단기준(MD11): 통합문서세트, 전사전략 반영 경영검토, 통합 내부심사, 통합 방침·목표, 통합 프로세스, 통합 개선체계, 통합 경영지원·책임 — 7개 충족정도로 인증기관이 판단
        </div>
      </div>
      <div class="field">
        <label>가로축 — 심사팀 다표준자격 비율(%) 자동계산</label>
        <div class="row2" style="gap:5px">
          <input type="number" id="intg-team-z" placeholder="심사원 수(Z)" min="1" value="1" oninput="calc()">
          <input type="number" id="intg-team-sumx" placeholder="자격표준수 합(ΣXi)" min="0" value="0" oninput="calc()">
        </div>
        <div id="intg-team-result" style="font-size:11px;color:var(--text2,#555);margin-top:4px">계산: -</div>
        <div style="font-size:9px;color:var(--text3,#888);margin-top:3px">
          공식(MD11): 100×Σ(Xᵢ-1)/(Z×(Y-1)), Xᵢ=심사원별 자격표준수, Y=통합대상 표준수, Z=심사원수
        </div>
      </div>
    </div>
    <div id="intg-reduction-result" style="font-size:12px;font-weight:700;color:#7B3FAF;margin-top:8px">예상 단축률: -</div>
  </div>
</div>

<!-- ── Step 2: 인증수행범위 ── -->
<div class="card">
  <div class="step">Step 2 — 인증수행범위</div>
  <div style="font-size:10px;color:var(--text3,#888);margin-bottom:5px">선택 표준에 따라 해당 패널이 표시됩니다</div>

  <!-- IAF 1~39 -->
  <div id="p-nace" class="panel">
    <div class="panel-title"><span class="pbadge">KSIC 코드</span>ISO 9001/14001/45001 복잡도 자동결정 (IAF코드_1 크로스워크 기준)</div>
    <div class="field">
      <label style="font-size:11px;color:var(--text2,#555);display:block;margin-bottom:4px">KSIC 코드 (기업정보 DB 값)</label>
      <input type="text" id="ksic-input" list="ksic-datalist" placeholder="예: 2011" oninput="onKsicChange()">
      <datalist id="ksic-datalist"></datalist>
    </div>
    <div class="nace-row" id="nace-badges"></div>
    <div id="ksic-match-info" style="font-size:11px;color:var(--text3,#888);margin-top:6px"></div>
  </div>

  <!-- ISO 13485 -->
  <div id="p-13485" class="panel" style="border-left-color:#C97820">
    <div class="panel-title"><span class="pbadge" style="background:#C97820">ISO 13485</span>의료기기 분류 (복수 선택)</div>
    <div id="md-list" style="display:grid;grid-template-columns:1fr 1fr;gap:3px;margin-bottom:8px"></div>
    <div class="sep"></div>
    <div class="row3" style="margin-top:6px">
      <div class="field"><label>제품 등급 (위험도)</label>
        <select id="md-risk" onchange="calc()">
          <option value="0">Class I — 저위험</option>
          <option value="1" selected>Class II — 중위험</option>
          <option value="2">Class III — 고위험</option>
          <option value="3">Class IV / 멸균 — 최고위험</option>
        </select>
      </div>
      <div class="field"><label>주요 제조 공정 수</label>
        <select id="md-proc" onchange="calc()">
          <option value="1">1~2개</option>
          <option value="2" selected>3~5개</option>
          <option value="3">6~10개</option>
          <option value="4">11개 이상</option>
        </select>
      </div>
      <div class="field"><label>규제 적용 지역</label>
        <select id="md-reg" onchange="calc()">
          <option value="1">단일 국가</option>
          <option value="2" selected>복수 (2~3개국)</option>
          <option value="3">글로벌 (4개국 이상)</option>
        </select>
      </div>
    </div>
  </div>

  <!-- ISO 22000 -->
  <div id="p-22000" class="panel" style="border-left-color:#27500A">
    <div class="panel-title"><span class="pbadge" style="background:#27500A">ISO 22000</span>식품사슬 범주 (ISO 22003-1:2022)</div>
    <div class="row2">
      <div class="field"><label>식품사슬 범주</label><select id="fsms-cat" onchange="updateFsmsTD();calc()"></select></div>
      <div class="field"><label>산정 기준 (자동)</label><div id="fsms-td-info" style="font-size:11px;padding:4px 0;color:var(--text2,#555)">—</div></div>
    </div>
    <div class="row3" style="margin-top:6px">
      <div class="field"><label>HACCP 연구 수</label><input type="number" id="haccp" value="1" min="0" max="20" oninput="validatePos(this);calc()"></div>
      <div class="field"><label>CCP 수</label><input type="number" id="ccp" value="5" min="0" max="50" oninput="validatePos(this);calc()"></div>
      <div class="field"><label>외주처리 비율</label>
        <select id="fsms-outsource" onchange="calc()">
          <option value="0">없음</option>
          <option value="1" selected>일부 (10~30%)</option>
          <option value="2">절반 이상 (30%+)</option>
        </select>
      </div>
    </div>
  </div>

  <!-- ISO 50001 -->
  <div id="p-50001" class="panel" style="border-left-color:#791F1F">
    <div class="panel-title"><span class="pbadge" style="background:#791F1F">ISO 50001</span>ISO 50003:2021 기반</div>
    <div class="row3">
      <div class="field"><label>연간 에너지 소비량 (TJ)</label><input type="number" id="en-tj" value="50" min="0" step="1" oninput="validatePos(this);calc()"></div>
      <div class="field"><label>SEU (주요에너지사용처) 수</label><input type="number" id="seu" value="3" min="0" max="30" oninput="validatePos(this);calc()"></div>
      <div class="field"><label>에너지원 복잡도</label>
        <select id="en-complexity" onchange="calc()">
          <option value="1">단순 — 단일 에너지원</option>
          <option value="2" selected>중간 — 2~3종</option>
          <option value="3">복잡 — 자가발전·재생에너지 포함</option>
        </select>
      </div>
    </div>
  </div>

  <!-- ISO 27001 -->
  <div id="p-27001" class="panel" style="border-left-color:#1a5276">
    <div class="panel-title"><span class="pbadge" style="background:#1a5276">ISO 27001</span>정보보안 — 시스템 기준</div>
    <div class="row3">
      <div class="field"><label>IT 사용자 수 (명)</label><input type="number" id="it-users" value="100" min="1" oninput="calc()"></div>
      <div class="field"><label>정보시스템 수</label>
        <select id="it-systems" onchange="calc()">
          <option value="1">1~5개</option>
          <option value="2" selected>6~15개</option>
          <option value="3">16~30개</option>
          <option value="4">31개 이상</option>
        </select>
      </div>
      <div class="field"><label>데이터 민감도</label>
        <select id="it-sensitivity" onchange="calc()">
          <option value="1">일반 내부 데이터</option>
          <option value="2" selected>고객·개인정보 포함</option>
          <option value="3">금융·의료·국가 기밀</option>
        </select>
      </div>
    </div>
  </div>

  <!-- ISO 19443 -->
  <div id="p-19443" class="panel">
    <div class="panel-title"><span class="pbadge">ISO 19443</span>핵연료 공급망 분류</div>
    <div class="field"><select id="nuclear-scope" onchange="calc()">
      <option value="A">A — 기계 및 구조물</option>
      <option value="B">B — 전자기기 및 계전기기</option>
      <option value="C">C — 핵연료</option>
      <option value="D">D — 발전 및 송전</option>
      <option value="E">E — 건설</option>
      <option value="F">F — 운송 및 폐기물 처리</option>
      <option value="G">G — 정보기술</option>
    </select></div>
  </div>

  <!-- 하부코드 없음 -->
  <div id="p-nocode" class="panel" style="border-left-color:#888">
    <div class="panel-title"><span class="pbadge" style="background:#888">IAF 1~39 공용</span>하부코드 없이 사용</div>
    <div style="font-size:11px;color:var(--text2,#555)">
      ISO 37001 / ISO 37301 / ISO 22301 / ISO/IEC 42001은 위 "IAF 1~39" 패널에서 선택한
      업종코드(KSIC 자동조회 결과)를 그대로 사용하며, 별도의 하부 세분류 코드는 적용하지 않습니다.
    </div>
  </div>

  <!-- ISO 27701 — PII 역할 (KAB-SR-PIMS 9.1.4 확정 공식의 필수 입력값) -->
  <div id="p-27701-pii" class="panel" style="border-left-color:#555">
    <div class="panel-title"><span class="pbadge" style="background:#555">ISO/IEC 27701</span>PII 역할 (27001 기준 가산율 결정)</div>
    <div class="field"><select id="pii-role" onchange="calc()">
      <option value="controller" selected>PII 컨트롤러 — 27001기준 +30% (최소 3일)</option>
      <option value="processor">PII 프로세서 — 27001기준 +20% (최소 2.5일)</option>
      <option value="both">컨트롤러+프로세서 둘 다 — 27001기준 +50% (최소 3.5일)</option>
    </select></div>
    <div style="font-size:10px;color:var(--text3,#888);margin-top:4px">KAB-SR-PIMS 9.1.4 확정 기준 — 기준값은 동일 범위 ISO/IEC 27001 계산결과</div>
  </div>
</div>

<!-- ── Step 3: 조직 정보 ── -->
<div class="card">
  <div class="step">Step 3 — 조직 기본 정보</div>
  <div class="row2" style="margin-bottom:9px">
    <div class="field"><label>유효 인원수 (명) *</label><input type="number" id="emp" value="50" min="1" oninput="validateEmp();calc()"></div>
    <div class="field"><label>심사 종류</label>
      <select id="atype" onchange="onSiteChange();calc()">
        <option value="initial">최초심사 (1단계+2단계)</option>
        <option value="surv6">사후관리심사 — 6개월 주기</option>
        <option value="surv12">사후관리심사 — 12개월 주기</option>
        <option value="recert">갱신인증심사</option>
        <option value="transfer_surv6">전환심사 — 사후(6개월) 시점</option>
        <option value="transfer_surv12">전환심사 — 사후(12개월) 시점</option>
        <option value="transfer_recert">전환심사 — 갱신 시점</option>
      </select>
    </div>
  </div>
  <div class="row2" style="margin-bottom:9px">
    <div class="field">
      <label>교대 근무 유형</label>
      <select id="shift-type" onchange="onShiftChange()">
        <option value="same">동일 인원 교대 (인원 그대로)</option>
        <option value="diff">다른 인원 교대 (총 인원 합산)</option>
      </select>
    </div>
    <div class="field" id="shift-cnt-wrap" style="display:none">
      <label>교대 수</label>
      <select id="shift-cnt" onchange="calc()">
        <option value="2">2교대</option>
        <option value="3">3교대</option>
      </select>
    </div>
  </div>
  <!-- 복수 사업장 -->
  <div class="sep"></div>
  <div class="sub-label">복수 사업장 (IAF MD1 6.1.3.3 — 심사유형별 공식 자동 적용)</div>
  <div class="row3">
    <div class="field"><label>총 사업장 수</label>
      <input type="number" id="site-total" value="1" min="1" oninput="onSiteChange();calc()">
    </div>
    <div class="field"><label>샘플 사업장 심사 비율</label>
      <select id="site-factor" onchange="calc()">
        <option value="0.5" selected>0.5 (50%) — 기본값 권장</option>
        <option value="0.6">0.6 (60%)</option>
        <option value="0.7">0.7 (70%)</option>
        <option value="0.8">0.8 (80%)</option>
      </select>
    </div>
    <div class="field"><label>샘플 사업장 수 (공식 자동)</label>
      <div id="site-sample-info" style="font-size:12px;padding:4px 0;color:var(--text2,#555)">해당없음</div>
    </div>
  </div>
  <div class="row3" style="margin-top:6px">
    <div class="field">
      <label>갱신심사 시스템 성숙도 (갱신심사에만 적용)</label>
      <select id="recert-mature" onchange="calc()">
        <option value="n" selected>일반 — y=√x</option>
        <option value="y">성숙(전 주기 효과적 운영 입증) — y=0.8√x</option>
      </select>
    </div>
  </div>
  <div style="font-size:10px;color:var(--text3,#888);margin-top:4px">
    최초/갱신심사: y=√x | 사후심사: y=0.6√x | 갱신심사(성숙): y=0.8√x — 전부 올림(ceil) 적용 (MD1 6.1.3.3)
  </div>
</div>

<!-- ── Step 4: 위험도 ── -->
<div class="card">
  <div class="step">Step 4 — 위험도 설정</div>
  <div style="font-size:10px;color:var(--text3,#888);margin-bottom:7px">인증수행범위 선택 시 기본값 자동 제안 → 직접 수정 가능</div>
  <div class="row3">
    <div class="field">
      <label>환경 위험도 (ISO 14001)</label>
      <select id="risk14" onchange="calc()">
        <option value="high">높음 — 화학·정유·조선·핵</option>
        <option value="med" selected>중간 — 제조·건설·운송</option>
        <option value="low">낮음 — 서비스·사무</option>
        <option value="restrict">제한 — 환경영향 최소</option>
      </select>
    </div>
    <div class="field">
      <label>안전보건 위험도 (ISO 45001)</label>
      <select id="risk45" onchange="calc()">
        <option value="high">높음 — 건설·금속·화학·조선</option>
        <option value="med" selected>중간 — 제조·운송·보건</option>
        <option value="low">낮음 — 서비스·IT·사무</option>
      </select>
    </div>
    <div class="field">
      <label>범용 복잡도 (9001 등)</label>
      <select id="complexity" onchange="calc()">
        <option value="high">높음 (+15%)</option>
        <option value="med" selected>중간 (±0%)</option>
        <option value="low">낮음 (-10%)</option>
      </select>
    </div>
  </div>
</div>

<!-- ── 결과 ── -->
<div class="card">
  <div style="font-size:13px;font-weight:700;margin-bottom:10px">산정 결과 (기본 MD)</div>
  <div class="res-grid">
    <div class="ri"><div class="rl">기준 심사일수</div><div class="rv info" id="r-base">-</div><div class="rs">M/D</div></div>
    <div class="ri"><div class="rl">가감 합계</div><div class="rv" id="r-adj">-</div><div class="rs">M/D</div></div>
    <div class="ri"><div class="rl">최종 심사일수</div><div class="rv" style="font-size:26px" id="r-final">-</div><div class="rs">M/D</div></div>
    <div class="ri"><div class="rl">권장 심사원</div><div class="rv" id="r-aud">-</div><div class="rs">명 (참고)</div></div>
  </div>
  <div id="alerts"></div>
  <!-- 최초심사 1단계/2단계 배분 가이드 -->
  <div id="stage-split" style="display:none;background:#f0f7ff;border:0.5px solid #185FA5;border-radius:7px;padding:10px 12px;margin-bottom:8px">
    <div style="font-size:11px;font-weight:700;color:#0C447C;margin-bottom:6px">📋 최초심사 1단계 / 2단계 배분</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
      <div style="background:#fff;border-radius:5px;padding:8px;text-align:center;border:0.5px solid #185FA5">
        <div style="font-size:10px;color:#555;margin-bottom:3px">1단계 — 문서심사 (20%)</div>
        <div style="font-size:20px;font-weight:700;color:#185FA5" id="stage1-days">-</div>
        <div style="font-size:9px;color:#888;margin-top:2px">M/D</div>
      </div>
      <div style="background:#fff;border-radius:5px;padding:8px;text-align:center;border:0.5px solid #27500A">
        <div style="font-size:10px;color:#555;margin-bottom:3px">2단계 — 현장심사 (80%)</div>
        <div style="font-size:20px;font-weight:700;color:#27500A" id="stage2-days">-</div>
        <div style="font-size:9px;color:#888;margin-top:2px">M/D</div>
      </div>
    </div>
  </div>
  <div id="log-table"></div>
</div>

<!-- ══════════════════════════════════════════════════ -->
<!-- 산정 근거 및 기준 안내 -->
<!-- ══════════════════════════════════════════════════ -->
<div class="card">
  <div style="font-size:15px;font-weight:800;margin-bottom:4px">📚 산정 근거 및 기준 안내</div>
  <div style="font-size:11px;color:var(--text3,#888);margin-bottom:16px">
    이 계산기가 사용하는 공식 근거·기준표를 공개합니다.
  </div>

  <div style="font-size:13px;font-weight:700;margin:16px 0 8px;padding-top:10px;border-top:1px solid var(--border,#e5e7eb)">
    ① IAF 1~39 복잡도 기준
  </div>
  <div id="guidance-complexity-table" style="overflow-x:auto"></div>

  <div style="font-size:13px;font-weight:700;margin:20px 0 8px;padding-top:14px;border-top:1px solid var(--border,#e5e7eb)">
    ② QMS·EMS·OHSMS 기본 MD 기준표
  </div>
  <div id="guidance-md5-table" style="overflow-x:auto"></div>

  <div style="margin-top:20px;padding-top:14px;border-top:1px solid var(--border,#e5e7eb)">
    <button type="button" id="guidance-standards-toggle" onclick="toggleGuidanceStandards()"
      style="background:none;border:1px solid var(--border,#e5e7eb);border-radius:8px;padding:8px 14px;font-size:12px;font-weight:700;cursor:pointer;color:var(--text2,#555)">
      ▼ 표준별 산출 요인 및 방식 보기
    </button>
    <div id="guidance-standards-box" style="display:none;margin-top:10px;overflow-x:auto">
      <div id="guidance-standards-table"></div>
    </div>
  </div>
</div>
</div>

<style>
.gtbl{width:100%;border-collapse:collapse;font-size:12px}
.gtbl th{background:var(--surface2,#f7f8fa);color:var(--text2,#555);font-weight:700;padding:6px 8px;text-align:center;border:1px solid var(--border,#e5e7eb);position:sticky;top:0}
.gtbl td{padding:6px 8px;text-align:center;border:1px solid var(--border,#e5e7eb)}
</style>

<script>const KAB_CONFIG = <?php echo md_calc_config_json(); ?>;</script>
<script src="/kab_audit_days.js"></script>
<script>initKabCalcEngine();</script>


<?php if (!empty($prefill)): ?>
<script>
window.PREFILL = <?= json_encode($prefill, JSON_UNESCAPED_UNICODE) ?>;
</script>
<?php endif; ?>
<!-- ── CB 포털 연동 ── -->
<script>
// URL 파라미터에서 기업 정보 자동 주입
(function() {
  const P      = window.PREFILL || {};
  const params = new URLSearchParams(window.location.search);
  const emp    = P.emp || params.get('emp');
  const stds   = P.stds || params.get('stds');     // 쉼표구분 표준코드
  const atype  = P.atype || params.get('atype');    // initial/followup/renewal
  const sites  = P.sites || params.get('sites');
  const ksic   = P.ksic || params.get('ksic');     // 기업정보 DB의 KSIC코드 (복잡도 판정 주 입력)
  const iaf    = P.iaf || params.get('iaf');       // 인증기관 기보유 IAF코드 (KSIC 매칭 실패시 참고용)
  const coName = P.co || params.get('co');
  const appId  = P.app_id || params.get('app_id');   // certification_applications.id — 검토서(cb_application_review.php)와 동일 키
  if (emp) {
    const empEl = document.getElementById('emp');
    if (empEl) { empEl.value = emp; }
  }
  if (atype) {
    const atEl = document.getElementById('atype');
    if (atEl) atEl.value = atype;
  }
  if (sites && parseInt(sites) > 1) {
    const siteEl = document.getElementById('site-total');
    if (siteEl) { siteEl.value = sites; onSiteChange && onSiteChange(); }
  }

  // 복잡도 판정 — KSIC코드가 주 입력값 (KSIC-IAF 크로스워크로 자동확정)
  if (ksic) {
    const ksicEl = document.getElementById('ksic-input');
    if (ksicEl) {
      ksicEl.value = ksic;
      onKsicChange && onKsicChange();
    }
  } else if (iaf) {
    // KSIC이 없을 때만 기존 보유 IAF코드를 참고용으로 표시 (복잡도 자동판정은 되지 않음 — 수동 확인 필요)
    const infoEl = document.getElementById('ksic-match-info');
    if (infoEl) infoEl.textContent = `⚠ KSIC코드가 없어 복잡도 자동판정이 불가합니다. 참고: 기존 보유 IAF코드 = ${iaf} (수동으로 KSIC 또는 복잡도를 확인하세요)`;
  }

  // 표준 자동 선택 — cfg().standards를 기준으로 정확히 매칭 (부분일치 금지)
  // 형식: "9001,14001" (심사유형 공통) 또는 "9001:surv12,14001:recert" (표준별 심사유형 지정)
  function resolveStdCode(token) {
    const clean = token.trim().toLowerCase()
      .replace(/iso\s*\/?\s*iec\s*/g, '').replace(/[^0-9a-z-]/g, '');
    const stds2 = cfg().standards;
    let hit = stds2.find(s => s.code.toLowerCase() === clean);
    if (hit) return hit.code;
    hit = stds2.find(s => (s.code.replace(/-\d{4}$/, '') + s.version_year) === clean);
    if (hit) return hit.code;
    const family = clean.replace(/(19|20)\d{2}$/, '');
    const candidates = stds2.filter(s => s.code.replace(/-\d{4}$/, '') === family);
    if (candidates.length) return (candidates.find(s => s.status === 'active') || candidates[0]).code;
    return null;
  }
  if (stds) {
    const pairs = stds.split(',').map(entry => {
      const [codeToken, atypeToken] = entry.split(':');
      return { code: resolveStdCode(codeToken), atype: atypeToken || null };
    }).filter(p => p.code);
    setTimeout(() => {
      if (pairs.length > 1 && typeof setMode === 'function') setMode('integrated');
      pairs.forEach(({ code }) => {
        const card = document.querySelector(`.scard[data-code="${code}"]`);
        if (card && !card.classList.contains('on')) card.click();
      });
      setTimeout(() => {
        pairs.forEach(({ code, atype }) => {
          if (atype && typeof setStdAtype === 'function') setStdAtype(code, atype);
        });
        calc && calc();
      }, 100);
    }, 300);
  }

  // 상단에 기업명 표시
  if (coName) {
    const title = document.createElement('div');
    title.style.cssText = 'background:#185FA5;color:#fff;padding:10px 16px;font-size:13px;font-weight:700;display:flex;justify-content:space-between;align-items:center';
    title.innerHTML = `🧮 MD 산정 — ${decodeURIComponent(coName)}
      <div style="display:flex;gap:8px">
        ${appId ? `<button onclick="saveMdResult('${appId}')" style="padding:5px 12px;background:#fff;color:#185FA5;border:none;border-radius:6px;font-size:12px;font-weight:700;cursor:pointer">💾 결과 저장</button>` : ''}
        <button onclick="window.close()" style="padding:5px 12px;background:rgba(255,255,255,.2);color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer">✕ 닫기</button>
      </div>`;
    document.body.insertBefore(title, document.body.firstChild);
  }

  // 결과 저장 함수 — certification_application_md_reviews.base_md로 저장 (검토서가 그대로 읽어감)
  window.saveMdResult = async function(applicationId) {
    const final = document.getElementById('r-final')?.textContent || '0';
    const fd = new FormData();
    fd.append('application_id', applicationId);
    fd.append('base_md', final);
    // 검토서 쪽 감사근거(왜 이 숫자가 나왔는지)를 위해 계산 상세를 그대로 첨부 — 필드 하나하나 나열하지 않고 구조 전체를 JSON으로
    fd.append('base_md_detail_json', JSON.stringify(window._lastCalcLog || {}));
    try {
      const r = await fetch('md_save_base.php', {method:'POST', body:fd});
      const j = await r.json();
      alert(j.ok ? `✅ 저장 완료! 기본 MD: ${final}일` : '저장 실패: ' + (j.msg||''));
      if (j.ok) window.close();
    } catch(e) {
      alert('저장 오류: ' + e.message);
    }
  };
})();
</script>
</body>
</html>
