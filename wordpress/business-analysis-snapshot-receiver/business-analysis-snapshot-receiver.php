<?php
/**
 * Plugin Name: Business Analysis Snapshot Receiver
 * Description: Independent authenticated atomic delivery of quality-gated BA vacancy snapshots.
 * Version: 0.1.0
 */
if (!defined('ABSPATH')) { exit; }

/* Dedicated capability: assign ba_deliver_snapshot only to an approved account. */
function zarafy_ba_validate_snapshot($d, $now = null) {
    if (!is_array($d) || ($d['schema'] ?? '') !== 'ba-live-snapshot/v1'
        || ($d['quality']['passed'] ?? null) !== true
        || ($d['refresh']['status'] ?? '') !== 'success'
        || !is_array($d['sources'] ?? null) || count($d['sources']) !== 5
        || !is_array($d['records'] ?? null) || count($d['records']) < 1
        || count($d['records']) > 1000) {
        return new WP_Error('ba_invalid_snapshot', 'Invalid schema, quality or records', array('status'=>422));
    }
    $names = array('CV-Library','Totaljobs','Reed UK','Indeed UK','JobServe');
    $seen = array();
    foreach ($d['sources'] as $s) {
        if (!is_array($s) || !in_array($s['source'] ?? '', $names, true)
            || ($s['status'] ?? '') !== 'SUCCEEDED'
            || ($s['attempted'] ?? null) !== true
            || empty($s['run_id']) || empty($s['dataset_id'])
            || isset($seen[$s['source']])) {
            return new WP_Error('ba_incomplete_sources', 'Five successful source receipts required', array('status'=>422));
        }
        $seen[$s['source']] = true;
    }
    $stamp = $d['refresh']['finished_at'] ?? '';
    $time = is_string($stamp) && preg_match('/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/D', $stamp) ? strtotime($stamp) : false;
    $now = $now === null ? time() : (int) $now;
    if ($time === false || $time > $now+900 || $time < $now-36*HOUR_IN_SECONDS) {
        return new WP_Error('ba_stale', 'Snapshot is stale or future-dated', array('status'=>422));
    }
    $ids=array();
    foreach ($d['records'] as $r) {
        if (!is_array($r) || !is_string($r['id'] ?? null) || !is_string($r['title'] ?? null)
            || !is_string($r['original_advert_url'] ?? null)
            || !wp_http_validate_url($r['original_advert_url'])
            || strpos($r['original_advert_url'],'https://') !== 0
            || !isset($seen[$r['job_source'] ?? ''])
            || empty($r['role_family']) || empty($r['source_run_id']) || isset($ids[$r['id']])) {
            return new WP_Error('ba_bad_row','Unsafe or incomplete advertisement',array('status'=>422));
        }
        $ids[$r['id']]=true;
    }
    return $time;
}
function zarafy_ba_receive(WP_REST_Request $request) {
    $data=$request->get_json_params();
    if (!is_array($data) || !is_string($data['snapshot'] ?? null)
        || !is_string($data['sha256'] ?? null)
        || !preg_match('/^[a-f0-9]{64}$/D',$data['sha256'])) {
        return new WP_Error('ba_envelope','Invalid delivery envelope',array('status'=>400));
    }
    $raw=$data['snapshot'];
    if (strlen($request->get_body())>1500000 || strlen($raw)>1100000 || strlen($raw)<64
        || !hash_equals(hash('sha256',$raw),$data['sha256'])) {
        return new WP_Error('ba_checksum','Oversize or checksum mismatch',array('status'=>422));
    }
    $parsed=json_decode($raw,true);
    $stamp=zarafy_ba_validate_snapshot($parsed);
    if (is_wp_error($stamp)) return $stamp;
    $uploads=wp_get_upload_dir();
    if (!empty($uploads['error']) || empty($uploads['basedir']))
        return new WP_Error('ba_storage','Uploads unavailable',array('status'=>503));
    $dir=trailingslashit($uploads['basedir']).'business-analysis-tracker';
    $target=$dir.'/live-data.json';
    if (is_link($dir) || is_link($target) || (file_exists($dir) && !is_dir($dir)))
        return new WP_Error('ba_path','Unsafe data path',array('status'=>409));
    if (!wp_mkdir_p($dir)) return new WP_Error('ba_storage','Cannot create data directory',array('status'=>503));
    $lockpath=$dir.'/.snapshot.lock';
    if (is_link($lockpath)) return new WP_Error('ba_path','Unsafe lock path',array('status'=>409));
    $lock=@fopen($lockpath,'c');
    if (!$lock || !flock($lock,LOCK_EX|LOCK_NB)) {
        if ($lock) fclose($lock);
        return new WP_Error('ba_busy','Delivery already in progress',array('status'=>409));
    }
    try {
        if (is_file($target)) {
            $prior=json_decode((string)@file_get_contents($target),true);
            $old=is_array($prior) ? strtotime($prior['refresh']['finished_at'] ?? '') : false;
            if ($old===false || $stamp<=$old)
                return new WP_Error('ba_rollback','Equal or older snapshot rejected',array('status'=>409));
        }
        $tmp=tempnam($dir,'ba-stage-');
        if ($tmp===false) return new WP_Error('ba_storage','Cannot stage',array('status'=>503));
        try {
            if (file_put_contents($tmp,$raw,LOCK_EX)!==strlen($raw)
                || !hash_equals($data['sha256'],(string)hash_file('sha256',$tmp))
                || !rename($tmp,$target)) {
                return new WP_Error('ba_storage','Atomic save failed',array('status'=>503));
            }
        } finally {
            if (file_exists($tmp)) @unlink($tmp);
        }
        return array('accepted'=>true,'sha256'=>$data['sha256'],
                     'record_count'=>count($parsed['records']),
                     'refresh_finished_at'=>$parsed['refresh']['finished_at']);
    } finally {
        flock($lock,LOCK_UN); fclose($lock);
    }
}
add_action('rest_api_init',static function () {
    register_rest_route('business-analysis-tracker/v1','/snapshot',array(
        'methods'=>'POST',
        'permission_callback'=>static function () {
            return is_user_logged_in() && current_user_can('ba_deliver_snapshot');
        },
        'callback'=>'zarafy_ba_receive'
    ));
});
