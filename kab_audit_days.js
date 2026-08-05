
'use strict';

// ═══════════════════════════════════════════════════
// 데이터 계층 — 전부 KAB_CONFIG(md_calc_config.php/json, DB 연동 예정)에서 읽음
// 하드코딩된 표준별 배열은 이 파일에 없음. 값 갱신은 md_calc_config.json만 수정하면 됨.
// ═══════════════════════════════════════════════════
function cfg(){
  if (typeof KAB_CONFIG === 'undefined' || !KAB_CONFIG) {
    throw new Error('KAB_CONFIG가 로드되지 않았습니다. initKabCalcEngine() 호출 전에 설정을 주입하세요.');
  }
  return KAB_CONFIG;
}
const KAB_SURV6    = () => cfg().kab_ratios.surv6;
const KAB_SURV12   = () => cfg().kab_ratios.surv12;
const KAB_RECERT   = () => cfg().kab_ratios.recert;
const KAB_TRANSFER_ADD = () => cfg().kab_ratios.transfer_review_add; // 전환심사 시 이전 인증기관 이력검토 추가시간 (근거 미확정, 추정치)


// ═══ 상태 ═══
let mode='single';
let selStds=new Set(['9001']);
let stdAtypeOverrides={}; // 표준코드별 심사유형 override — 예: 9001=사후, 14001=갱신을 같은 신청서에서 동시에
function getAtypeFor(code){
  return stdAtypeOverrides[code] || g('atype')?.value || 'initial';
}
function setStdAtype(code, atype){
  if(!atype || atype==='__default__') delete stdAtypeOverrides[code];
  else stdAtypeOverrides[code]=atype;
  calc();
}
let selMdCats=new Set(['AI']);
// fv (Step5 가감요인 상태) 제거됨 — review.php로 이관

// ═══ 유틸 ═══
const r1=(v)=>Math.round(v*10)/10;
// 0.5 M/D 단위 반올림 (실무 표준 — 예: 3.2→3.5, 4.7→5.0)
const snap05=(v)=>Math.round(v*2)/2;
// 절대 최소 일수 (IAF MD5)
const FLOOR_INITIAL=1.0;   // 최초심사
const FLOOR_SURV=0.5;      // 사후심사

// ── KAB 기준표 룩업 — 표준 하나당 함수 하나씩 있던 lk9001/lk14001/lk45001을
//    표(md5_employee_table)와 표모양 정의(md5_table_schema)만 다르고 로직은 완전히 같으므로
//    함수 하나(lookupMD5Table)로 통일. 신규 MD5계열 표준 추가 시 config만 늘리면 됨(코드 변경 없음).
// 행 구조: [emp_min, (1단계,2단계)×카테고리수, 사후(카테고리수 또는 1개), 갱신(카테고리수 또는 1개)]
// ※ 9001은 원문(KAB-AR-MD5 Table QMS1)에 위험도 구분이 없는 단일 트랙임 — cx 입력은 무시됨.
function lookupMD5Table(stdCode, emp, cx){
  const map = cfg().md5_standard_map[stdCode];
  if(!map) throw new Error(`md5_standard_map에 ${stdCode} 정의가 없습니다`);
  const table  = cfg().md5_employee_table[map.table];
  const schema = cfg().md5_table_schema[map.table];

  let row = table[table.length-1];
  for(let i=0;i<table.length-1;i++){
    if(emp>=table[i][0] && emp<table[i+1][0]){ row=table[i]; break; }
  }

  const categories = schema.categories;
  let catIdx = categories.indexOf(cx);
  if(catIdx<0) catIdx = schema.survMode==='single' ? 0 : Math.min(1, categories.length-1); // 못 찾으면 '중간'격 항목으로 대체

  const st1 = row[schema.stageColBase + catIdx*2]   * map.multiplier;
  const st2 = row[schema.stageColBase + catIdx*2+1] * map.multiplier;
  const total = r1(st1+st2);

  let surv=null, recert=null;
  if(schema.survMode==='single'){
    surv   = row[schema.survColBase];
    recert = row[schema.recertColBase];
  } else if(schema.survMode==='per_category'){
    surv   = row[schema.survColBase + catIdx];
    recert = row[schema.recertColBase + catIdx];
  }

  return {
    total: r1(total), st1: r1(st1), st2: r1(st2),
    surv:  surv!=null  ? r1(surv*map.multiplier)  : null,
    recert:recert!=null? r1(recert*map.multiplier): null,
  };
}

const lk=(t,e)=>{for(const r of t)if(e>=r[0]&&e<=r[1])return r[2];return t[t.length-1][2];};
const g=(id)=>document.getElementById(id);
const gv=(id,def=0)=>parseFloat(g(id)?.value??def)||def;
const gi=(id,def=0)=>parseInt(g(id)?.value??def)||def;
const rL=(r)=>({high:'높음',med:'중간',low:'낮음',restrict:'제한'}[r]||'중간');
const cL=(c)=>({high:'복잡도 높음',med:'복잡도 중간',low:'복잡도 낮음'}[c]||'중간');

function validateEmp(){
  const el=g('emp');
  if(!el) return;
  if(parseInt(el.value)<=0||isNaN(parseInt(el.value))){
    el.value=1;
    alert('유효 인원수는 1명 이상이어야 합니다.');
  }
}
function validatePos(el){
  if(parseFloat(el.value)<0) el.value=0;
}

function getEmp(){
  const e=gi('emp',50);
  if(g('shift-type')?.value==='diff'){
    return e*(gi('shift-cnt',2));
  }
  return e;
}
function r14val(){return g('risk14')?.value||'med';}
function r45val(){return g('risk45')?.value||'med';}

// ═══════════════════════════════════════════════════
// 계산 함수 — 표준별 분리
// ═══════════════════════════════════════════════════

