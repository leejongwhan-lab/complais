<?php
declare(strict_types=1);

require_once __DIR__ . '/config.php';

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_name(APP_INSTANCE . '_sid');
    session_start();
}

ini_set('display_errors', '1');
error_reporting(E_ALL);

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/helpers.php';
require_once __DIR__ . '/document_number_lib.php';
require_once __DIR__ . '/includes/standards_dropdown.php';

require_role(['cb', 'cb_admin', 'cb_staff', 'cb_manager', 'cb_reviewer', 'admin']);

if (!function_exists('app_review_calc_base_md')) {
    // 기본MD의 유일한 출처는 MD 산출기(kab_audit_days.php)다.
    // 산출기가 저장한 값(certification_application_md_reviews.base_md)이 있으면 그걸 그대로 쓰고,
    // 아직 계산이 안 된 신청서라면 그때만 예전 방식(인원수+표준수 단순계산)으로 잠정 표시한다.
    function app_review_calc_base_md(array $app, ?array $mdReview = null): ?float
    {
        if (!empty($mdReview['base_md']) && (float)$mdReview['base_md'] > 0) {
            return (float)$mdReview['base_md'];
        }
        $emp = (int)($app['employee_count'] ?? $app['total_count'] ?? 0);
        $base = md_base_by_employee_count($emp);
        if ($base === null) {
            return null;
        }
        $stdCount = md_standard_count_from_json($app['standards_json'] ?? '[]');
        $mode = (string)($app['audit_mode'] ?? 'single');
        return md_effective_from_base($base, $stdCount, $mode);
    }

    // 산출기 계산 여부(저장된 값이 있는지) — 화면에 "MD 계산기로 계산된 값"인지 "잠정치"인지 표시할 때 사용
    function app_review_base_md_is_calculated(?array $mdReview): bool
    {
        return !empty($mdReview['base_md']) && (float)$mdReview['base_md'] > 0;
    }

    function app_review_calc_adjustment_limit(array $app, ?float $baseMd): float
    {
        if ($baseMd === null || $baseMd <= 0) return 0.0;
        $ratio = ((string)($app['audit_mode'] ?? 'single') === 'integrated') ? 0.2 : 0.3;
        return md_round_half($baseMd * $ratio);
    }

    function app_review_adjustment_limit_percent(array $app): int
    {
        return ((string)($app['audit_mode'] ?? 'single') === 'integrated') ? 20 : 30;
    }

    function app_review_percent_to_md(?float $baseMd, int $percent): float
    {
        if ($baseMd === null || $baseMd <= 0 || $percent <= 0) return 0.0;
        return $baseMd * ($percent / 100);
    }

    function app_review_md_to_percent(?float $baseMd, float $md): int
    {
        if ($baseMd === null || $baseMd <= 0 || $md <= 0) return 0;
        return (int)(round((($md / $baseMd) * 100) / 5) * 5);
    }

    function app_review_normalize_percent(array $app, int $plusPct, int $minusPct): array
    {
        $limitPct = app_review_adjustment_limit_percent($app);
        $netPct = $plusPct - $minusPct;
        if ($netPct > $limitPct) {
            $plusPct = $minusPct + $limitPct;
        } elseif ($netPct < -$limitPct) {
            $minusPct = $plusPct + $limitPct;
        }
        return [$plusPct, $minusPct, $limitPct];
    }

    function app_review_normalize_adjustment(array $app, ?float $baseMd, float $plusMd, float $minusMd): array
    {
        $limit = app_review_calc_adjustment_limit($app, $baseMd);
        $net = $plusMd - $minusMd;
        if ($limit > 0) {
            if ($net > $limit) {
                $plusMd = $minusMd + $limit;
            } elseif ($net < -$limit) {
                $minusMd = $plusMd + $limit;
            }
        }
        return [$plusMd, $minusMd, $limit];
    }

    function app_review_calc_final_md(?float $baseMd, float $plusMd, float $minusMd): float
    {
        if ($baseMd === null || $baseMd <= 0) return 0.0;
        return md_round_half(max(0.0, $baseMd + $plusMd - $minusMd));
    }
}

$appId = (int)($_GET['id'] ?? $_POST['id'] ?? 0);
if ($appId <= 0) {
    http_response_code(400);
    echo '잘못된 요청입니다.';
    exit;
}

$app = db_one(
    $pdo,
    "SELECT a.*, c.name AS company_name, c.biz_no, c.ceo_name,
            c.name_en AS org_name_en, c.address, c.address_en,
            c.ksic_code, c.iaf_code, c.employee_count,
            cb.name AS cb_name
     FROM certification_applications a
     LEFT JOIN companies c ON c.id = a.company_id
     LEFT JOIN certification_bodies cb ON cb.id = a.cb_id
     WHERE a.id = ? LIMIT 1",
    [$appId]
);

if (empty($app)) {
    http_response_code(404);
    echo '신청서를 찾을 수 없습니다.';
    exit;
}

$standards = safe_json_decode($app['standards_json'] ?? null, []);
$appIafCodes = safe_json_decode($app['iaf_codes_json'] ?? null, []);
$questions = safe_json_decode($app['questionnaire_json'] ?? null, []);
$snapshot = safe_json_decode($app['company_snapshot_json'] ?? null, []);

$sites = table_exists($pdo, 'certification_application_sites')
    ? db_all($pdo, "SELECT * FROM certification_application_sites WHERE application_id = ? ORDER BY site_no ASC", [$appId])
    : [];

$answers = table_exists($pdo, 'certification_application_answers')
    ? db_all($pdo, "SELECT * FROM certification_application_answers WHERE application_id = ? ORDER BY standard_code ASC, question_key ASC", [$appId])
    : [];

$logs = table_exists($pdo, 'certification_application_review_logs')
    ? db_all($pdo, "SELECT * FROM certification_application_review_logs WHERE application_id = ? ORDER BY id DESC", [$appId])
    : [];

$mdReview = table_exists($pdo, 'certification_application_md_reviews')
    ? db_one($pdo, "SELECT * FROM certification_application_md_reviews WHERE application_id = ? LIMIT 1", [$appId])
    : [];

$status_kr = [
    'draft'        => '작성중',
    'submitted'    => '제출완료',
    'under_review' => '검토중',
    'need_fix'     => '보완요청',
    'approved'     => '승인',
    'rejected'     => '반려',
    'contracted'   => '계약완료',
    'withdrawn'    => '취소',
];
$status_badge = [
    'draft'        => ['#94A3B8','#F1F5F9'],
    'submitted'    => ['#2563EB','#EFF6FF'],
    'under_review' => ['#D97706','#FFFBEB'],
    'need_fix'     => ['#7C3AED','#F5F3FF'],
    'approved'     => ['#059669','#ECFDF5'],
    'rejected'     => ['#DC2626','#FEF2F2'],
    'contracted'   => ['#059669','#ECFDF5'],
    'withdrawn'    => ['#64748B','#F1F5F9'],
];
function review_standard_short_label(string $code, ?string $typeKey = null): string
{
    $base = std_doc_short_code($code);
    if ($typeKey === null || $typeKey === '') return $base;
    $suffixMap = [
        'initial'         => 'IA',
        'surveillance'    => 'SA1',
        'surveillance1'   => 'SA1',
        'surveillance_1'  => 'SA1',
        'surveillance2'   => 'SA2',
        'surveillance_2'  => 'SA2',
        'recertification' => 'RA',
        'special'         => 'SaP',
        'transfer'        => 'TA',
        'scope_extension' => 'SE',
    ];
    $suffix = $suffixMap[$typeKey] ?? '';
    if ($suffix === '') return $base;
    return preg_replace('/\([^)]+\)$/', '', $base) . '-' . $suffix;
}

