<?php
declare(strict_types=1);

/**
 * md_save_base.php
 * MD 산출기(kab_audit_days.php)가 계산한 "기본 MD"를 저장하는 단일 창구.
 * 검토서(cb_application_review.php)는 이 값을 certification_application_md_reviews.base_md로 그대로 읽어간다.
 *
 * 요청: POST application_id, base_md, base_md_detail_json(선택)
 * 응답: {"ok":true} 또는 {"ok":false, "msg":"..."}
 */

require_once __DIR__ . '/config.php';

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_name(APP_INSTANCE . '_sid');
    session_start();
}

require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/auth.php';
require_once __DIR__ . '/helpers.php';

header('Content-Type: application/json; charset=utf-8');

require_role(['cb', 'cb_admin', 'cb_staff', 'cb_manager', 'cb_reviewer', 'admin']);

$applicationId = (int)($_POST['application_id'] ?? 0);
$baseMd        = (float)($_POST['base_md'] ?? -1);
$detailJson    = (string)($_POST['base_md_detail_json'] ?? '{}');

if ($applicationId <= 0 || $baseMd < 0) {
    echo json_encode(['ok' => false, 'msg' => '잘못된 요청입니다 (application_id/base_md 확인 필요)']);
    exit;
}

// 계산 상세(JSON)는 그대로 검증 없이 저장 — 감사근거 표시용일 뿐 계산에는 관여하지 않음
json_decode($detailJson);
if (json_last_error() !== JSON_ERROR_NONE) {
    $detailJson = '{}';
}

$actor = (string)($_SESSION['user_role'] ?? $_SESSION['role'] ?? '');

try {
    $exists = table_exists($pdo, 'certification_application_md_reviews');
    if (!$exists) {
        echo json_encode(['ok' => false, 'msg' => 'certification_application_md_reviews 테이블이 없습니다. 스키마 생성이 먼저 필요합니다.']);
        exit;
    }

    $stmt = $pdo->prepare(
        "INSERT INTO certification_application_md_reviews
            (application_id, base_md, base_md_detail_json, base_md_calculated_at, base_md_calculated_by)
         VALUES (:app_id, :base_md, :detail, NOW(), :actor)
         ON DUPLICATE KEY UPDATE
            base_md = VALUES(base_md),
            base_md_detail_json = VALUES(base_md_detail_json),
            base_md_calculated_at = VALUES(base_md_calculated_at),
            base_md_calculated_by = VALUES(base_md_calculated_by)"
    );
    $stmt->execute([
        'app_id'  => $applicationId,
        'base_md' => $baseMd,
        'detail'  => $detailJson,
        'actor'   => $actor,
    ]);

    echo json_encode(['ok' => true]);
} catch (Throwable $e) {
    echo json_encode(['ok' => false, 'msg' => $e->getMessage()]);
}