// MD5: ISO 9001 / 14001 / 45001 (2015·2026 버전 포함) — KAB 공식 기준표 적용
function CALC_MD5(code, empN){
  const log=[];
  const at=getAtypeFor(code);
  const cx=g('complexity')?.value||'med';
  const r14=r14val(), r45=r45val();

  const stdMeta=cfg().standards.find(s=>s.code===code);
  const family = code.startsWith('14001') ? '14001' : code.startsWith('45001') ? '45001' : '9001';

  let looked, stdLabel, cxLabel;
  if(family==='14001'){
    looked=lookupMD5Table(code, empN, r14);
    stdLabel=`${stdMeta?.full||code} KAB 기준표`;
    cxLabel=`환경위험: ${rL(r14)}`;
  } else if(family==='45001'){
    looked=lookupMD5Table(code, empN, r45);
    stdLabel=`${stdMeta?.full||code} KAB 기준표`;
    cxLabel=`안전위험: ${rL(r45)}`;
  } else {
    looked=lookupMD5Table(code, empN, 'single');
    stdLabel=`${stdMeta?.full||code} KAB 기준표`;
    cxLabel=`인원수 단일트랙(위험도 구분 없음, KAB-AR-MD5 Table QMS1 원문 기준)`;

    // QMS 고복잡도 가산 — 인증기관 정책값(config), KSIC 크로스워크로 이미 확정된 복잡도(cx) 기준 자동 적용
    // ※ 수동선택이 아니라 KSIC 결과를 그대로 씀 — 판단이 아니라 객관적 파생값이므로 여기서 적용해도 원칙 위반 아님
    const addon = cfg().qms_complexity_addon;
    if(addon?.enabled){
      const pct = cx==='high' ? addon.high_pct : cx==='low' ? addon.low_pct : addon.med_pct;
      if(pct){
        const mult = 1 + pct/100;
        const before = looked.total;
        looked = {
          total: r1(looked.total*mult), st1: r1(looked.st1*mult), st2: r1(looked.st2*mult),
          surv:  looked.surv!=null  ? r1(looked.surv*mult)  : null,
          recert:looked.recert!=null? r1(looked.recert*mult): null,
        };
        log.push([`QMS 고복잡도 가산 (인증기관 정책, 조정 가능)`,
          `KSIC 크로스워크 복잡도 '${cL(cx)}' → +${pct}%`, `${before}→${looked.total} M/D`]);
      }
    }
  }

  if(stdMeta?.status && stdMeta.status!=='active'){
    log.push([`⚠ ${stdMeta.full}`, stdMeta.note||'개정판 반영 전 — 기존판 산정표 잠정 적용', '잠정치']);
  }

  // ── STEP 1: 기준일수 (최초 기준)
  let baseInit=looked.total;
  log.push([`① 최초 기준일수 (${stdLabel})`,
    `${cxLabel} | 인원: ${empN}명 | 합계: ${baseInit} M/D (1단계 ${looked.st1} + 2단계 ${looked.st2})`,
    `${baseInit} M/D`]);

  // ── STEP 2: 심사유형 적용 — 반드시 최종 단계
  let base=baseInit;
  if(at==='surv6'){
    // 9001/45001: 사후 직접값 있는 경우 활용, 없으면 비율
    let survVal;
    if(looked.surv && looked.surv>0){
      survVal=r1(looked.surv*KAB_SURV6()/KAB_SURV12()); // SA6 = SA12 값의 2/3
    } else {
      survVal=r1(baseInit*KAB_SURV6());
    }
    base=survVal;
    log.push(['② 심사유형 — 사후관리(6개월)',`최초×${(KAB_SURV6()).toFixed(4)} (KAB 기준: 4/15)`,`${base} M/D`]);
  } else if(at==='surv12'){
    let survVal=looked.surv&&looked.surv>0 ? looked.surv : r1(baseInit*KAB_SURV12());
    base=survVal;
    log.push(['② 심사유형 — 사후관리(12개월)',`최초×${(KAB_SURV12()).toFixed(4)} (KAB 기준: 6/15)`,`${base} M/D`]);
  } else if(at==='recert'){
    let recertVal=looked.recert&&looked.recert>0 ? looked.recert : r1(baseInit*KAB_RECERT());
    base=recertVal;
    log.push(['② 심사유형 — 갱신인증',`최초×${(KAB_RECERT()).toFixed(4)} (KAB 기준: 8/15)`,`${base} M/D`]);
  } else if(at==='transfer_surv6'){
    let survVal;
    if(looked.surv && looked.surv>0){
      survVal=r1(looked.surv*KAB_SURV6()/KAB_SURV12());
    } else {
      survVal=r1(baseInit*KAB_SURV6());
    }
    base=r1(survVal+KAB_TRANSFER_ADD());
    log.push(['② 심사유형 — 전환심사(사후 6개월 시점)',
      `사후(6개월) ${survVal} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${base} M/D`]);
  } else if(at==='transfer_surv12'){
    let survVal=looked.surv&&looked.surv>0 ? looked.surv : r1(baseInit*KAB_SURV12());
    base=r1(survVal+KAB_TRANSFER_ADD());
    log.push(['② 심사유형 — 전환심사(사후 12개월 시점)',
      `사후(12개월) ${survVal} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${base} M/D`]);
  } else if(at==='transfer_recert'){
    let recertVal=looked.recert&&looked.recert>0 ? looked.recert : r1(baseInit*KAB_RECERT());
    base=r1(recertVal+KAB_TRANSFER_ADD());
    log.push(['② 심사유형 — 전환심사(갱신 시점)',
      `갱신 ${recertVal} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${base} M/D`]);
  } else {
    log.push(['② 심사유형 — 최초인증 (1단계+2단계)',
      `1단계 ${looked.st1} M/D + 2단계 ${looked.st2} M/D`,`${base} M/D`]);
  }
  return {base, log};
}
// FSMS: ISO 22000 — DS = TD + (HACCP수 × TH단가) + TFTE
// ※ MD5 기준표 미사용. CCP수 항목은 KAB-SR-FSMS 원문(부속서B, DS=TD+TH+TFTE)에 없어 제거함.
function CALC_FSMS(code, empN){
  const log=[];
  const catKey=g('fsms-cat')?.value||'CI';
  const cats=cfg().fsms_categories['22000'];
  const cat=cats.find(x=>x.k===catKey)||cats[1];

  const haccp=Math.max(0,gi('haccp',1));
  const outsource=gi('fsms-outsource',1);

  // STEP 1: TD — 식품체인 범주별 기본일수
  const td=cat.td;
  log.push(['TD — 식품사슬 범주 기본일수',`범주: ${cat.k}`,`${td} M/D`]);

  // STEP 2: TH — HACCP 연구 1건당 가산(범주별 단가: A/B계열 0.25, C0 이후 0.50 — KAB-SR-FSMS 표B.1)
  const th=r1(haccp*cat.th);
  log.push(['TH — HACCP 연구 가산',`${haccp}건 × ${cat.th} (범주 ${cat.k} 단가)`,`+${th} M/D`]);

  // STEP 3: TFTE (인원 기반, KAB-SR-FSMS 표B.1 전용 구간표)
  const tfte=empN<=5?0:empN<=49?0.5:empN<=99?1.0:empN<=199?1.5:empN<=499?2.0:empN<=999?2.5:3.0;
  log.push(['TFTE — 상근상당 종업원',`${empN}명`,`+${tfte} M/D`]);

  // STEP 4: 외주처리 보정 (참고: KAB-SR-FSMS 원문 DS=TD+TH+TFTE에는 없는 보조 조정 — 필요시 검토서 단계로 이관 검토)
  let outsourceAdj=0;
  if(outsource>0){
    outsourceAdj=outsource===1?0.25:0.5;
    log.push(['외주처리 비율 보정(보조)',`${['없음','일부(10~30%)','절반이상'][outsource]}`,`+${outsourceAdj} M/D`]);
  }

  let base=r1(td+th+tfte+outsourceAdj);
  log.push(['소계 (DS = TD + TH + TFTE, + 보조조정)','KAB-SR-FSMS 부속서B',`${base} M/D`]);
  return {base, log};
}

