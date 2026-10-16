<?php
/**
 * Plugin Name: Business Analysis Snapshot Receiver
 * Description: Independent authenticated atomic delivery of quality-gated BA vacancy snapshots.
 * Version: 0.3.2
 */
if (!defined('ABSPATH')) { exit; }
require_once __DIR__ . '/rolling-retention.php';

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
        $seen[$s['source']] = $s;
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
            || ($seen[$r['job_source']]['run_id'] ?? '') !== ($r['source_run_id'] ?? '')
            || ($seen[$r['job_source']]['dataset_id'] ?? '') !== ($r['dataset_id'] ?? '')
            || zarafy_ba_safe_observed_time($r['observed_at'] ?? null, $time, $time-36*HOUR_IN_SECONDS) === false
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
        try {
            $merged=zarafy_ba_merge_rolling_snapshot($parsed, $prior ?? null);
            $to_store=json_encode($merged, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
            if (!is_string($to_store) || strlen($to_store)>1100000)
                throw new RuntimeException('Invalid rolling snapshot size');
        } catch (Throwable $e) {
            return new WP_Error('ba_retention','Rolling retention quality check failed',array('status'=>422));
        }
        $tmp=tempnam($dir,'ba-stage-');
        if ($tmp===false) return new WP_Error('ba_storage','Cannot stage',array('status'=>503));
        try {
            if (file_put_contents($tmp,$to_store,LOCK_EX)!==strlen($to_store)
                || !hash_equals(hash('sha256',$to_store),(string)hash_file('sha256',$tmp))
                || !rename($tmp,$target)) {
                return new WP_Error('ba_storage','Atomic save failed',array('status'=>503));
            }
        } finally {
            if (file_exists($tmp)) @unlink($tmp);
        }
        return array('accepted'=>true,'sha256'=>$data['sha256'],
                     'record_count'=>count($parsed['records']),
                     'retained_display_count'=>count($merged['records']),
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


/**
 * Server-rendered, fail-closed front-end handoff for BA page 49 only.
 * This reads the receiver's private local file, not a public uploads URL.
 * If the file or any validation fails, return the original embedded table.
 */
function zarafy_ba_live_content_bridge($content) {
    if (!is_string($content) || !is_page(49) || get_the_ID() !== 49
        || strpos($content, '<tbody id="ba-v2-body">') === false
        || strpos($content, '<script type="application/json" id="ba-v2-json">') === false) {
        return $content;
    }
    $uploads = wp_get_upload_dir();
    if (!empty($uploads['error']) || empty($uploads['basedir'])) return $content;
    $directory = trailingslashit($uploads['basedir']) . 'business-analysis-tracker';
    $path = $directory . '/live-data.json';
    if (is_link($directory) || is_link($path) || !is_file($path)) return $content;
    $size = @filesize($path);
    if (!is_int($size) || $size < 64 || $size > 1100000) return $content;
    $raw = @file_get_contents($path);
    if (!is_string($raw) || strlen($raw) !== $size) return $content;
    $data = json_decode($raw, true);
    if (!is_array($data) || !in_array(($data['schema'] ?? ''), array('ba-live-snapshot/v1','ba-live-snapshot/v2'), true)
        || ($data['quality']['passed'] ?? null) !== true
        || ($data['refresh']['status'] ?? '') !== 'success'
        || !is_array($data['sources'] ?? null) || count($data['sources']) !== 5
        || !is_array($data['records'] ?? null)
        || count($data['records']) < 1 || count($data['records']) > 1000) {
        return $content;
    }
    $expected = array_fill_keys(array('CV-Library','Totaljobs','Reed UK','Indeed UK','JobServe'), true);
    $seen = array();
    foreach ($data['sources'] as $receipt) {
        $name = is_array($receipt) ? ($receipt['source'] ?? '') : '';
        if (!isset($expected[$name]) || isset($seen[$name])
            || ($receipt['status'] ?? '') !== 'SUCCEEDED'
            || ($receipt['attempted'] ?? null) !== true
            || !is_string($receipt['run_id'] ?? null) || $receipt['run_id'] === ''
            || !is_string($receipt['dataset_id'] ?? null) || $receipt['dataset_id'] === '') {
            return $content;
        }
        $seen[$name] = $receipt;
    }
    // Provenance for retained advertisements must remain attached to their
    // original successful Actor run, not impersonate this refresh's five runs.
    $historic = array();
    if (($data['schema'] ?? '') === 'ba-live-snapshot/v2') {
        if (!is_array($data['historical_sources'] ?? null)
            || count($data['historical_sources']) > 180) return $content;
        foreach ($data['historical_sources'] as $receipt) {
            $source=$receipt['source'] ?? '';
            $run=$receipt['run_id'] ?? '';
            $dataset=$receipt['dataset_id'] ?? '';
            if (!isset($expected[$source]) || !is_string($run) || $run === ''
                || !is_string($dataset) || $dataset === ''
                || ($receipt['status'] ?? '') !== 'SUCCEEDED'
                || ($receipt['attempted'] ?? null) !== true) return $content;
            $key=zarafy_ba_source_key($source,$run,$dataset);
            if (isset($historic[$key])) return $content;
            $historic[$key] = true;
        }
    }
    $finished = $data['refresh']['finished_at'] ?? null;
    $time = is_string($finished) ? strtotime($finished) : false;
    if ($time === false || $time > time() + 900) return $content;
    $rows = array();
    $seen_ids = array();
    foreach ($data['records'] as $r) {
        if (!is_array($r) || !is_string($r['id'] ?? null) || $r['id'] === ''
            || isset($seen_ids[$r['id']]) || empty($r['title']) || empty($r['role_family'])) return $content;
        $source = $r['job_source'] ?? '';
        $url = $r['original_advert_url'] ?? '';
        $parsed = is_string($url) ? wp_parse_url($url) : false;
        $is_current = isset($seen[$source])
            && ($r['source_run_id'] ?? '') === ($seen[$source]['run_id'] ?? '')
            && ($r['dataset_id'] ?? '') === ($seen[$source]['dataset_id'] ?? '');
        // $seen is source => original current run receipt.
        $provenance=zarafy_ba_source_key($source, $r['source_run_id'] ?? '', $r['dataset_id'] ?? '');
        if ((!$is_current && !isset($historic[$provenance]))
            || (($data['schema'] ?? '') === 'ba-live-snapshot/v2' &&
                zarafy_ba_safe_observed_time($r['last_observed_at'] ?? null, $time, $time-30*86400) === false)
            || !is_array($parsed) || ($parsed['scheme'] ?? '') !== 'https'
            || empty($parsed['host']) || isset($parsed['user']) || isset($parsed['pass'])) {
            return $content;
        }
        $seen_ids[$r['id']] = true;
        $item = array(
            'id' => $r['id'],
            'title' => (string) $r['title'],
            'advertiser' => (string) ($r['advertiser'] ?? 'Not specified'),
            'location' => (string) ($r['location'] ?? 'Not specified'),
            'source' => (string) $source,
            'role_family' => (string) $r['role_family'],
            'track' => (string) ($r['track'] ?? ''),
            'url' => $url,
            'posted_date' => (string) ($r['posted_date'] ?? ''),
            'employment' => (string) ($r['employment'] ?? 'Not specified'),
            'working_arrangement' => (string) ($r['working_arrangement'] ?? 'Not specified'),
            'sector' => (string) ($r['sector_display'] ?? $r['sector'] ?? 'Not specified'),
            'description_summary' => (string) ($r['description_summary'] ?? ''),
            'skills' => array(),
            'cross_post_cluster' => (string) ($r['cross_post_cluster'] ?? ''),
            'last_observed_at' => (string) ($r['last_observed_at'] ?? $r['observed_at'] ?? ''),
            'observed_age_days' => (int) ($r['observed_age_days'] ?? 0),
            'availability_status' => 'SOURCE_OBSERVED_NOT_EMPLOYER_CONFIRMED'
        );
        $rows[] = $item;
    }
    $json = wp_json_encode($rows, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_UNICODE);
    if (!is_string($json) || $json === '') return $content;

    // Plain server-rendered table remains available if JavaScript is disabled.
    $trs = '';
    foreach ($rows as $r) {
        $date = 'Not specified';
        if (preg_match('/^\\d{4}-\\d\\d-\\d\\d$/D', $r['posted_date'])) {
            $dt = DateTimeImmutable::createFromFormat('!Y-m-d', $r['posted_date']);
            if ($dt && $dt->format('Y-m-d') === $r['posted_date']) $date = $dt->format('d/m/Y');
        }
        $trs .= '<tr class="ba-v2-record"><td><strong>' . esc_html($r['title'])
            . '</strong><small>Role family: ' . esc_html($r['role_family'])
            . '</small><small>Last source observation: ' .
              esc_html(($r['last_observed_at'] && strtotime($r['last_observed_at'])) ?
                  wp_date('d/m/Y', strtotime($r['last_observed_at'])) : 'Not specified')
            . ' · Not employer-confirmed open</small><details><summary>Job description summary</summary><p>Source excerpt: '
            . esc_html($r['description_summary'] ?: 'Not supplied by source')
            . '</p></details></td><td>' . esc_html($r['advertiser'])
            . '<small>Sector: ' . esc_html($r['sector']) . '</small></td><td>'
            . esc_html($r['location']) . '<small>Work mode: '
            . esc_html($r['working_arrangement']) . '</small></td><td>'
            . esc_html($r['employment']) . '</td><td>' . esc_html($r['source'])
            . '</td><td>' . esc_html($date) . '</td><td><a href="'
            . esc_url($r['url'])
            . '" target="_blank" rel="noopener noreferrer nofollow">View original advert &#8599;</a></td></tr>';
    }
    $tbody_start = '<tbody id="ba-v2-body">';
    $json_start = '<script type="application/json" id="ba-v2-json">';
    $tbody_end = '</tbody>';
    $script_end = '</script>';
    $body_at = strpos($content, $tbody_start);
    $body_stop = strpos($content, $tbody_end, $body_at);
    $script_at = strpos($content, $json_start);
    $script_stop = strpos($content, $script_end, $script_at);
    if ($body_at === false || $body_stop === false || $script_at === false || $script_stop === false
        || $script_at < $body_stop) return $content;
    $new_body = $tbody_start . $trs . $tbody_end;
    $content = substr_replace($content, $new_body, $body_at,
        $body_stop + strlen($tbody_end) - $body_at);
    $script_at = strpos($content, $json_start);
    $script_stop = strpos($content, $script_end, $script_at);
    $content = substr_replace($content, $json_start . $json . $script_end,
        $script_at, $script_stop + strlen($script_end) - $script_at);

    $status = '<strong id="ba-v2-status" aria-live="polite">';
    $at = strpos($content, $status);
    $stop = $at === false ? false : strpos($content, '</strong>', $at);
    if ($stop !== false) {
        $count = count($rows);
        $content = substr_replace($content, $status . $count . ' of ' . $count
            . ' advertisements shown</strong>', $at, $stop + 9 - $at);
    }
    $label = '<p id="ba-snapshot-observed" class="ba-foot">Snapshot loaded from the authenticated WordPress receiver. Last source observation: '
        . esc_html(wp_date('d/m/Y H:i', $time))
        . '. Includes retained advertisements observed within 30 days. Individual observation dates are shown; availability is not employer-confirmed.</p>';
    $marker = '<div class="ba-wrap">';
    if (strpos($content, $marker) !== false && strpos($content, 'id="ba-snapshot-observed"') === false) {
        $content = str_replace($marker, $label . $marker, $content);
    }
    // Include the six scope-approved technology and engineering families in
    // the visible role filter without changing the saved WordPress page.
    $family_select = '<select id="ba-v2-family">';
    $family_start = strpos($content, $family_select);
    if ($family_start !== false) {
        $family_end = strpos($content, '</select>', $family_start);
        if ($family_end !== false) {
            $select_fragment = substr($content, $family_start, $family_end - $family_start);
            $extra_families = array(
                'Technology Leadership & Management',
                'Enterprise & Solution Architecture',
                'IT Infrastructure & Support Engineering',
                'Engineering & Technical Delivery',
                'Security Engineering',
                'Technology Governance, Risk & Compliance'
            );
            $family_counts = array_count_values(array_column($rows, 'role_family'));
            $extra = '';
            foreach ($extra_families as $family) {
                if (strpos($select_fragment, 'value="' . esc_attr($family) . '"') !== false) continue;
                $extra .= '<option value="' . esc_attr($family) . '">' . esc_html($family)
                    . ' (' . (int)($family_counts[$family] ?? 0) . ')</option>';
            }
            if ($extra !== '') {
                $extra = '<optgroup label="Technology / Architecture / Engineering">' . $extra . '</optgroup>';
                $content = substr_replace($content, $extra, $family_end, 0);
            }
        }
    }
    return $content;
}
add_filter('the_content', 'zarafy_ba_live_content_bridge', 18);
