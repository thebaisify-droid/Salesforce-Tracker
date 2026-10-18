<?php
/**
 * Plugin Name: Salesforce Snapshot Receiver
 * Description: Authenticated, fail-closed delivery of quality-gated Salesforce snapshots.
 * Version: 0.2.0
 */
if (!defined('ABSPATH')) { exit; }

/** Assign this capability only to a dedicated transport identity after review. */
function sf_snapshot_validate($data, $now = null) {
    $now = $now === null ? time() : (int) $now;
    if (!is_array($data) || ($data['schema'] ?? '') !== 'salesforce-hiring-dashboard/v1'
        || !is_array($data['vacancies'] ?? null)
        || !is_int($data['active_vacancies'] ?? null)
        || $data['active_vacancies'] < 0
        || $data['active_vacancies'] > count($data['vacancies'])
        || ($data['pipeline']['quality_passed'] ?? null) !== true
        || ($data['refresh']['status'] ?? null) !== 'success') {
        return new WP_Error('sf_invalid_snapshot', 'Quality or schema validation failed', array('status' => 422));
    }
    $stamp = $data['refresh']['finished_at'] ?? null;
    $time = is_string($stamp) && preg_match('/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/D', $stamp) ? strtotime($stamp) : false;
    if ($time === false || $time > $now + 900 || $time < $now - 36 * HOUR_IN_SECONDS) {
        return new WP_Error('sf_stale_snapshot', 'Missing, stale, or future-dated refresh', array('status' => 422));
    }
    return $time;
}

function sf_snapshot_receive(WP_REST_Request $request) {
    $args = $request->get_json_params();
    if (!is_array($args) || !is_string($args['snapshot'] ?? null)
        || !is_string($args['sha256'] ?? null)
        || !preg_match('/^[a-f0-9]{64}$/D', $args['sha256'])) {
        return new WP_Error('sf_bad_envelope', 'Invalid snapshot envelope', array('status' => 400));
    }
    $raw = $args['snapshot'];
    if (strlen((string) $request->get_body()) > 560000) {
        return new WP_Error('sf_oversized_envelope', 'Envelope exceeds size limit', array('status' => 413));
    }
    if (strlen($raw) > 400000 || strlen($raw) < 64
        || !hash_equals(hash('sha256', $raw), $args['sha256'])) {
        return new WP_Error('sf_checksum_failed', 'Payload size or checksum mismatch', array('status' => 422));
    }
    $data = json_decode($raw, true);
    $verified = sf_snapshot_validate($data);
    if (is_wp_error($verified)) { return $verified; }

    $upload = wp_get_upload_dir();
    if (!empty($upload['error']) || empty($upload['basedir'])) {
        return new WP_Error('sf_storage', 'Uploads directory unavailable', array('status' => 503));
    }
    $dir = trailingslashit($upload['basedir']) . 'salesforce-tracker';
    $target = $dir . '/live-data.json';
    if (is_link($dir) || is_link($target) || (file_exists($dir) && !is_dir($dir))) {
        return new WP_Error('sf_unsafe_path', 'Unsafe snapshot path', array('status' => 409));
    }
    if (!wp_mkdir_p($dir)) {
        return new WP_Error('sf_storage', 'Cannot prepare directory', array('status' => 503));
    }
    $lockpath = $dir . '/.salesforce-snapshot.lock';
    if (is_link($lockpath)) {
        return new WP_Error('sf_unsafe_path', 'Unsafe lock path', array('status' => 409));
    }
    $lock = @fopen($lockpath, 'c');
    if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) {
        if ($lock) { fclose($lock); }
        return new WP_Error('sf_busy', 'Another snapshot upload is in progress', array('status' => 409));
    }
    try {
    if (is_file($target)) {
        $prior = json_decode((string) @file_get_contents($target), true);
        $prior_time = is_array($prior) && is_string($prior['refresh']['finished_at'] ?? null)
            ? strtotime($prior['refresh']['finished_at']) : false;
        if ($prior_time === false || $verified < $prior_time) {
            return new WP_Error('sf_rollback_refused', 'Current snapshot needs review or is newer', array('status' => 409));
        }
    }
    $temporary = tempnam($dir, 'sf-stage-');
    if ($temporary === false) {
        return new WP_Error('sf_storage', 'Unable to stage snapshot', array('status' => 503));
    }
    try {
        if (file_put_contents($temporary, $raw, LOCK_EX) !== strlen($raw)
            || !hash_equals($args['sha256'], (string) hash_file('sha256', $temporary))
            || !rename($temporary, $target)) {
            return new WP_Error('sf_storage', 'Atomic snapshot replacement failed', array('status' => 503));
        }
    } finally {
        if (is_file($temporary)) { @unlink($temporary); }
    }
    delete_transient('zarafytek_sf_dashboard_v2');
    return array('accepted' => true, 'sha256' => $args['sha256'],
                 'refresh_finished_at' => $data['refresh']['finished_at'],
                 'vacancy_records' => count($data['vacancies']));
    } finally {
        flock($lock, LOCK_UN);
        fclose($lock);
    }
}

add_action('rest_api_init', static function () {
    register_rest_route('salesforce-tracker/v1', '/snapshot', array(
        'methods' => 'POST',
        'permission_callback' => static function () {
            return is_user_logged_in() && current_user_can('sf_deliver_snapshot');
        },
        'callback' => 'sf_snapshot_receive',
    ));
});