// EN50: ISO 50001
// TD(TJ기반) × SEU계수(1+SEU×0.05, max1.5) × 에너지복잡도계수
function CALC_EN50(code, empN){
  const log=[];
  const tj=Math.max(0,gv('en-tj',50));
  const seu=Math.max(0,gi('seu',3));
  const ec=gi('en-complexity',2);

  // STEP 1: TJ 기반 기본일수
  const td=tj<10?1.5:tj<50?2:tj<100?2.5:tj<500?3:tj<1000?3.5:tj<5000?4:tj<10000?5:6;
  log.push(['TD — 연간 에너지 소비량 기준',`${tj} TJ`,`${td} M/D`]);

  // STEP 2: SEU 계수 = 1 + min(SEU수 × 0.05, 0.5) — 상한 0.5 고정
  let seuFactor=1+Math.min(seu*0.05, 0.5);
  seuFactor=Math.round(seuFactor*100)/100;
  log.push(['SEU 계수','1 + min(SEU수×0.05, 0.5) — 상한 0.5 고정',`×${seuFactor}`]);

  // STEP 3: 에너지 복잡도 계수
  const ecFactor=ec===1?1.0:ec===2?1.1:1.2;
  log.push(['에너지복잡도 계수',`${['','단순','중간(2~3종)','복잡(자가발전포함)'][ec]}`,`×${ecFactor}`]);

  const base=r1(td*seuFactor*ecFactor);
  log.push(['소계','TD × SEU계수 × 복잡도계수',`${base} M/D`]);
  return {base, log};
}

// IS27: ISO 27001 — IT 사용자 수 기반
function CALC_IS27(code, empN){
  const log=[];
  const itUsers=Math.max(1,gi('it-users',100));
  const itSys=gi('it-systems',2);
  const itSens=gi('it-sensitivity',2);

  const base0=lk(cfg().is27_table, itUsers);
  log.push(['기본일수 (27001 IT사용자 기준표)',`IT 사용자: ${itUsers}명`,`${base0} M/D`]);

  const sysFactor=itSys===1?0.9:itSys===2?1.0:itSys===3?1.15:1.3;
  log.push(['정보시스템 수 계수',`${['','1~5개','6~15개','16~30개','31개+'][itSys]} ×${sysFactor}`,`×${sysFactor}`]);

  const sensFactor=itSens===1?0.9:itSens===2?1.0:1.2;
  log.push(['데이터 민감도 계수',`${['','일반내부','고객·개인정보','금융·의료·기밀'][itSens]} ×${sensFactor}`,`×${sensFactor}`]);

  const base=r1(base0*sysFactor*sensFactor);
  log.push(['소계','기본 × 시스템 × 민감도',`${base} M/D`]);
  return {base, log};
}

// MD13: ISO 13485
// 기준일수×1.15 × 제품등급계수(1+등급×0.2, max1.6) × 공정복잡도 × 규제지역 × 분류수
function CALC_MD13(code, empN){
  const log=[];
  const mdRisk=gi('md-risk',1); // 0~3
  const mdProc=gi('md-proc',2);
  const mdReg=gi('md-reg',2);
  const catCount=Math.max(1,selMdCats.size);

  const cx=g('complexity')?.value||'med';
  const base0=r1(lookupMD5Table('9001', empN, cx).total*1.15);
  log.push(['기본일수 (9001 KAB 기준표 × 1.15 의료기기 가중)',`인원: ${empN}명 (9001 Table QMS1은 위험도 구분 없는 단일트랙)`,`${base0} M/D`]);

  // STEP 2: 제품 등급 계수 = 1 + 등급 × 0.2, 최대 1.5
  let riskFactor=1+(mdRisk*0.2);
  if(riskFactor>1.5) riskFactor=1.5;
  riskFactor=Math.round(riskFactor*10)/10;
  const riskLabel=['Class I','Class II','Class III','Class IV/멸균'][mdRisk];
  log.push(['제품 등급 계수','1 + (등급 × 0.2), 최대 1.5',`${riskLabel} ×${riskFactor}`]);

  const procFactor=mdProc===1?0.9:mdProc===2?1.0:mdProc===3?1.15:1.3;
  log.push(['제조 공정 복잡도',`공정수 ${['','1~2개','3~5개','6~10개','11개+'][mdProc]} ×${procFactor}`,`×${procFactor}`]);

  const regFactor=mdReg===1?1.0:mdReg===2?1.1:1.25;
  log.push(['규제 적용 지역',`${['','단일국가','복수(2~3국)','글로벌(4국+)'][mdReg]} ×${regFactor}`,`×${regFactor}`]);

  const catAdj=r1(1+Math.min(catCount-1,5)*0.04);
  if(catCount>1) log.push(['의료기기 분류 수 보정',`${catCount}개 분류`,`×${catAdj}`]);

  const base=r1(base0*riskFactor*procFactor*regFactor*catAdj);
  log.push(['소계','기본 × 등급 × 공정 × 규제 × 분류수',`${base} M/D`]);
  return {base, log};
}

// GEN: 일반 표준 (9001 KAB 기준표 × 표준계수)
function CALC_GEN(code, empN){
  const log=[];
  const std=cfg().standards.find(s=>s.code===code);

  // 27701 — KAB-SR-PIMS 9.1.4 확정 공식: 27001 계산결과 기준 + PII 역할별 % 가산 (9001기준 아님)
  if(code==='27701' && std?.base_standard){
    const roleEl=g('pii-role');
    const role=roleEl?.value||'controller';
    const roleTable={controller:{pct:0.30,min:3}, processor:{pct:0.20,min:2.5}, both:{pct:0.50,min:3.5}};
    const r=roleTable[role]||roleTable.controller;

    const base27001=calcStd(std.base_standard, empN);
    log.push(...base27001.log.map(l=>[`[27001 기준] ${l[0]}`, l[1], l[2]]));

    let base=r1(base27001.base*(1+r.pct));
    log.push([`PII 역할 가산 (${role})`,`27001 기준 × (1+${r.pct})`,`${base} M/D`]);

    const at=getAtypeFor(code);
    if(at==='initial' && base<r.min){
      log.push(['최소일수 하한 (KAB-SR-PIMS)',`역할 '${role}' 최초심사 최소 ${r.min}일`,`→ ${r.min} M/D`]);
      base=r.min;
    }
    // 별도 심사(ISMS 사후/갱신과 분리 진행) 시 +0.5일 — 검토서 단계 판단 필요, 참고 로그만 표시
    log.push(['참고 — ISMS와 별도심사 시', 'PIMS 관점 확장 확인용 +0.5일 별도 고려 필요(KAB-SR-PIMS 9.1.4)', '수동 확인']);
    return {base, log};
  }

  // 나머지(37001/37301/22301/42001/19443) — 근거계수 확정 전, 9001기준 gf 잠정치
  const f=std?.gf||1.0;
  const cx=g('complexity')?.value||'med';
  const looked=lookupMD5Table('9001', empN, cx);
  const base0=looked.total;
  log.push(['기본일수 (ISO 9001 KAB 기준표, 잠정 기준)',`인원: ${empN}명 (9001 Table QMS1은 위험도 구분 없는 단일트랙)`,`${base0} M/D`]);
  const base=r1(base0*f);
  const statusNote = std?.coefficient_status==='unconfirmed' ? '근거 미확인 — 원문 확보 전 잠정치'
                    : std?.coefficient_status==='estimated'  ? '업계 추정치 — 공식 근거 미확정'
                    : '';
  if(f!==1) log.push(['표준 계수(잠정)',`×${f}${statusNote?' — '+statusNote:''}`,`${base} M/D`]);
  return {base, log};
}