$embed = isset($_GET['embed']) && (string)$_GET['embed'] === '1';

$notice = '';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = trim((string)($_POST['action'] ?? ''));
    $memo = trim((string)($_POST['memo'] ?? ''));
    $mdPlusPct = (int)($_POST['md_plus_pct'] ?? 0);
    $mdMinusPct = (int)($_POST['md_minus_pct'] ?? 0);
    $mdNote = trim((string)($_POST['md_note'] ?? ''));
    $mdBase = app_review_calc_base_md($app, $mdReview);
    [$mdPlusPct, $mdMinusPct, $mdAdjustLimitPct] = app_review_normalize_percent($app, $mdPlusPct, $mdMinusPct);
    $mdPlus = app_review_percent_to_md($mdBase, $mdPlusPct);
    $mdMinus = app_review_percent_to_md($mdBase, $mdMinusPct);
    [, , $mdAdjustLimit] = app_review_normalize_adjustment($app, $mdBase, $mdPlus, $mdMinus);
    $mdFinal = app_review_calc_final_md($mdBase, $mdPlus, $mdMinus);

    $allowed = [
        'under_review' => ['submitted'],
        'need_fix'     => ['submitted', 'under_review', 'need_fix'],
        'approved'     => ['under_review', 'need_fix'],
        'rejected'     => ['submitted', 'under_review', 'need_fix'],
    ];
    $before = (string)($app['status'] ?? '');
    $after  = $action;

    if ($action === 'save_md') {
        if ($mdBase === null) {
            $error = '기본 MD를 계산할 수 없습니다.';
        } else {
            try {
                $calcSummary = sprintf('기본 %.1f / 가산 %d%%(%.2f) / 감산 %d%%(%.2f) / 최종 %.1f', $mdBase, $mdPlusPct, $mdPlus, $mdMinusPct, $mdMinus, $mdFinal);
                $calcSummaryEsc = DB::esc($calcSummary);
                $mdNoteEsc = DB::esc($mdNote);
                $roleEsc = DB::esc((string)($_SESSION['user_role'] ?? 'cb_admin'));
                $uid = (int)($_SESSION['user_id'] ?? 0);

                if (table_exists($pdo, 'certification_application_md_reviews')) {
                    DB::exec("INSERT INTO certification_application_md_reviews
                        (application_id, base_md, add_md, subtract_md, final_md, calculation_note, reviewer_user_id, reviewer_role, reviewed_at)
                        VALUES ($appId, $mdBase, $mdPlus, $mdMinus, $mdFinal, '$mdNoteEsc', $uid, '$roleEsc', NOW())
                        ON DUPLICATE KEY UPDATE
                            base_md=VALUES(base_md),
                            add_md=VALUES(add_md),
                            subtract_md=VALUES(subtract_md),
                            final_md=VALUES(final_md),
                            calculation_note=VALUES(calculation_note),
                            reviewer_user_id=VALUES(reviewer_user_id),
                            reviewer_role=VALUES(reviewer_role),
                            reviewed_at=VALUES(reviewed_at)");
                }
                DB::exec("INSERT INTO certification_application_review_logs
                          (application_id, actor_user_id, actor_role, action, before_status, after_status, memo)
                          VALUES ($appId, $uid, '$roleEsc', 'md_save', '" . DB::esc($before) . "', '" . DB::esc($before) . "', '$calcSummaryEsc')");
                header('Location: cb_application_review.php?id=' . $appId . '&saved=1' . ($embed ? '&embed=1' : ''));
                exit;
            } catch (Throwable $e) {
                $error = 'MD 저장 실패: ' . $e->getMessage();
            }
        }
    } elseif (!isset($allowed[$action])) {
        $error = '허용되지 않은 동작입니다.';
    } elseif (!in_array($before, $allowed[$action], true)) {
        $error = '현재 상태(' . ($status_kr[$before] ?? $before) . ')에서는 해당 동작을 수행할 수 없습니다.';
    } elseif ($action === 'approved' && ($mdBase === null || $mdFinal <= 0)) {
        $error = '승인 전에 MD를 먼저 확정해 주세요.';
    } else {
        try {
            $uid        = (int)($_SESSION['user_id'] ?? 0);
            $after_esc  = DB::esc($after);
            $memo_esc   = DB::esc($memo);
            $role_esc   = DB::esc((string)($_SESSION['user_role'] ?? 'cb_admin'));
            $before_esc = DB::esc($before);
            $act_esc    = DB::esc($action);
            $mdSummary  = '';
            if ($mdBase !== null) {
                $mdSummary = sprintf('MD 기본 %.1f / 가산 %.1f / 감산 %.1f / 최종 %.1f', $mdBase, $mdPlus, $mdMinus, $mdFinal);
                if ($mdNote !== '') $mdSummary .= ' | ' . $mdNote;
            }
            $memoFinal  = trim($memo . ($mdSummary !== '' ? ($memo !== '' ? ' / ' : '') . $mdSummary : ''));
            $memoFinalE = DB::esc($memoFinal);

            // CB 인정범위 차단 체크 — 승인 시에만, CB에 범위가 등록된 경우만 검증
            if ($action === 'approved') {
                $_rAppCbId = (int)($app['cb_id'] ?? $cb_id);
                $_rStds    = json_decode($app['standards_json'] ?? '[]', true) ?: [];
                if ((bool)DB::val("SELECT COUNT(*) FROM cb_accreditation_scopes WHERE cb_id=$_rAppCbId AND is_active=1")) {
                    $_noScope = array_values(array_filter($_rStds, fn($s) => !cb_has_scope($_rAppCbId, (string)$s)));
                    if (!empty($_noScope)) {
                        throw new \RuntimeException('CB 인정범위 미포함 표준: ' . implode(', ', $_noScope) . ' — CB 정보 탭 › 인정정보 변경요청으로 먼저 등록하세요.');
                    }
                }
            }

            DB::exec("UPDATE certification_applications
                      SET status='$after_esc', reviewed_at=NOW(),
                          reviewed_by=$uid, review_note='$memoFinalE'
                      WHERE id=$appId");

            if ($after === 'approved' && empty($app['contract_id'])) {
                $appCbId   = (int)($app['cb_id'] ?? $cb_id);
                $appCoId   = (int)($app['company_id'] ?? 0);
                $appMode   = in_array((string)($app['audit_mode'] ?? 'single'), ['single', 'integrated'], true) ? (string)$app['audit_mode'] : 'single';
                $appAtype  = (string)($app['application_type'] ?? 'initial');
                $contractNo = (string)($app['application_no'] ?? '');
                if ($contractNo === '') {
                    $stdAbbr = doc_std_abbr_from_list(json_decode((string)($app['standards_json'] ?? '[]'), true) ?: []);
                    $contractNo = generate_contract_no(null, $appCbId, $appCoId, $stdAbbr, $appAtype);
                }
                $contractNoE = DB::esc($contractNo);
                $stdsJson = DB::esc((string)($app['standards_json'] ?? '[]'));
                $ps = !empty($app['desired_audit_start']) ? "'" . DB::esc((string)$app['desired_audit_start']) . "'" : 'NULL';
                $pe = !empty($app['desired_audit_end']) ? "'" . DB::esc((string)$app['desired_audit_end']) . "'" : 'NULL';
                $mdVal = (float)$mdFinal;
                $newContractId = DB::insert("INSERT INTO contracts
                    (contract_id, cb_id, company_id, audit_type, standards, audit_period_start, audit_period_end, audit_mode, total_md, agreed_amount, lead_auditor_id, status)
                    VALUES ('$contractNoE', $appCbId, $appCoId, '" . DB::esc($appAtype) . "', '$stdsJson', $ps, $pe, '" . DB::esc($appMode) . "', $mdVal, 0, NULL, 'draft')");
                if ($newContractId) {
                    DB::exec("UPDATE certification_applications SET contract_id=" . (int)$newContractId . " WHERE id=$appId");
                }
            }

            DB::exec("INSERT INTO certification_application_review_logs
                      (application_id, actor_user_id, actor_role, action,
                       before_status, after_status, memo)
                      VALUES ($appId, $uid, '$role_esc', '$act_esc',
                              '$before_esc', '$after_esc', '$memoFinalE')");

            if ($mdBase !== null && table_exists($pdo, 'certification_application_md_reviews')) {
                DB::exec("INSERT INTO certification_application_md_reviews
                    (application_id, base_md, add_md, subtract_md, final_md, calculation_note, reviewer_user_id, reviewer_role, reviewed_at)
                    VALUES ($appId, $mdBase, $mdPlus, $mdMinus, $mdFinal, '" . DB::esc($mdSummary) . "', $uid, '$role_esc', NOW())
                    ON DUPLICATE KEY UPDATE
                        base_md=VALUES(base_md),
                        add_md=VALUES(add_md),
                        subtract_md=VALUES(subtract_md),
                        final_md=VALUES(final_md),
                        calculation_note=VALUES(calculation_note),
                        reviewer_user_id=VALUES(reviewer_user_id),
                        reviewer_role=VALUES(reviewer_role),
                        reviewed_at=VALUES(reviewed_at)");
            }

            header('Location: cb_application_review.php?id=' . $appId . '&saved=1' . ($embed ? '&embed=1' : ''));
            exit;
        } catch (Throwable $e) {
            $error = '저장 실패: ' . $e->getMessage();
        }
    }
}

if (isset($_GET['saved'])) {
    $notice = '처리가 저장되었습니다.';
}

$standardsLabel = [];
$standardsDetail = []; // [{code, audit_type, audit_type_label}] — 표준마다 심사유형이 다를 수 있음
foreach ($standards as $code) {
    if (is_string($code)) {
        $standardsLabel[] = $code;
        $standardsDetail[] = ['code' => $code, 'audit_type' => (string)($app['audit_type'] ?? 'initial')];
    } elseif (is_array($code) && isset($code['code'])) {
        $standardsLabel[] = (string)$code['code'];
        $standardsDetail[] = ['code' => (string)$code['code'], 'audit_type' => (string)($code['audit_type'] ?? $app['audit_type'] ?? 'initial')];
    }
}

$cur_status  = $app['status'] ?? 'draft';
$can_start   = $cur_status === 'submitted';
$can_review  = in_array($cur_status, ['under_review', 'need_fix']);
$is_done     = in_array($cur_status, ['approved', 'rejected', 'contracted', 'withdrawn']);
[$st_clr, $st_bg] = $status_badge[$cur_status] ?? ['#94A3B8','#F1F5F9'];
$atype_kr = ['initial'=>'최초심사','surveillance'=>'사후심사','recertification'=>'갱신심사','scope_extension'=>'범위확대','transfer'=>'전환심사','special'=>'특별심사'];
foreach ($standardsDetail as &$sd) {
    $sd['audit_type_label'] = $atype_kr[$sd['audit_type']] ?? $sd['audit_type'];
}
unset($sd);
$reviewBaseMd = app_review_calc_base_md($app, $mdReview);
$reviewPlusMd = (float)($mdReview['add_md'] ?? 0);
$reviewMinusMd = (float)($mdReview['subtract_md'] ?? 0);
[$reviewPlusMd, $reviewMinusMd, $reviewAdjustLimit] = app_review_normalize_adjustment($app, $reviewBaseMd, $reviewPlusMd, $reviewMinusMd);
$reviewPlusPct = app_review_md_to_percent($reviewBaseMd, $reviewPlusMd);
$reviewMinusPct = app_review_md_to_percent($reviewBaseMd, $reviewMinusMd);
[$reviewPlusPct, $reviewMinusPct, $reviewAdjustLimitPct] = app_review_normalize_percent($app, $reviewPlusPct, $reviewMinusPct);
$reviewFinalMd = $reviewBaseMd !== null
    ? app_review_calc_final_md($reviewBaseMd, $reviewPlusMd, $reviewMinusMd)
    : 0.0;
$employeeView = (int)($app['employee_count'] ?? $snapshot['employee_count'] ?? 0);
$siteCountView = (int)($app['site_count'] ?? 0);
$workTypeView = (string)($app['work_type'] ?? '');
$desiredPeriodView = trim((string)($app['desired_audit_start'] ?? '')) !== ''
    ? substr((string)$app['desired_audit_start'], 0, 10) . (!empty($app['desired_audit_end']) ? ' ~ ' . substr((string)$app['desired_audit_end'], 0, 10) : '')
    : '—';
$appNoteView = trim((string)($app['note'] ?? ''));
$modeLabelView = (($app['audit_mode'] ?? 'single') === 'integrated') ? '통합' : '단일';
$appTypeLabelView = $atype_kr[$app['application_type'] ?? ''] ?? ($app['application_type'] ?? '');
$mdIncreaseFactors = [
    '공통' => [
        ['ref' => '추가요소 공통', 'label' => '현장이 2개 이상의 건물 또는 장소와 관련된 복잡한 물류인가?'],
        ['ref' => '추가요소 공통', 'label' => '2개 이상의 언어를 사용하는 직원이 포함되어 통역이 요구되는가?'],
        ['ref' => '2.1', 'label' => '종업원 수에 비하여 광범위한 사업장인가?'],
        ['ref' => '2.7', 'label' => '매우 복잡한 프로세스를 포함하거나 고유활동이 상대적으로 다수 포함된 시스템'],
        ['ref' => '3.4.1', 'label' => '임시사업장(건설현장 등)의 확인이 요구되는 경우 이동시간'],
        ['ref' => '2.8', 'label' => '외주처리하는 기능 또는 프로세스가 있는가? (있는 경우 이동시간)'],
        ['ref' => '고위험', 'label' => '높은 리스크에 해당하는 활동'],
    ],
    'EMS' => [
        ['ref' => '5.2.2', 'label' => '주변환경의 민감도가 높은 경우(특별대책지역이나 상수도 보호구역 등)인가?'],
        ['ref' => '5.2.2', 'label' => '이해관계자의 의견이 있는가?'],
        ['ref' => '5.2.2', 'label' => '심사시간의 증가를 필요로 하는 간접적인 측면'],
        ['ref' => '5.2.2', 'label' => '산업분야별 부가적/특이한 환경측면 또는 환경 허가/규제기관의 조건이 있는가?'],
        ['ref' => '5.2.2', 'label' => '환경사고나 영향이 증가되는 리스크(지리적, 계절적 요인 포함)가 있는가?'],
    ],
    'OH&S' => [
        ['ref' => '6.1', 'label' => '이해관계자의 견해'],
        ['ref' => '6.2', 'label' => '산업분야 평균보다 높은 사고 및 질병 발생률'],
        ['ref' => '6.3', 'label' => '일반 대중의 일원이 조직의 현장에 존재하는 경우'],
        ['ref' => '6.4', 'label' => '법적 소송에 처한 경우'],
        ['ref' => '6.5', 'label' => '다수의 협력사 및 관련 인원이 있는 경우'],
        ['ref' => '6.6', 'label' => '위험물질이 대량으로 존재하는 경우'],
        ['ref' => '6.7', 'label' => '모국 이외의 다른 국가에 사이트가 있는 경우'],
    ],
];
$mdDecreaseFactors = [
    '공통' => [
        ['ref' => '2.5 / 2.6', 'label' => '종업원 수에 비하여 매우 작은 사업장인가? (사무소만 있는 경우)'],
        ['ref' => '감소요소 공통', 'label' => '경영시스템 성숙도'],
        ['ref' => '감소요소 공통', 'label' => '경영시스템에 대한 사전지식(SMI의 타 경영시스템 인증 보유시)'],
        ['ref' => '감소요소 공통', 'label' => '경영체제 인증 준비상태(다른 인증을 유지하고 있는 경우)'],
        ['ref' => '저위험', 'label' => '낮은 리스크로 간주할 수 있는 활동(복잡도 낮음)'],
    ],
    'QMS' => [
        ['ref' => '2.5 / 2.6', 'label' => '다수의 종업원이 외근직이고 동일한 업무를 수행하며 기록을 통해 확인 가능한 경우'],
        ['ref' => '감소요소 QMS', 'label' => '높은 자동화 수준'],
    ],
    'EMS' => [
        ['ref' => '감소요소 EMS', 'label' => '다수의 종업원이 외근직이고 동일한 업무를 수행하며 기록을 통해 확인 가능한 경우'],
        ['ref' => '감소요소 EMS', 'label' => '높은 자동화 수준 및 낮은 환경적 중요성'],
    ],
];
$mdIntegratedFactors = [
    ['ref' => '통합수준', 'label' => '적절하게 개발된 업무지침 등을 포함한 통합 문서세트'],
    ['ref' => '통합수준', 'label' => '전체적인 사업전략 및 계획을 고려하는 경영검토'],
    ['ref' => '통합수준', 'label' => '내부심사 통합 접근'],
    ['ref' => '통합수준', 'label' => '방침 및 목표에 대한 통합 접근'],
    ['ref' => '통합수준', 'label' => '시스템 프로세스에 대한 통합 접근'],
    ['ref' => '통합수준', 'label' => '개선 메커니즘에 대한 통합 접근(시정조치, 개선)'],
    ['ref' => '통합수준', 'label' => '통합된 경영지원 및 지침'],
];
?>
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ComplAIs — 신청 검토</title>
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F0F4F8; --surface:#fff; --surface2:#F7F9FB; --border:#E3E8EF; --border2:#CBD5E1;
  --text:#0F172A; --text2:#334155; --text3:#64748B; --blue:#2563EB; --blue2:#EFF6FF;
  --green:#059669; --green2:#ECFDF5; --amber:#D97706; --amber2:#FFFBEB; --red:#DC2626; --red2:#FEF2F2;
  --shadow:0 1px 3px rgba(15,23,42,.08); --r:14px;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Pretendard',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
body.embed{background:#fff;min-height:auto}
a{text-decoration:none;color:inherit}
.wrap{max-width:1280px;margin:0 auto;padding:24px}
body.embed .wrap{max-width:none;padding:16px}
.header{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:18px}
.tt{font-size:24px;font-weight:800}
.sub{color:var(--text3);margin-top:4px;line-height:1.7}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--shadow);margin-bottom:16px;overflow:hidden}
.chd{padding:16px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.ctit{font-size:15px;font-weight:800}
.cb{padding:18px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.ff{display:flex;flex-direction:column;gap:5px}
.ff label{font-size:12px;font-weight:700;color:var(--text2)}
.ff input,.ff select,.ff textarea{width:100%;padding:12px 14px;border:1.5px solid var(--border2);border-radius:10px;font-size:14px;font-family:inherit;background:#fff;color:var(--text)}
.ff textarea{min-height:90px;resize:vertical;line-height:1.7}
.btn{display:inline-flex;align-items:center;justify-content:center;border:none;border-radius:10px;padding:12px 16px;font-size:14px;font-weight:800;cursor:pointer;background:var(--blue);color:#fff}
.btn:hover{background:#1D4ED8}
.btn-o{background:#fff;color:var(--text2);border:1px solid var(--border2)}
.note{padding:14px 16px;border-radius:10px;margin-bottom:14px;line-height:1.7}
.ok{background:var(--green2);border:1px solid var(--green);color:#14532D}
.err{background:var(--red2);border:1px solid var(--red);color:#7F1D1D}
.warn{background:var(--amber2);border:1px solid var(--amber);color:#7A4A00}
.badge{display:inline-flex;align-items:center;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:700}
.b1{background:var(--blue2);color:var(--blue)}
.b2{background:var(--green2);color:var(--green)}
.b3{background:var(--amber2);color:var(--amber)}
.b4{background:var(--red2);color:var(--red)}
.table{width:100%;border-collapse:collapse}
.table th,.table td{padding:10px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:left;vertical-align:top}
.table th{font-size:11px;color:var(--text3);background:var(--surface2)}
.small{font-size:12px;color:var(--text3);line-height:1.7}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}
.doc-shell{background:#fff;border:1px solid var(--border);border-radius:18px;box-shadow:var(--shadow);padding:34px 36px;margin-bottom:18px}
.doc-head{text-align:center;padding-bottom:18px;border-bottom:2px solid #0f172a;margin-bottom:22px}
.doc-title{font-size:32px;font-weight:900;letter-spacing:.22em;color:#111827}
.doc-meta{display:flex;justify-content:center;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:13px;color:var(--text3)}
.doc-meta strong{color:var(--text)}
.doc-intro{font-size:14px;line-height:1.8;color:var(--text2);margin-bottom:22px}
.doc-section{margin-bottom:22px}
.doc-section-title{font-size:16px;font-weight:900;color:#111827;padding-bottom:8px;border-bottom:1px solid var(--border2);margin-bottom:12px}
.doc-table{width:100%;border-collapse:collapse;font-size:13px}
.doc-table th,.doc-table td{border:1px solid var(--border);padding:10px 12px;vertical-align:top}
.doc-table th{width:168px;background:#F8FAFC;color:var(--text2);font-size:12px;font-weight:800;text-align:left}
.doc-table td{color:var(--text);line-height:1.75}
.doc-table td{word-break:break-word}
.doc-stds{display:flex;gap:8px;flex-wrap:wrap}
.doc-std-badge{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:var(--blue2);border:1px solid #BFDBFE;color:var(--blue);font-size:12px;font-weight:800}
.doc-grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.doc-box{border:1px solid var(--border);border-radius:14px;background:#FCFDFE;padding:14px 16px}
.doc-box-title{font-size:13px;font-weight:900;color:var(--text2);margin-bottom:8px}
.doc-kv{display:grid;grid-template-columns:120px 1fr;gap:8px 12px;font-size:13px;line-height:1.7}
.doc-kv div:nth-child(odd){font-weight:800;color:var(--text2)}
.doc-pre{white-space:pre-wrap;word-break:break-word}
.doc-table-wide{table-layout:fixed}
.doc-table-wide col:nth-child(1){width:18%}
.doc-table-wide col:nth-child(2){width:42%}
.doc-table-wide col:nth-child(3){width:40%}
.doc-table-sites{table-layout:fixed}
.doc-table-sites col:nth-child(1){width:22%}
.doc-table-sites col:nth-child(2){width:42%}
.doc-table-sites col:nth-child(3){width:20%}
.doc-table-sites col:nth-child(4){width:16%}
.md-review-grid{display:flex;flex-direction:column;gap:16px}
.md-panel{border:1px solid var(--border);border-radius:16px;background:#FBFCFE;padding:18px}
.md-panel-title{font-size:14px;font-weight:900;color:var(--text);margin-bottom:10px}
.md-panel-sub{font-size:12px;color:var(--text3);line-height:1.65;margin-bottom:12px}
.md-auto-box{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:22px 24px;border-radius:16px;background:linear-gradient(135deg,#EEF4FF,#F8FBFF);border:1px solid #BFDBFE}
.md-auto-val{font-size:34px;font-weight:900;line-height:1;color:var(--blue)}
.md-auto-unit{font-size:14px;font-weight:800;color:var(--text2)}
.md-summary-list{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:14px}
.md-summary-item{border:1px solid var(--border);border-radius:12px;background:#fff;padding:14px 12px;min-height:82px;display:flex;flex-direction:column;justify-content:center}
.md-summary-lbl{font-size:11px;font-weight:800;color:var(--text3);margin-bottom:6px}
.md-summary-val{font-size:15px;font-weight:900;color:var(--text)}
.md-adjust-grid{display:grid;grid-template-columns:1.1fr 1.1fr .9fr 1.4fr;gap:12px;align-items:stretch}
.md-select-box{border:1px solid var(--border);border-radius:14px;background:#fff;padding:14px;min-height:116px;display:flex;flex-direction:column;justify-content:center}
.md-select-box .ff{gap:6px}
.md-select-meta{font-size:12px;color:var(--text3);line-height:1.65}
.md-final-box{margin-top:16px;padding:18px 20px;border-radius:14px;background:#F8FAFC;border:1px dashed var(--border2);display:flex;align-items:center;justify-content:space-between;gap:12px}
.md-final-lbl{font-size:12px;font-weight:800;color:var(--text2)}
.md-final-val{font-size:28px;font-weight:900;color:var(--text)}
.md-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.md-note-help{margin-top:10px;font-size:12px;color:var(--text3);line-height:1.7}
.md-factor-wrap{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}
.md-factor-box{border:1px solid var(--border);border-radius:14px;background:#fff;padding:14px}
.md-factor-title{font-size:13px;font-weight:900;color:var(--text);margin-bottom:6px}
.md-factor-hint{font-size:11px;color:var(--text3);line-height:1.6;margin-bottom:10px}
.md-factor-list{display:flex;flex-direction:column;gap:8px}
.md-factor-item{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:start;padding:10px 0;border-top:1px dashed var(--border)}
.md-factor-item:first-child{border-top:none;padding-top:0}
.md-factor-text{font-size:12px;line-height:1.65;color:var(--text)}
.md-factor-meta{display:block;font-size:11px;font-weight:800;color:var(--blue);margin-bottom:2px}
.md-factor-btn{border:1px solid #BFDBFE;background:#EFF6FF;color:#1D4ED8;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:800;cursor:pointer;white-space:nowrap}
.md-factor-btn:hover{background:#DBEAFE}
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}.wrap{padding:16px}}
@media(max-width:900px){.doc-shell{padding:22px 16px}.doc-grid-2,.md-adjust-grid,.md-summary-list,.md-factor-wrap{grid-template-columns:1fr}.doc-kv{grid-template-columns:1fr}.doc-table th{width:120px}.doc-title{font-size:24px;letter-spacing:.08em}.doc-table-wide,.doc-table-sites{table-layout:auto}}
</style>
<link rel="stylesheet" href="complais_readability.css">
</head>
<body class="<?= $embed ? 'embed' : '' ?>">
<div class="wrap">
  <div class="header">
    <div>
      <div class="tt">신청 검토</div>
      <div class="sub">기업 신청 내용을 보고 검토, 보완요청, 승인, 반려를 처리합니다.</div>
    </div>
    <?php if (!$embed): ?>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <a class="btn btn-o" href="cb_portal.php?tab=applications">← 목록으로</a>
      <a class="btn btn-o" href="client_portal.php">기업포털</a>
    </div>
    <?php endif; ?>
  </div>

  <?php if ($notice): ?><div class="note ok"><?= h($notice) ?></div><?php endif; ?>
  <?php if ($error): ?><div class="note err"><?= h($error) ?></div><?php endif; ?>

  <div class="doc-shell">
    <div class="doc-head">
      <div class="doc-title">기업 인증신청검토서</div>
      <div class="doc-meta">
        <span>신청번호 <strong class="mono"><?= h((string)$app['application_no']) ?></strong></span>
        <span>인증기관 <strong><?= h((string)($app['cb_name'] ?? '—')) ?></strong></span>
        <span>현재상태 <strong style="color:<?= $st_clr ?>"><?= h($status_kr[$cur_status] ?? $cur_status) ?></strong></span>
      </div>
    </div>

    <div class="doc-intro">
      본 검토서는 기업 포털에서 제출한 인증신청 내용을 기준으로 작성되며, 신청 범위와 표준, 인원 및 사업장 조건, 희망 심사 일정과 특이사항을 검토하기 위한 문서입니다.
    </div>

    <div class="doc-section">
      <div class="doc-section-title">1. 신청 조직 기본정보</div>
      <table class="doc-table">
        <tr>
          <th>기업명</th>
          <td><?= h((string)($app['company_name'] ?? '')) ?></td>
          <th>대표자</th>
          <td><?= h((string)($app['ceo_name'] ?? '')) ?></td>
        </tr>
        <tr>
          <th>사업자등록번호</th>
          <td><?= h((string)($app['biz_no'] ?? '')) ?></td>
          <th>인증기관</th>
          <td><?= h((string)($app['cb_name'] ?? '')) ?></td>
        </tr>
        <tr>
          <th>주소</th>
          <td colspan="3"><?= h((string)($app['address'] ?? '')) ?></td>
        </tr>
        <tr>
          <th>영문 조직명</th>
          <td><?= h((string)($app['org_name_en'] ?? '')) ?></td>
          <th>영문 주소</th>
          <td><?= h((string)($app['address_en'] ?? '')) ?></td>
        </tr>
      </table>
    </div>

    <div class="doc-section">
      <div class="doc-section-title">2. 신청 내용</div>
      <div class="doc-grid-2">
        <div class="doc-box">
          <div class="doc-box-title">신청 조건</div>
          <div class="doc-kv">
            <div>신청유형</div><div><?= h($appTypeLabelView) ?></div>
            <div>심사형태</div><div><?= h($modeLabelView) ?></div>
            <div>직원수</div><div><?= h((string)$employeeView) ?>명</div>
            <div>사업장 수</div><div><?= h((string)$siteCountView) ?>개</div>
            <div>작업형태</div><div><?= h($workTypeView !== '' ? $workTypeView : '—') ?></div>
            <div>희망 심사일</div><div><?= h($desiredPeriodView) ?></div>
          </div>
        </div>
        <div class="doc-box">
          <div class="doc-box-title">분류 및 코드</div>
          <div class="doc-kv">
            <div>회사 IAF</div><div><?= h((string)($app['iaf_code'] ?? '')) ?></div>
            <div>신청 IAF</div><div><?= h(is_array($appIafCodes) ? implode(', ', $appIafCodes) : '—') ?></div>
            <div>KSIC 코드</div><div><?= h((string)($app['ksic_code'] ?? '')) ?></div>
            <div>비고</div><div class="doc-pre"><?= h($appNoteView !== '' ? $appNoteView : '—') ?></div>
          </div>
        </div>
      </div>
    </div>

    <div class="doc-section">
      <div class="doc-section-title">3. 신청 표준</div>
      <div class="doc-stds">
        <?php if (empty($standardsDetail)): ?>
          <span class="small">선택된 표준이 없습니다.</span>
        <?php else: ?>
          <?php foreach ($standardsDetail as $std): ?>
            <span class="doc-std-badge"><?= h($std['code']) ?> · <?= h($std['audit_type_label']) ?></span>
          <?php endforeach; ?>
        <?php endif; ?>
      </div>
    </div>

    <div class="doc-section">
      <div class="doc-section-title">4. 인증 범위</div>
      <table class="doc-table">
        <tr>
          <th>국문 인증범위</th>
          <td class="doc-pre"><?= h((string)($app['scope_kr'] ?? '')) ?></td>
        </tr>
        <tr>
          <th>영문 인증범위</th>
          <td class="doc-pre"><?= h((string)($app['scope_en'] ?? '')) ?></td>
        </tr>
      </table>
    </div>

    <div class="doc-section">
      <div class="doc-section-title">5. 사업장 정보</div>
      <table class="doc-table doc-table-sites">
        <colgroup>
          <col><col><col><col>
        </colgroup>
        <thead>
          <tr>
            <th>사업장명</th>
            <th>주소</th>
            <th>작업형태</th>
            <th>인원</th>
          </tr>
        </thead>
        <tbody>
          <?php if (empty($sites)): ?>
            <tr><td colspan="4">등록된 사업장 정보가 없습니다.</td></tr>
          <?php else: ?>
            <?php foreach ($sites as $site): ?>
            <tr>
              <td><?= h((string)($site['site_name'] ?? '')) ?></td>
              <td><?= h((string)($site['address_kr'] ?? '')) ?></td>
              <td><?= h((string)($site['work_type'] ?? '')) ?></td>
              <td><?= h((string)($site['total_count'] ?? '')) ?></td>
            </tr>
            <?php endforeach; ?>
          <?php endif; ?>
        </tbody>
      </table>
    </div>

    <div class="doc-section" style="margin-bottom:0">
      <div class="doc-section-title">6. 기업 포털 제출 응답</div>
      <table class="doc-table doc-table-wide">
        <colgroup>
          <col><col><col>
        </colgroup>
        <thead>
          <tr>
            <th>표준</th>
            <th>질문</th>
            <th>답변</th>
          </tr>
        </thead>
        <tbody>
          <?php if (empty($answers)): ?>
            <tr><td colspan="3">기업 포털 제출 응답이 없습니다.</td></tr>
          <?php else: ?>
            <?php foreach ($answers as $ans): ?>
            <tr>
              <td><?= h((string)($ans['standard_code'] ?? '')) ?></td>
              <td><?= h((string)($ans['answer_text'] ?? '')) ?></td>
              <td><?= h((string)($ans['answer_value'] ?? '')) ?></td>
            </tr>
            <?php endforeach; ?>
          <?php endif; ?>
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="chd">
      <div class="ctit">MD 검토</div>
      <div class="small">심사일수계산기 기준 기본 MD를 먼저 확인하고, 행정 검토에 따라 가산·감산만 조정합니다.</div>
    </div>
    <div class="cb">
      <input type="hidden" id="md-base-hidden" value="<?= h((string)($reviewBaseMd ?? 0)) ?>">
      <div class="md-review-grid">
        <div class="md-panel">
          <div class="md-panel-title">자동 산정 MD</div>
          <div class="md-panel-sub">기업이 제출한 신청 정보와 심사일수계산기 기준으로 자동 산정된 기본 MD입니다. 이 값은 직접 수정하지 않고, 아래 행정 가감 검토에서 비율만 선택합니다.</div>
          <div class="md-auto-box">
            <div>
              <div class="md-summary-lbl">기본 MD</div>
              <div><span class="md-auto-val" id="md-base-display"><?= h((string)($reviewBaseMd ?? 0)) ?></span> <span class="md-auto-unit">MD</span></div>
            </div>
            <div class="small" style="text-align:right">
              <?= h(($reviewBaseMd !== null ? '심사일수계산기 자동 산정' : '직원수 정보 없음')) ?>
            </div>
          </div>
          <input type="hidden" id="md-base" value="<?= h((string)($reviewBaseMd ?? 0)) ?>">
          <div class="md-summary-list">
            <div class="md-summary-item">
              <div class="md-summary-lbl">신청유형</div>
              <div class="md-summary-val"><?= h($appTypeLabelView) ?></div>
            </div>
            <div class="md-summary-item">
              <div class="md-summary-lbl">심사형태</div>
              <div class="md-summary-val"><?= h($modeLabelView) ?></div>
            </div>
            <div class="md-summary-item">
              <div class="md-summary-lbl">직원수</div>
              <div class="md-summary-val"><?= h((string)$employeeView) ?>명</div>
            </div>
            <div class="md-summary-item">
              <div class="md-summary-lbl">사업장 수</div>
              <div class="md-summary-val"><?= h((string)$siteCountView) ?>개</div>
            </div>
          </div>
        </div>
        <div class="md-panel">
          <div class="md-panel-title">행정 가감 검토</div>
          <div class="md-panel-sub">특이 사업장, 통합심사 조건, 제외 공정 등 행정 검토 사유가 있으면 가산·감산 비율을 선택합니다. IAF MD5:2019 §5.4 기준으로 가감요인은 합산 후 단일 적용하며, 최종 MD에서만 0.5 M/D 단위 반올림을 적용합니다.</div>
          <div class="md-adjust-grid">
            <div class="md-select-box">
              <div class="ff">
                <label>가산 비율</label>
                <select name="md_plus_pct" id="md-plus-pct" form="review-form" onchange="calcMdReview('plus')">
                  <?php foreach ([0, 5, 10, 15, 20, 25, 30] as $pct): ?>
                  <option value="<?= $pct ?>" <?= $reviewPlusPct === $pct ? 'selected' : '' ?>><?= $pct > 0 ? '+' . $pct : '0' ?>%</option>
                  <?php endforeach; ?>
                </select>
              </div>
            </div>
            <div class="md-select-box">
              <div class="ff">
                <label>감산 비율</label>
                <select name="md_minus_pct" id="md-minus-pct" form="review-form" onchange="calcMdReview('minus')">
                  <?php foreach ([0, 5, 10, 15, 20, 25, 30] as $pct): ?>
                  <option value="<?= $pct ?>" <?= $reviewMinusPct === $pct ? 'selected' : '' ?>><?= $pct > 0 ? '-' . $pct : '0' ?>%</option>
                  <?php endforeach; ?>
                </select>
              </div>
            </div>
            <div class="md-select-box">
              <div class="md-summary-lbl">순가감 한도</div>
              <div class="md-summary-val">±<?= h((string)$reviewAdjustLimitPct) ?>%</div>
              <div class="md-select-meta">기본 MD 기준 최대 <?= h((string)$reviewAdjustLimit) ?> M/D</div>
            </div>
            <div class="md-select-box">
              <div class="md-summary-lbl">현재 선택</div>
              <div class="md-summary-val" id="md-percent-summary">가산 <?= h((string)$reviewPlusPct) ?>% / 감산 <?= h((string)$reviewMinusPct) ?>%</div>
              <div class="md-select-meta">행정직원은 비율만 선택하면 최종 MD가 자동 계산됩니다.</div>
            </div>
          </div>
          <div class="ff" style="margin-top:12px">
            <label>가감 사유</label>
            <textarea name="md_note" id="md-note" form="review-form" placeholder="예: 다수 사업장 추가 가산&#10;단순 지원부서 제외 감산"><?= h((string)($mdReview['calculation_note'] ?? '')) ?></textarea>
          </div>
          <div class="md-factor-wrap">
            <div class="md-factor-box">
              <div class="md-factor-title">추가요소 인용</div>
              <div class="md-factor-hint">심사일수 산정 체크리스트의 추가요소를 검토한 뒤, 해당 항목을 클릭해 MD 가감 사유에 인용합니다.</div>
              <?php foreach ($mdIncreaseFactors as $group => $items): ?>
                <div class="md-factor-list" style="margin-top:10px">
                  <?php foreach ($items as $item): ?>
                  <div class="md-factor-item">
                    <div class="md-factor-text">
                      <span class="md-factor-meta"><?= h($group) ?> / <?= h($item['ref']) ?></span>
                      <?= h($item['label']) ?>
                    </div>
                    <button type="button" class="md-factor-btn" onclick="appendMdFactor('추가요소','<?= h($group) ?>','<?= h($item['ref']) ?>','<?= h($item['label']) ?>')">추가</button>
                  </div>
                  <?php endforeach; ?>
                </div>
              <?php endforeach; ?>
            </div>
            <div class="md-factor-box">
              <div class="md-factor-title">감소요소 인용</div>
              <div class="md-factor-hint">감소요소에 해당하는 경우 근거를 남겨 감산 사유를 표준 문구로 기록합니다.</div>
              <?php foreach ($mdDecreaseFactors as $group => $items): ?>
                <div class="md-factor-list" style="margin-top:10px">
                  <?php foreach ($items as $item): ?>
                  <div class="md-factor-item">
                    <div class="md-factor-text">
                      <span class="md-factor-meta"><?= h($group) ?> / <?= h($item['ref']) ?></span>
                      <?= h($item['label']) ?>
                    </div>
                    <button type="button" class="md-factor-btn" onclick="appendMdFactor('감소요소','<?= h($group) ?>','<?= h($item['ref']) ?>','<?= h($item['label']) ?>')">추가</button>
                  </div>
                  <?php endforeach; ?>
                </div>
              <?php endforeach; ?>
              <?php if (($app['audit_mode'] ?? 'single') === 'integrated'): ?>
              <div class="md-factor-title" style="margin-top:14px">통합심사 참고요소</div>
              <div class="md-factor-hint">통합심사 시 통합수준 판단 근거를 함께 남기면 MD 가감 검토 이력이 명확해집니다.</div>
              <div class="md-factor-list">
                <?php foreach ($mdIntegratedFactors as $item): ?>
                <div class="md-factor-item">
                  <div class="md-factor-text">
                    <span class="md-factor-meta"><?= h($item['ref']) ?></span>
                    <?= h($item['label']) ?>
                  </div>
                  <button type="button" class="md-factor-btn" onclick="appendMdFactor('통합심사','통합수준','<?= h($item['ref']) ?>','<?= h($item['label']) ?>')">추가</button>
                </div>
                <?php endforeach; ?>
              </div>
              <?php endif; ?>
            </div>
          </div>
          <div class="md-final-box">
            <div>
              <div class="md-final-lbl">최종 MD</div>
              <div class="small">기본 MD + 가산 MD - 감산 MD</div>
            </div>
            <div><span class="md-final-val" id="md-final-display"><?= h((string)$reviewFinalMd) ?></span> <span class="md-auto-unit">MD</span></div>
          </div>
          <input type="hidden" id="md-final" name="md_final" form="review-form" value="<?= h((string)$reviewFinalMd) ?>">
          <div class="md-actions">
            <button type="submit" form="review-form" onclick="return doAction('save_md')" class="btn" style="padding:11px 18px;background:#334155">
              💾 MD 저장
            </button>
          </div>
          <div class="md-note-help">
            MD를 먼저 저장한 뒤 `검토 시작`, `승인 및 MD 확정`, `보완 요청`, `반려` 단계로 이어서 진행하면 됩니다.
          </div>
          <?php if (!app_review_base_md_is_calculated($mdReview)): ?>
          <div class="note" style="background:#FFF5E0;border-color:#C97820;color:#7A4A0E;margin-top:10px">
            ⚠ 이 신청서는 아직 MD 계산기로 계산되지 않아 잠정치가 표시되고 있습니다. 아래 버튼으로 계산기를 열어 정식으로 계산·저장하세요.
          </div>
          <?php endif; ?>
          <?php
            // 신청서의 심사유형 표기(surveillance/recertification 등)를 계산기 내부 코드(surv12/recert 등)로 변환
            $calcAtypeMap = ['initial'=>'initial','surveillance'=>'surv12','recertification'=>'recert','special'=>'initial','transfer'=>'transfer_surv12','scope_extension'=>'initial'];
            $stdsParam = implode(',', array_map(
                fn($sd) => $sd['code'] . ':' . ($calcAtypeMap[$sd['audit_type']] ?? 'initial'),
                $standardsDetail
            ));
            $mdCalcUrl = 'kab_audit_days.php?' . http_build_query([
                'app_id' => $appId,
                'co'     => $app['company_name'] ?? '',
                'emp'    => $app['employee_count'] ?? '',
                'stds'   => $stdsParam,
                'sites'  => count($sites) ?: 1,
                'ksic'   => $app['ksic_code'] ?? '',
                'iaf'    => $app['iaf_code'] ?? '',
            ]);
          ?>
          <a href="<?= h($mdCalcUrl) ?>" target="_blank" rel="noopener"
             style="display:inline-flex;align-items:center;gap:6px;margin-top:10px;padding:9px 18px;border-radius:8px;background:#185FA5;color:#fff;font-size:13px;font-weight:700;text-decoration:none">
            🧮 MD 계산기 <?= app_review_base_md_is_calculated($mdReview) ? '재계산' : '열기' ?> →
          </a>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="chd">
      <div class="ctit">검토 처리</div>
      <span style="font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px;background:<?= $st_bg ?>;color:<?= $st_clr ?>">
        <?= $status_kr[$cur_status] ?? $cur_status ?>
      </span>
    </div>
    <div class="cb">
      <?php if (!$is_done): ?>
      <form method="post" id="review-form">
        <input type="hidden" name="id" value="<?= (int)$appId ?>">
        <?php if ($embed): ?>
        <input type="hidden" name="embed" value="1">
        <?php endif; ?>
        <input type="hidden" name="action" id="review-action" value="">
        <div class="ff" style="margin-bottom:16px">
          <label>메모 (선택 — 반려·보완 시 사유 입력 권장)</label>
          <input type="text" name="memo" id="review-memo" placeholder="예: 사업장 수 확인 필요, 범위 재검토 요청">
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="submit" onclick="return doAction('save_md')"
            style="padding:10px 20px;border-radius:8px;border:none;background:#334155;color:#fff;font-size:14px;font-weight:700;cursor:pointer">
            💾 MD 저장
          </button>
          <?php if ($can_start): ?>
          <button type="submit" onclick="return doAction('under_review')"
            style="padding:10px 20px;border-radius:8px;border:none;background:#D97706;color:#fff;font-size:14px;font-weight:700;cursor:pointer">
            🔍 검토 시작
          </button>
          <?php endif; ?>
          <?php if ($can_review): ?>
          <button type="submit" onclick="return doAction('approved')"
            style="padding:10px 20px;border-radius:8px;border:none;background:#059669;color:#fff;font-size:14px;font-weight:700;cursor:pointer">
            ✅ 승인 및 MD 확정
          </button>
          <button type="submit" onclick="return doAction('need_fix')"
            style="padding:10px 20px;border-radius:8px;border:none;background:#7C3AED;color:#fff;font-size:14px;font-weight:700;cursor:pointer">
            📋 보완 요청
          </button>
          <button type="submit" onclick="return doAction('rejected')"
            style="padding:10px 20px;border-radius:8px;border:none;background:#DC2626;color:#fff;font-size:14px;font-weight:700;cursor:pointer">
            ❌ 반려
          </button>
          <?php endif; ?>
        </div>
      </form>
      <?php else: ?>
      <div class="note ok" style="background:<?= $st_bg ?>;border-color:<?= $st_clr ?>;color:<?= $st_clr ?>">
        이 신청은 <strong><?= $status_kr[$cur_status] ?? $cur_status ?></strong> 상태입니다.
        <?php if ($cur_status === 'approved'): ?>처리 완료 — 아래에서 다음 단계를 진행하세요.<?php endif; ?>
      </div>
      <?php endif; ?>

      <?php if ($cur_status === 'approved'): ?>
      <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border);display:flex;gap:10px;flex-wrap:wrap;align-items:center">
        <span style="font-size:13px;font-weight:700;color:var(--text2)">다음 단계:</span>
        <a href="cb_portal.php?tab=proposal&app_id=<?= (int)$appId ?>&auto_audit_days=<?= h((string)$reviewFinalMd) ?>"
           style="display:inline-flex;align-items:center;gap:6px;padding:11px 22px;border-radius:8px;background:#7C3AED;color:#fff;font-size:14px;font-weight:700;text-decoration:none;box-shadow:0 2px 8px rgba(124,58,237,.3)">
          📄 제안서 작성 →
        </a>
        <a href="cb_auditor_assignment.php?app_id=<?= (int)$appId ?>"
           style="display:inline-flex;align-items:center;gap:6px;padding:11px 22px;border-radius:8px;background:#2563EB;color:#fff;font-size:14px;font-weight:700;text-decoration:none">
          👤 심사원 배정 →
        </a>
      </div>
      <?php endif; ?>
    </div>
  </div>

  <div class="card">
    <div class="chd"><div class="ctit">처리 이력</div></div>
    <div class="cb" style="padding:0">
      <table class="table">
        <thead><tr><th>시간</th><th>행위자</th><th>동작</th><th>상태</th><th>메모</th></tr></thead>
        <tbody>
          <?php if (empty($logs)): ?>
            <tr><td colspan="5" class="small" style="padding:16px">이력이 없습니다.</td></tr>
          <?php else: ?>
            <?php foreach ($logs as $log): ?>
              <tr>
                <td><?= h(substr((string)($log['created_at'] ?? ''), 0, 19)) ?></td>
                <td><?= h((string)($log['actor_role'] ?? '')) ?></td>
                <td><?= h((string)($log['action'] ?? '')) ?></td>
                <?php
                  $skr = ['draft'=>'작성중','submitted'=>'제출완료','under_review'=>'검토중','need_fix'=>'보완요청','approved'=>'승인','rejected'=>'반려','contracted'=>'계약완료','withdrawn'=>'취소'];
                  $akr = ['under_review'=>'검토시작','need_fix'=>'보완요청','approved'=>'승인','rejected'=>'반려'];
                ?>
                <td><?= $skr[$log['before_status']??'']??h($log['before_status']??'') ?> → <?= $skr[$log['after_status']??'']??h($log['after_status']??'') ?></td>
                <td><?= h((string)($log['memo'] ?? '')) ?></td>
              </tr>
            <?php endforeach; ?>
          <?php endif; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>
<script>
function calcMdReview(changedField) {
  const base = parseFloat(document.getElementById('md-base')?.value) || 0;
  const plusEl = document.getElementById('md-plus-pct');
  const minusEl = document.getElementById('md-minus-pct');
  let nextPlusPct = parseInt(plusEl?.value || '0', 10) || 0;
  let nextMinusPct = parseInt(minusEl?.value || '0', 10) || 0;
  const limitPct = <?= (int)$reviewAdjustLimitPct ?>;
  const netPct = nextPlusPct - nextMinusPct;
  if (limitPct > 0) {
    if (netPct > limitPct && changedField === 'plus') {
      nextPlusPct = nextMinusPct + limitPct;
      if (plusEl) plusEl.value = String(nextPlusPct);
    } else if (netPct < -limitPct && changedField === 'minus') {
      nextMinusPct = nextPlusPct + limitPct;
      if (minusEl) minusEl.value = String(nextMinusPct);
    }
  }
  const nextPlus = base * (nextPlusPct / 100);
  const nextMinus = base * (nextMinusPct / 100);
  const final = Math.max(0, Math.round((base + nextPlus - nextMinus) * 2) / 2);
  const el = document.getElementById('md-final');
  const finalText = final.toFixed(1).replace(/\.0$/, '');
  if (el) el.value = finalText;
  const display = document.getElementById('md-final-display');
  if (display) display.textContent = finalText;
  const summary = document.getElementById('md-percent-summary');
  if (summary) summary.textContent = `가산 ${nextPlusPct}% (${nextPlus.toFixed(2)} M/D) / 감산 ${nextMinusPct}% (${nextMinus.toFixed(2)} M/D)`;
}
function appendMdFactor(kind, group, ref, label) {
  const note = document.getElementById('md-note');
  if (!note) return;
  const parts = [`[${kind}]`, `[${group}${ref ? ' ' + ref : ''}]`, label];
  const line = parts.join(' ');
  const current = (note.value || '').trim();
  const rows = current ? current.split('\n').map(v => v.trim()).filter(Boolean) : [];
  if (rows.includes(line)) return;
  note.value = current ? current + '\n' + line : line;
  note.dispatchEvent(new Event('input', { bubbles: true }));
}
function doAction(action) {
  if (action === 'rejected') {
    const memo = document.getElementById('review-memo').value.trim();
    if (!memo && !confirm('반려 사유 없이 진행하시겠습니까?')) return false;
  }
  document.getElementById('review-action').value = action;
  return true;
}
document.addEventListener('DOMContentLoaded', calcMdReview);
</script>
</body>
</html>
