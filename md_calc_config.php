<?php
/**
 * md_calc_config.php — MD 산정 파라미터 단일 소스
 *
 * 지금은 md_calc_config.json 파일을 그대로 읽어서 반환하지만,
 * 실제 운영 DB 연동 시에는 이 함수 내부만 DB::rows() 조회로 교체하면 되고,
 * 이 파일을 사용하는 kab_audit_days.php / kab_audit_days_v8.html 쪽 코드는
 * 전혀 손댈 필요가 없도록 설계했다 (데이터 출처를 이 한 곳에만 감춤).
 *
 * 예) 운영 전환 시 아래처럼 교체:
 *   $config['md5_employee_table']['9001'] = DB::rows("SELECT emp_min, risk_high_total, ... FROM md5_employee_table WHERE standard_code='9001' ORDER BY emp_min");
 */
function load_md_calc_config(): array {
    static $cache = null;
    if ($cache !== null) return $cache;

    $jsonPath = __DIR__ . '/md_calc_config.json';
    $raw = file_get_contents($jsonPath);
    $cache = json_decode($raw, true) ?: [];
    return $cache;
}

/** JSON 문자열 그대로 반환 (페이지에 <script>const KAB_CONFIG=...</script>로 주입할 때 사용) */
function md_calc_config_json(): string {
    // 이미 유효한 JSON 파일이므로 재인코딩 없이 그대로 전달 (데이터 손실/재변환 위험 없음)
    return file_get_contents(__DIR__ . '/md_calc_config.json');
}