// ═══════════════════════════════════════════════════
// 심사유형 적용 — MD5 이외의 표준(FSMS/EN50/IS27/MD13/GEN)용
// KAB 비율: SA6=4/15, SA12=6/15, RA=8/15
// ═══════════════════════════════════════════════════
function applyAuditType(base, log, code){
  const at=getAtypeFor(code);
  let result=base;
  if(at==='surv6'){
    result=r1(base*KAB_SURV6());
    log.push(['심사유형 — 사후관리(6개월)',`최초×4/15 (KAB 기준)`,`${result} M/D`]);
  } else if(at==='surv12'){
    result=r1(base*KAB_SURV12());
    log.push(['심사유형 — 사후관리(12개월)',`최초×6/15 (KAB 기준)`,`${result} M/D`]);
  } else if(at==='recert'){
    result=r1(base*KAB_RECERT());
    log.push(['심사유형 — 갱신인증',`최초×8/15 (KAB 기준)`,`${result} M/D`]);
  } else if(at==='transfer_surv6'){
    const survPart=r1(base*KAB_SURV6());
    result=r1(survPart+KAB_TRANSFER_ADD());
    log.push(['심사유형 — 전환심사(사후 6개월 시점)',
      `사후(6개월) ${survPart} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${result} M/D`]);
  } else if(at==='transfer_surv12'){
    const survPart=r1(base*KAB_SURV12());
    result=r1(survPart+KAB_TRANSFER_ADD());
    log.push(['심사유형 — 전환심사(사후 12개월 시점)',
      `사후(12개월) ${survPart} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${result} M/D`]);
  } else if(at==='transfer_recert'){
    const recertPart=r1(base*KAB_RECERT());
    result=r1(recertPart+KAB_TRANSFER_ADD());
    log.push(['심사유형 — 전환심사(갱신 시점)',
      `갱신 ${recertPart} M/D + 이전기관 이력검토 ${KAB_TRANSFER_ADD()} M/D(추정치)`, `${result} M/D`]);
  } else {
    log.push(['심사유형 — 최초인증','—',`${result} M/D`]);
  }
  return {result, log};
}

// 디스패처
const _calcStdVisiting = new Set(); // 재귀 순환 방지용 — base_standard 체인이 실수로 순환구조가 되어도 무한루프로 안 빠지게 함
function calcStd(code, empN){
  if(_calcStdVisiting.has(code)){
    console.error(`calcStd 순환 참조 감지: ${code} — base_standard 설정을 확인하세요.`);
    return {base:0, log:[['⚠ 순환 참조 오류', `${code} 계산 중 자기 자신 또는 상위 표준을 다시 참조함`, '0 M/D']], std:null};
  }
  _calcStdVisiting.add(code);
  try {
    const std=cfg().standards.find(s=>s.code===code);
    if(!std) return {base:0, log:[], std};
    let res;
    switch(std.type){
      case 'MD5':  res=CALC_MD5(code,empN); res.skipAuditType=true; break; // 심사유형 내부 처리
      case 'FSMS': res=CALC_FSMS(code,empN); break;
      case 'EN50': res=CALC_EN50(code,empN); break;
      case 'IS27': res=CALC_IS27(code,empN); break;
      case 'MD13': res=CALC_MD13(code,empN); break;
      case 'GEN':  res=CALC_GEN(code,empN);  break;
      default:     res={base:0,log:[]};
    }
    if(!res.skipAuditType){
      const {result, log}=applyAuditType(res.base, res.log, code);
      res.base=result; res.log=log;
    }
    return {base:res.base, log:res.log, std};
  } finally {
    _calcStdVisiting.delete(code);
  }
}

// ═══════════════════════════════════════════════════
// 복수사업장 (IAF MD1) — 본사 DS + 샘플(√n-1)개 × DS × siteFactor
// siteFactor: 사용자 선택 (기본 0.5)
// ═══════════════════════════════════════════════════
// 공용 헬퍼 — MD1 6.1.3.3 심사유형별 샘플 수 계산 (calcMultiSite 및 UI 미리보기에서 공유)
function multiSiteSampleCount(sites, atype, mature){
  if(sites<=1) return {sample:0, raw:0, label:''};
  let raw, label;
  if(atype==='surv6'||atype==='surv12'||atype==='transfer_surv6'||atype==='transfer_surv12'){
    raw=0.6*Math.sqrt(sites); label='0.6√x (사후)';
  } else if((atype==='recert'||atype==='transfer_recert')&&mature){
    raw=0.8*Math.sqrt(sites); label='0.8√x (갱신·성숙)';
  } else {
    raw=Math.sqrt(sites); label=((atype==='recert'||atype==='transfer_recert')?'√x (갱신)':'√x (최초)');
  }
  return {sample:Math.ceil(raw), raw, label};
}

// 복수사업장 (IAF MD1 6.1.3.3) — 심사유형별 공식 분리
// 최초심사: y=√x | 사후심사: y=0.6√x | 갱신심사: y=√x (성숙시 0.8√x 옵션)
function calcMultiSite(baseDay){
  const sites=gi('site-total',1);
  if(sites<=1) return {add:0, log:[]};
  const at=g('atype')?.value||'initial';
  const mature=g('recert-mature')?.value==='y'; // 갱신심사 성숙도 옵션

  const {sample, raw, label}=multiSiteSampleCount(sites, at, mature);
  const formulaLabel=`복수사업장 샘플링: y=${label} (MD1 6.1.3.3)`;
  // 사용자 선택 사이트 비율
  const siteFactor=parseFloat(g('site-factor')?.value||0.5);
  const siteDays=r1(baseDay*siteFactor);
  const extraSites=Math.max(0, sample-1);
  const add=r1(siteDays*extraSites);       // 추가분만 가산 (본사는 이미 포함)
  return {
    add,
    log:[[formulaLabel,
      `총 ${sites}개 → 샘플 ${sample}개 (계산값 ${r1(raw)}, 올림) | 본사 DS=${r1(baseDay)} + 추가 ${extraSites}개 × DS×${siteFactor}(${siteDays}M/D)`,
      `+${add} M/D`]]
  };
}

// ═══════════════════════════════════════════════════
// [제거됨] 가감요인(설계포함/범위제한/기존인증성숙도/통역/부적합이력/추가사업장복잡도)
// → 판단이 필요한 값이라 이 도구(기본MD 산출)가 아닌 인증신청검토서(review.php)에서
//   운영팀이 입력하도록 이관함 (IAF MD5 8절: "판단 사항은 정당화·기록되어야 한다")
// ═══════════════════════════════════════════════════

// ═══════════════════════════════════════════════════
// IAF MD11 2.1.2 + Figure 1 — 통합심사 감축률 2축 조회 방법론
// 세로축: 통합수준(%, CB 판단) / 가로축: 심사팀 다표준자격비율(%, 공식산출)
// ═══════════════════════════════════════════════════
const MD11_MATRIX = {
  100:{20:0, 40:5,  60:10, 80:15, 100:20},
  80: {20:0, 40:5,  60:10, 80:15, 100:15},
  60: {20:0, 40:5,  60:10, 80:10, 100:10},
  40: {20:0, 40:5,  60:5,  80:5,  100:5},
  20: {20:0, 40:0,  60:0,  80:0,  100:0},
  0:  {20:0, 40:0,  60:0,  80:0,  100:0},
};
function snapBucket20(v){
  const buckets=[0,20,40,60,80,100];
  let best=0, bd=Infinity;
  for(const b of buckets){ const d=Math.abs(v-b); if(d<bd){bd=d; best=b;} }
  return best;
}
// 심사팀 다표준자격비율(%) = 100×Σ(Xi-1)/(Z×(Y-1))
function calcTeamCapabilityPct(z, sumX, y){
  z=Math.max(1, z||1);
  y=Math.max(1, y||1);
  if(y<=1 || z<=0) return 0;
  const val=100*(sumX - z)/(z*(y-1));
  return Math.max(0, Math.min(100, val));
}
// (통합수준%, 능력%) → 감축률(0~0.20)
function md11ReductionRate(levelPct, capPct){
  const lvl=snapBucket20(levelPct);
  let cap=snapBucket20(capPct);
  if(cap===0) cap=20; // 표는 20부터 정의, 0~19는 20 컬럼(값 0)과 동일 취급
  const row=MD11_MATRIX[lvl]||MD11_MATRIX[0];
  return (row[cap]??0)/100;
}

// ═══════════════════════════════════════════════════
// 메인 calc()
// ═══════════════════════════════════════════════════
const ATYPE_LABEL={initial:'최초',surv6:'사후(6개월)',surv12:'사후(12개월)',recert:'갱신',
  transfer_surv6:'전환·사후(6개월)',transfer_surv12:'전환·사후(12개월)',transfer_recert:'전환·갱신'};
function calc(){
  updateScopePanels();
  const empN=getEmp();
  const maxPct=mode==='integrated'?20:30;
  const stdArr=[...selStds];
  const at=g('atype')?.value||'initial'; // 표준별 override가 없을 때 쓰는 기본값

  let rows=[], allLogs=[];
  let totalBase=0;

  stdArr.forEach((code)=>{
    const {base, log, std}=calcStd(code,empN);
    totalBase=r1(totalBase+base);
    const usedAtype=getAtypeFor(code);
    const label=`${std?.full||code} — ${ATYPE_LABEL[usedAtype]||usedAtype}`;
    rows.push({label, color:std?.color||'#555', net:base, intgCut:0, atype:usedAtype});
    allLogs.push({label, color:std?.color||'#555', log});
  });

  // ── 통합심사 감축 (IAF MD11 2.1.2 + Figure 1) — 표준별이 아닌 T=A+B+C 합계에 1회만 적용
  let intgReduction=0;
  if(mode==='integrated'&&stdArr.length>=2){
    const levelPct=parseFloat(g('intg-level')?.value||'0');
    const z=gi('intg-team-z',1);
    const sumX=gi('intg-team-sumx',0);
    const y=stdArr.length;
    const capPct=calcTeamCapabilityPct(z,sumX,y);
    const rate=md11ReductionRate(levelPct,capPct);
    intgReduction=r1(totalBase*rate);

    const teamResEl=g('intg-team-result');
    if(teamResEl) teamResEl.textContent=`계산: Y=${y}, Z=${z}, ΣXi=${sumX} → 능력비율 ${capPct.toFixed(1)}%`;
    const redResEl=g('intg-reduction-result');
    if(redResEl) redResEl.textContent=`예상 단축률: 통합수준 ${levelPct}% × 능력비율 ${capPct.toFixed(1)}% → ${(rate*100).toFixed(0)}% 단축 (-${intgReduction} M/D, 상한 20%)`;

    if(intgReduction>0){
      totalBase=r1(totalBase-intgReduction);
      allLogs.push({label:'통합심사 감축 (IAF MD11 Fig.1)', color:'#7B3FAF', log:[
        [`통합수준 ${levelPct}% × 팀능력비율 ${capPct.toFixed(1)}%`,
         `Figure 1 조회 → 단축률 ${(rate*100).toFixed(0)}% (T=Σ표준base 합계 ${r1(totalBase+intgReduction)} M/D 기준, 상한 20%)`,
         `-${intgReduction} M/D`]
      ]});
    }
  } else {
    const redResEl=g('intg-reduction-result');
    if(redResEl) redResEl.textContent = stdArr.length<2 ? '예상 단축률: 표준 2개 이상 선택 시 계산' : '예상 단축률: -';
  }

  // 복수사업장 가산
  const {add:siteAdd, log:siteLog}=calcMultiSite(totalBase);
  const totalWithSite=r1(totalBase+siteAdd);
  if(siteLog.length) allLogs.push({label:'복수사업장 (IAF MD1)', color:'#185FA5', log:siteLog});

  // ── 기본일수 기준 확정 (변동 제한의 기준값 — 가감 전)
  const baseDays=totalWithSite;

  // ── [제거됨] Step5 가감요인 합산 로직 — review.php로 이관 (변수는 하위 호환을 위해 0으로 유지)
  let adjFactor=0;
  let daysAdd=0;
  const adjLog=[];
  const maxF=maxPct/100;
  const adjFactorClamped=0;
  const pctOver=false;

  const adjDays=0;
  // 0.5 M/D 단위 반올림 (실무 표준)
  let final=snap05(baseDays);

  // ── 총 변동 범위 제한 — baseDays(기본일수, 가감 전) 기준으로 명확히 적용
  const limitMin=snap05(baseDays*0.7);
  const limitMax=snap05(baseDays*1.3);
  let limitApplied='';
  if(final<limitMin){ final=limitMin; limitApplied=`하한 (기준${baseDays}×0.7=${limitMin})`; }
  if(final>limitMax){ final=limitMax; limitApplied=`상한 (기준${baseDays}×1.3=${limitMax})`; }
  if(limitApplied){
    allLogs.push({label:'총 변동 범위 제한', color:'#854F0B', log:[
      ['변동 제한 기준값',`baseDays = ${baseDays} M/D (가감 적용 전 기준)`,`허용: ${limitMin}~${limitMax} M/D`],
      [limitApplied,'자동 조정',`→ ${final} M/D`]
    ]});
  }

  // ── 절대 최소 일수 Floor (IAF MD5) — 심사유형별 하한
  const isSurv=(at==='surv6'||at==='surv12'||at==='transfer_surv6'||at==='transfer_surv12');
  const floor=isSurv?FLOOR_SURV:FLOOR_INITIAL;
  let floorApplied=false;
  if(final<floor){ final=floor; floorApplied=true; }

  const audN=final<=3?1:final<=6?2:Math.ceil(final/4);
  const totalAdj=r1(adjDays+daysAdd);

  if(floorApplied){
    allLogs.push({label:'절대 최소 일수 (IAF MD5 Floor)', color:'#791F1F', log:[
      [`${isSurv?'사후심사':'최초심사'} 절대 최소 보장`,`IAF MD5 하한 ${floor} M/D`,`→ ${final} M/D`]
    ]});
  }

  // ── 구조화 로그 (인정심사 대응 — window._lastCalcLog로 접근 가능)
  window._lastCalcLog={
    timestamp:new Date().toISOString(),
    standards:[...selStds],
    perStandard:rows.map(r=>({label:r.label, atype:r.atype, md:r.net})),
    employees:empN,
    auditType:at,
    baseDays,
    adjFactor:Math.round(adjFactorClamped*100),
    adjDays,
    daysAdd,
    siteSampling:{
      total:gi('site-total',1),
      sample:multiSiteSampleCount(gi('site-total',1), at, g('recert-mature')?.value==='y').sample,
      factor:parseFloat(g('site-factor')?.value||0.5),
      add:siteAdd
    },
    integration:{mode, levelPct:g('intg-level')?.value||'0',
                 teamZ:gi('intg-team-z',1), teamSumX:gi('intg-team-sumx',0)},
    limitApplied,
    floor:{applied:floorApplied,value:floor},
    finalDays:final
  };

  // UI 업데이트
  g('r-base').textContent=baseDays.toFixed(1);
  g('r-adj').textContent=(totalAdj>=0?'+':'')+totalAdj.toFixed(1);
  g('r-final').textContent=final.toFixed(1);
  g('r-aud').textContent=audN+'명';

  // 1단계/2단계 배분 (최초심사에만 표시)
  const stageSplit=g('stage-split');
  if(at==='initial'){
    // MD5 표준이 단독 선택된 경우 KAB 기준표 ST1·ST2 실제값 표시
    const singleMd5=stdArr.length===1 && !!cfg().md5_standard_map[stdArr[0]];
    let s1, s2;
    if(singleMd5){
      const code=stdArr[0];
      const cx=g('complexity')?.value||'med';
      const r14=r14val(), r45=r45val();
      let looked;
      if(code.startsWith('14001')) looked=lookupMD5Table(code, empN, r14);
      else if(code.startsWith('45001')) looked=lookupMD5Table(code, empN, r45);
      else looked=lookupMD5Table(code, empN, cx);
      s1=snap05(looked.st1);
      s2=snap05(looked.st2);
    } else {
      // 복수 표준 또는 비MD5: 20/80 비율로 배분
      s1=snap05(final*0.2);
      s2=snap05(final*0.8);
    }
    g('stage1-days').textContent=s1.toFixed(1);
    g('stage2-days').textContent=s2.toFixed(1);
    stageSplit.style.display='block';
  } else {
    stageSplit.style.display='none';
  }

  // 알림
  let al='';
  if(mode==='integrated'&&stdArr.length<2) al+=`<div class="alert al-info">통합심사 모드 — 표준 2개 이상 선택 시 단축 적용</div>`;
  if(!limitApplied&&!floorApplied) al+=`<div class="alert al-ok">기본 심사일수(Base MD) 정상 산출 — 가감요인은 인증신청검토서에서 적용</div>`;
  if(limitApplied) al+=`<div class="alert al-warn">총 변동 범위 제한 (기준 ${baseDays} M/D): ${limitApplied} 적용</div>`;
  if(floorApplied) al+=`<div class="alert al-warn">절대 최소 일수 적용: ${isSurv?'사후':'최초'}심사 하한 ${floor} M/D (IAF MD5)</div>`;
  const totalSites=gi('site-total',1);
  if(totalSites>1){
    const ms=multiSiteSampleCount(totalSites, at, g('recert-mature')?.value==='y');
    al+=`<div class="alert al-info">복수사업장 ${totalSites}개 → 샘플 ${ms.sample}개 (MD1 6.1.3.3, y=${ms.label}) | 비율 ${g('site-factor')?.value||'0.5'} | 가산 +${siteAdd} M/D</div>`;
  }
  g('alerts').innerHTML=al;

  // 로그 테이블
  let t='';
  allLogs.forEach(({label,color,log:lg})=>{
    if(!lg.length) return;
    t+=`<table style="margin-bottom:6px">
      <thead>
        <tr><th colspan="3" style="background:${color}22;color:${color};border-bottom:1.5px solid ${color};padding:5px 8px">
          <span style="background:${color};color:#fff;padding:1px 6px;border-radius:3px;font-size:9px;font-weight:700;margin-right:5px">산정</span>${label}
        </th></tr>
        <tr><th style="width:42%">항목</th><th>내용</th><th style="text-align:right;width:80px">결과</th></tr>
      </thead><tbody>`;
    lg.forEach((row,i)=>{
      const isLast=i===lg.length-1;
      t+=`<tr class="${isLast?'tr-total':'tr-sub'}">
        <td>${row[0]}</td><td>${row[1]||'—'}</td>
        <td style="text-align:right">${row[2]||'—'}</td>
      </tr>`;
    });
    t+='</tbody></table>';
  });

  // 최종 요약
  t+=`<table><tbody>
    <tr class="tr-total"><td>기준일수 (가감 전 기준값)</td><td style="font-size:10px;color:#888">변동 범위 제한 기준</td><td style="text-align:right">${baseDays} M/D</td></tr>
    <tr class="tr-total"><td>가감 (${Math.round(adjFactorClamped*100)>0?'+':''}${Math.round(adjFactorClamped*100)}%${daysAdd>0?' + '+daysAdd+'일':''})</td><td style="font-size:10px;color:#888">단일 계수 1회 적용</td><td style="text-align:right">${totalAdj>=0?'+':''}${totalAdj.toFixed(1)} M/D</td></tr>
    <tr style="font-size:10px"><td colspan="3" style="padding:3px 8px;color:#888">↑ 0.5 M/D 단위 반올림 | 변동범위 ${baseDays}×0.7(${limitMin})~×1.3(${limitMax}) | Floor ${floor} M/D</td></tr>
    <tr class="tr-final"><td colspan="2" style="font-size:13px">🔖 최종 심사일수</td><td style="text-align:right;font-size:16px">${final.toFixed(1)} M/D</td></tr>
  </tbody></table>
  <div style="font-size:9px;color:#bbb;margin-top:4px;text-align:right">인정심사 대응 로그: 브라우저 콘솔 → window._lastCalcLog</div>`;
  g('log-table').innerHTML=t;
}

// ═══ UI 초기화 ═══
function initNace(){
  // 예전 39개 대분류 select(IAF 1~39 단순목록)는 제거 — KSIC 크로스워크(ksic_iaf_map)로 대체
  initKsicDatalist();
}
function initKsicDatalist(){
  const dl=g('ksic-datalist');
  if(!dl) return;
  const seen=new Set();
  const rows=cfg().ksic_iaf_map||[];
  let opts='';
  rows.forEach(r=>{
    if(seen.has(r.ksic)) return;
    seen.add(r.ksic);
    opts+=`<option value="${r.ksic}">${r.iaf_sub}</option>`;
  });
  dl.innerHTML=opts;
}
function initFsmsCats(){
  const s1=g('fsms-cat');
  s1.innerHTML=cfg().fsms_categories['22000'].map(c=>`<option value="${c.k}">${c.l}</option>`).join('');
  s1.value='CI';
  updateFsmsTD();
}
function updateFsmsTD(){
  const k=g('fsms-cat')?.value||'CI';
  const c=cfg().fsms_categories['22000'].find(x=>x.k===k)||cfg().fsms_categories['22000'][1];
  g('fsms-td-info').textContent=`TD=${c.td}일, TH=×${c.th}일/건 (범주별 단가, KAB-SR-FSMS 표B.1)`;
}
function initMdList(){
  g('md-list').innerHTML=cfg().md13_categories.map(c=>`
    <label style="display:flex;align-items:flex-start;gap:4px;font-size:10px;padding:2px 0;cursor:pointer">
      <input type="checkbox" value="${c.k}" ${selMdCats.has(c.k)?'checked':''} onchange="toggleMd('${c.k}')" style="margin-top:1px;flex-shrink:0">
      <span>${c.l}</span>
    </label>`).join('');
}
function toggleMd(k){
  if(selMdCats.has(k)) selMdCats.delete(k);
  else selMdCats.add(k);
  if(!selMdCats.size) selMdCats.add(k);
  calc();
}
function buildAtypeOptionsHtml(selectedValue){
  const src=g('atype');
  if(!src) return '';
  let html=`<option value="__default__"${!selectedValue?' selected':''}>심사유형: 공통 적용</option>`;
  [...src.options].forEach(o=>{
    html+=`<option value="${o.value}"${selectedValue===o.value?' selected':''}>${o.textContent}</option>`;
  });
  return html;
}
function initStds(){
  g('std-grid').innerHTML=cfg().standards.map(s=>{
    const on=selStds.has(s.code);
    const showOverride = on && mode==='integrated';
    const overrideBlock = showOverride ? `
      <div onclick="event.stopPropagation()" style="margin-top:6px">
        <select style="width:100%;font-size:10px;padding:3px 6px" onchange="setStdAtype('${s.code}', this.value)">
          ${buildAtypeOptionsHtml(stdAtypeOverrides[s.code])}
        </select>
      </div>` : '';
    return `<div class="scard${on?' on':''}" data-code="${s.code}" onclick="toggleStd('${s.code}')">
      <div style="display:flex;align-items:flex-start;justify-content:space-between">
        <div>
          <div class="sn"><span style="width:5px;height:5px;border-radius:50%;background:${s.color};display:inline-block;margin-right:3px;vertical-align:middle"></span>${s.name}</div>
          <div class="sc">${s.full}</div>
        </div>
        <div class="ck">${on?'✓':''}</div>
      </div>
      ${overrideBlock}
    </div>`;
  }).join('');
}
function toggleStd(code){
  if(mode==='single'){selStds.clear();selStds.add(code);}
  else{
    if(selStds.has(code)&&selStds.size>1){ selStds.delete(code); delete stdAtypeOverrides[code]; }
    else selStds.add(code);
  }
  initStds(); calc();
}
function setMode(m){
  mode=m;
  g('tab-s').classList.toggle('on',m==='single');
  g('tab-i').classList.toggle('on',m==='integrated');
  g('std-hint').textContent=m==='single'?'표준 1개 선택':'복수 표준 선택 — 통합심사 수준에 따라 단축';
  const intgPanelEl=g('intg-panel');
  intgPanelEl.className='panel'+(m==='integrated'?' show':'');
  intgPanelEl.style.display=''; // 인라인 display:none이 CSS .panel.show를 덮어쓰던 문제 제거 — 이후 클래스로만 표시 제어
  if(m==='single'&&selStds.size>1){const f=[...selStds][0];selStds.clear();selStds.add(f);}
  initStds(); calc();
}
function updateScopePanels(){
  const groups=new Set([...selStds].map(c=>cfg().standards.find(x=>x.code===c)?.scopeGroup||'iaf39_nosub'));
  const show=(id,on,bc)=>{
    const el=g(id); if(!el) return;
    el.className='panel'+(on?' show':'');
    if(on&&bc) el.style.borderLeftColor=bc;
  };
  show('p-nace',       groups.has('iaf39'));
  show('p-13485',      groups.has('13485'),'#C97820');
  show('p-22000',      groups.has('22000'),'#27500A');
  show('p-50001',      groups.has('50001'),'#791F1F');
  show('p-27001',      groups.has('27001'),'#1a5276');
  show('p-19443',      groups.has('19443'));
  show('p-nocode',     groups.has('iaf39_nosub'),'#888');
  show('p-27701-pii',  selStds.has('27701'));
  if(groups.has('22000')) updateFsmsTD();
}
function complexityKeyFromLabel(v){
  const m={'높음':'high','중간':'med','낮음':'low','제한':'restrict','특별':'special'};
  return m[v]||'med';
}
function onKsicChange(){
  const v=(g('ksic-input')?.value||'').trim();
  const infoEl=g('ksic-match-info');
  const match=(cfg().ksic_iaf_map||[]).find(r=>r.ksic===v);
  const complexityEl=g('complexity'), risk14El=g('risk14'), risk45El=g('risk45');

  if(!match){
    // 매칭 실패 — 수동 선택 허용 (잠금 해제)
    [complexityEl,risk14El,risk45El].forEach(el=>{ if(el) el.disabled=false; });
    g('nace-badges').innerHTML='';
    if(infoEl) infoEl.textContent = v ? '⚠ 등록된 KSIC코드가 아닙니다 — 복잡도를 수동으로 확인·선택하세요.' : '';
    calc();
    return;
  }

  // KSIC→IAF 크로스워크 결과로 복잡도 자동 결정 + 잠금 (임의 재선택 방지)
  const qKey=complexityKeyFromLabel(match.qms), eKey=complexityKeyFromLabel(match.ems), oKey=complexityKeyFromLabel(match.ohsms);
  if(complexityEl){ complexityEl.value=qKey; complexityEl.disabled=true; }
  if(risk14El){ risk14El.value=eKey; risk14El.disabled=true; }
  if(risk45El){ risk45El.value=oKey; risk45El.disabled=true; }

  g('nace-badges').innerHTML=[
    `<span class="cbadge ${qKey==='high'?'cb-h':qKey==='low'?'cb-l':'cb-m'}">품질 ${match.qms||'-'}</span>`,
    `<span class="cbadge ${eKey==='high'?'cb-h':eKey==='low'?'cb-l':eKey==='restrict'?'cb-i':'cb-m'}">환경 ${match.ems||'-'}</span>`,
    `<span class="cbadge ${oKey==='high'?'cb-h':oKey==='low'?'cb-l':'cb-m'}">안전 ${match.ohsms||'-'}</span>`,
  ].join('');
  if(infoEl){
    infoEl.textContent = `심사원배정 매칭코드: IAF ${match.iaf_main} (대분류만 사용, 세분류 불필요) · 복잡도 판정 참고 세분류: ${match.iaf_sub} — 복잡도는 KSIC 크로스워크로 자동확정, 재선택하려면 KSIC 코드를 변경하세요.` + (match.note ? ` [참고: ${match.note}]` : '');
  }
  calc();
}
function onShiftChange(){
  g('shift-cnt-wrap').style.display=g('shift-type')?.value==='diff'?'block':'none';
  calc();
}
function onSiteChange(){
  const total=gi('site-total',1);
  const at=g('atype')?.value||'initial';
  const mature=g('recert-mature')?.value==='y';
  if(total<=1){ g('site-sample-info').textContent='해당없음'; return; }
  const ms=multiSiteSampleCount(total, at, mature);
  g('site-sample-info').textContent=`${ms.sample}개 사업장 (y=${ms.label} → 올림, 계산값 ${r1(ms.raw)})`;
}

// ═══════════════════════════════════════════════════
// 엔진 진입점 — KAB_CONFIG가 준비된 뒤 이 함수를 호출해서 초기화한다.
// (kab_audit_days.php: PHP가 KAB_CONFIG를 동기 주입한 뒤 바로 호출 /
//  kab_audit_days_v8.html: fetch()로 KAB_CONFIG를 받은 뒤 호출)
// ═══════════════════════════════════════════════════
function initKabCalcEngine(){
  initNace();
  initFsmsCats();
  initMdList();
  initStds();
  onSiteChange();
  calc();
  initGuidancePanel();
  window.dispatchEvent(new CustomEvent('kab-engine-ready'));
}
if (typeof window !== 'undefined') window.initKabCalcEngine = initKabCalcEngine;

// ═══════════════════════════════════════════════════
// 산정 근거 및 기준 안내 패널
// ① IAF 1~39 복잡도 요약표 (세분류/수행범위 생략, 대분류 기준 통합)
// ② QMS·EMS·OHSMS 기본MD표 (원본 엑셀과 동일한 9001→14001→45001 구성)
// ③ 표준별 산출 요인 및 방식 (클릭 시에만 펼침)
// ═══════════════════════════════════════════════════
function renderGuidanceComplexityTable(){
  const rows=cfg().iaf39_summary||[];
  const groups=[];
  rows.forEach(r=>{
    const last=groups[groups.length-1];
    if(last && last.iaf===r.iaf) last.items.push(r);
    else groups.push({iaf:r.iaf, kr:r.kr, items:[r]});
  });

  let html = `<table class="gtbl"><thead><tr>
    <th>IAF코드</th><th>업종</th><th>KSIC코드</th><th>QMS(9001)</th><th>EMS(14001)</th><th>OHSMS(45001)</th>
  </tr></thead><tbody>`;
  groups.forEach(gr=>{
    gr.items.forEach((r,i)=>{
      const ksicText=(r.ksic||[]).join(', ');
      html += '<tr>';
      if(i===0){
        html += `<td rowspan="${gr.items.length}">${gr.iaf}</td>`;
        html += `<td rowspan="${gr.items.length}" style="text-align:left">${gr.kr||''}</td>`;
      }
      html += `<td style="text-align:left;font-size:10px;max-width:280px">${ksicText}</td>
        <td>${r.qms||'-'}</td><td>${r.ems||'-'}</td><td>${r.ohsms||'-'}</td></tr>`;
    });
  });
  return html + `</tbody></table>`;
}
const MD5_STD_LABEL = {'9001':'ISO 9001 (QMS)','14001':'ISO 14001 (EMS)','45001':'ISO 45001 (OHSMS)'};
function renderMd5TableFor(stdKey){
  const rows=cfg().md5_employee_table[stdKey]||[];
  const schema=cfg().md5_table_schema[stdKey];
  const cats=schema.categories;
  const catLabel={single:'',high:'높음',med:'중간',low:'낮음',restrict:'제한'};

  let head1 = `<th rowspan="2">인원기준</th>` + (cats[0]==='single'
    ? `<th colspan="2">최초심사</th><th rowspan="2">사후심사</th><th rowspan="2">갱신심사</th>`
    : cats.map(c=>`<th colspan="2">${catLabel[c]}</th>`).join('') + `<th colspan="${cats.length}">사후심사</th><th colspan="${cats.length}">갱신심사</th>`);
  let head2 = (cats[0]==='single'
    ? `<th>1단계 심사</th><th>2단계 심사</th>`
    : cats.map(()=>`<th>1단계 심사</th><th>2단계 심사</th>`).join('') + cats.map(c=>`<th>${catLabel[c]}</th>`).join('') + cats.map(c=>`<th>${catLabel[c]}</th>`).join(''));
  let html = `<table class="gtbl"><thead><tr>${head1}</tr><tr>${head2}</tr></thead><tbody>`;

  rows.forEach((r,i)=>{
    const next=rows[i+1];
    const rangeLabel = next ? `${r[0]}~${next[0]-1}명` : `${r[0]}명 이상`;
    let cells='';
    cats.forEach((c,ci)=>{
      cells += `<td>${r[schema.stageColBase+ci*2]}</td><td>${r[schema.stageColBase+ci*2+1]}</td>`;
    });
    if(schema.survMode==='single'){
      cells += `<td>${r[schema.survColBase]}</td><td>${r[schema.recertColBase]}</td>`;
    } else {
      cats.forEach((c,ci)=>{ cells += `<td>${r[schema.survColBase+ci]}</td>`; });
      cats.forEach((c,ci)=>{ cells += `<td>${r[schema.recertColBase+ci]}</td>`; });
    }
    html += `<tr><td>${rangeLabel}</td>${cells}</tr>`;
  });
  return html + `</tbody></table>`;
}
function renderGuidanceMd5Table(){
  return ['9001','14001','45001'].map(stdKey =>
    `<div style="font-size:12px;font-weight:700;margin:14px 0 6px">${MD5_STD_LABEL[stdKey]}</div>` +
    renderMd5TableFor(stdKey)
  ).join('');
}
function renderGuidanceStandardsTable(){
  const rows=cfg().guidance_standards||[];
  let html = `<table class="gtbl"><thead><tr>
    <th>표준</th><th>근거문서</th><th>산정 요인</th><th>산출 방식</th><th>확인상태</th>
  </tr></thead><tbody>`;
  rows.forEach(r=>{
    const statusColor = r.status.startsWith('확정') ? '#047a5a' : r.status.startsWith('잠정') ? '#c97820' : '#8a8f98';
    html += `<tr><td style="font-weight:700;white-space:nowrap">${r.code}</td>
      <td style="font-size:11px">${r.basis}</td>
      <td style="font-size:11px">${r.factors}</td>
      <td style="font-size:11px">${r.method}</td>
      <td style="font-size:11px;font-weight:700;color:${statusColor}">${r.status}</td></tr>`;
  });
  return html + `</tbody></table>`;
}
function toggleGuidanceStandards(){
  const box=g('guidance-standards-box');
  const btn=g('guidance-standards-toggle');
  if(!box) return;
  const show = box.style.display==='none';
  box.style.display = show?'block':'none';
  if(btn) btn.textContent = show ? '▲ 접기' : '▼ 표준별 산출 요인 및 방식 보기';
}
function initGuidancePanel(){
  const c1=g('guidance-complexity-table');
  const c2=g('guidance-md5-table');
  const c3=g('guidance-standards-table');
  if(c1) c1.innerHTML=renderGuidanceComplexityTable();
  if(c2) c2.innerHTML=renderGuidanceMd5Table();
  if(c3) c3.innerHTML=renderGuidanceStandardsTable();
}

