<?php
/**
 * Multi-run historical retention for the UK Business & Technology Jobs Tracker.
 *
 * Pure, deterministic server-side merge. Incoming API snapshots must still
 * pass the existing strict five-source/current-run checks first. Never imply
 * that retained records were observed or confirmed on the latest refresh.
 */
if (!defined('ABSPATH')) { exit; }

function zarafy_ba_source_key($name, $run, $dataset) {
    return (string)$name . "|" . (string)$run . "|" . (string)$dataset;
}

/** Exact source + original HTTPS advert URL is the display identity across Actor runs. */
function zarafy_ba_advert_identity($r) {
    if (!is_array($r) || empty($r['job_source']) || empty($r['original_advert_url'])) return '';
    return hash('sha256', (string)$r['job_source'] . "\\0" . (string)$r['original_advert_url']);
}

function zarafy_ba_safe_observed_time($value, $end, $cutoff) {
    if (!is_string($value) || !preg_match('/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/D', $value)) return false;
    $stamp = strtotime($value);
    return $stamp !== false && $stamp >= $cutoff && $stamp <= $end + 900 ? $stamp : false;
}

/**
 * One-time migration of the published 15 Oct 2026 historical pilot.
 * Its old v1 rows omitted observed_at; attach the ACTUAL terminal timestamp
 * of the corresponding original Actor run (verified against Apify records).
 * Never use publication time, the current snapshot time, or a guessed date.
 * Reject all other legacy records without per-record provenance.
 */
function zarafy_ba_legacy_run_finish($r, $previous) {
    if (!is_array($previous)
        || ($previous['schema'] ?? '') !== 'ba-live-snapshot/v1'
        || ($previous['refresh']['type'] ?? '') !== 'HISTORICAL_COMPLETED_FIVE_SOURCE_PILOT'
        || ($previous['refresh']['finished_at'] ?? '') !== '2026-10-15T15:51:48.728Z'
        || !is_array($r)) return null;
    $original=array(
        'CV-Library'=>array('qo9YEfFlbYaV31MkK','OD5lSdCGHaw4q1D4j','2026-10-15T13:38:38.889Z'),
        'Totaljobs'=>array('2TlvO2bI41Bl50TeR','Yt7qb5XvPgdWn3TSW','2026-10-15T13:39:04.363Z'),
        'Reed UK'=>array('xLIKQOkwaZE5jFJn7','lecElui54GPzA0Qux','2026-10-15T13:39:24.929Z'),
        'Indeed UK'=>array('i6unDcLG8Qh1XSftt','ssJHtekdlbvmP2UCZ','2026-10-15T13:39:51.979Z'),
        'JobServe'=>array('c2PSagDDBiesSovtt','nkk1RZK5gznvfZogL','2026-10-15T15:51:48.728Z')
    );
    $source=$r['job_source'] ?? '';
    $match=$original[$source] ?? null;
    if (!$match || ($r['source_run_id'] ?? '') !== $match[0]
        || ($r['dataset_id'] ?? '') !== $match[1]) return null;
    return $match[2];
}

/** Pure merge. Previous data is used only if it was a correctly typed stored snapshot. */
function zarafy_ba_merge_rolling_snapshot($current, $previous = null) {
    $end = strtotime($current['refresh']['finished_at']);
    if ($end === false) throw new RuntimeException('Missing current source observation');
    $cutoff = $end - 30 * 86400;
    $family_allowlist = array(
        'Business Analysis', 'Data Analysis', 'Business Intelligence', 'Delivery Management',
        'Product Ownership', 'Product Management', 'Agile / Scrum', 'Project Management',
        'Business Change & Transformation', 'Programme & Portfolio Management',
        'Business Process & Operational Analysis', 'Agile Leadership',
        'Product Strategy & Operations', 'Service Management & Design',
        'Data & Analytics Management', 'Information Security Analysis',
        'Security Operations / SOC', 'Security Architecture',
        'Security Consulting & Advisory', 'Security Risk & Third-Party Risk',
        'Security Management', 'IT Security',
        // Additional families explicitly approved in the 16 October review.
        // Preserve exact family labels and source-run identity; no generic catch-all.
        'Technology Leadership & Management',
        'Enterprise & Solution Architecture',
        'IT Infrastructure & Support Engineering',
        'Engineering & Technical Delivery',
        'Security Engineering',
        'Technology Governance, Risk & Compliance'
    );
    $allowed = array_fill_keys($family_allowlist, true);
    $current_receipts = array();
    foreach ($current['sources'] as $s) {
        $current_receipts[zarafy_ba_source_key($s['source'], $s['run_id'], $s['dataset_id'])] = $s;
    }

    $previous_receipts = array();
    if (is_array($previous) && in_array($previous['schema'] ?? '', array('ba-live-snapshot/v1','ba-live-snapshot/v2'), true)
        && isset($previous['records'], $previous['sources']) && is_array($previous['records']) && is_array($previous['sources'])) {
        foreach (array_merge($previous['sources'], (array)($previous['historical_sources'] ?? array())) as $receipt) {
            if (!is_array($receipt) || empty($receipt['source']) || empty($receipt['run_id']) || empty($receipt['dataset_id'])
                || ($receipt['status'] ?? '') !== 'SUCCEEDED') continue;
            $previous_receipts[zarafy_ba_source_key($receipt['source'], $receipt['run_id'], $receipt['dataset_id'])] = $receipt;
        }
    }

    $records = array();
    $put = static function($r, $allowed_receipts) use (&$records, $allowed, $end, $cutoff) {
        if (!is_array($r) || !is_string($r['id'] ?? null) || $r['id'] === ''
            || empty($allowed[$r['role_family'] ?? ''])
            || !is_string($r['original_advert_url'] ?? null)
            || !filter_var($r['original_advert_url'], FILTER_VALIDATE_URL)
            || strtolower((string)parse_url($r['original_advert_url'], PHP_URL_SCHEME)) !== 'https'
            || parse_url($r['original_advert_url'], PHP_URL_USER) !== null
            || parse_url($r['original_advert_url'], PHP_URL_PASS) !== null
            || empty($r['title'])) return;
        $key = zarafy_ba_source_key($r['job_source'] ?? '', $r['source_run_id'] ?? '', $r['dataset_id'] ?? '');
        if (!isset($allowed_receipts[$key])) return;
        $stamp = zarafy_ba_safe_observed_time($r['observed_at'] ?? null, $end, $cutoff);
        if ($stamp === false) return;
        $r['last_observed_at'] = $r['observed_at'];
        $r['observed_age_days'] = max(0, (int)floor(($end - $stamp) / 86400));
        $r['availability_status'] = 'SOURCE_OBSERVED_NOT_EMPLOYER_CONFIRMED';
        // The same source URL can arrive with a new internal ID on a later run.
        // Keep the latest observation AND its original source-run provenance.
        $identity = zarafy_ba_advert_identity($r);
        if ($identity === '') return;
        if (!isset($records[$identity]) || $stamp >= strtotime($records[$identity]['last_observed_at'])) {
            $records[$identity] = $r;
        }
    };
    // Previous first, current second; a fresh current observation replaces an older one.
    if ($previous_receipts) {
        foreach ($previous['records'] as $r) {
            if (is_array($r) && empty($r['observed_at'])) {
                $terminal=zarafy_ba_legacy_run_finish($r,$previous);
                if ($terminal !== null) {
                    $r['observed_at']=$terminal;
                    $r['observation_timestamp_basis']='ORIGINAL_ACTOR_RUN_FINISHED_AT';
                }
            }
            $put($r, $previous_receipts);
        }
    }
    foreach ($current['records'] as $r) $put($r, $current_receipts);

    $by_family = array();
    foreach ($records as $r) $by_family[$r['role_family']][] = $r;
    $compare = static function($a, $b) {
        $d = strcmp($b['last_observed_at'], $a['last_observed_at']);
        return $d ?: strcmp($a['id'], $b['id']);
    };
    foreach ($by_family as &$group) usort($group, $compare);
    unset($group);

    // Reserve space for up to 20 recent observations from each represented family,
    // then fill remaining slots by recency. No invented minimum family count.
    $selected = array(); $remainder = array();
    foreach ($family_allowlist as $family) {
        $group = $by_family[$family] ?? array();
        foreach (array_slice($group, 0, 20) as $row) $selected[zarafy_ba_advert_identity($row)] = $row;
        foreach (array_slice($group, 20) as $row) $remainder[] = $row;
    }
    usort($remainder, $compare);
    foreach ($remainder as $r) {
        if (count($selected) >= 450) break;
        $selected[zarafy_ba_advert_identity($r)] = $r;
    }
    $final = array_values($selected);
    usort($final, $compare);
    if (count($final) > 450) $final = array_slice($final, 0, 450);

    $current_keys = array_fill_keys(array_keys($current_receipts), true);
    $historic = array();
    foreach ($final as $r) {
        $key = zarafy_ba_source_key($r['job_source'], $r['source_run_id'], $r['dataset_id']);
        if (!isset($current_keys[$key]) && isset($previous_receipts[$key])) $historic[$key] = $previous_receipts[$key];
    }
    $output = $current;
    $output['schema'] = 'ba-live-snapshot/v2';
    $output['historical_sources'] = array_values($historic);
    $output['records'] = $final;
    $output['retention'] = array(
        'policy' => 'LAST_SOURCE_OBSERVATION_WITHIN_30_DAYS',
        'max_records' => 450,
        'source_observed_not_employer_confirmed' => true,
        'current_batch_count' => count($current['records']),
        'display_count' => count($final),
        'family_count' => count($by_family),
    );
    // Keep the most recent 450 records and hard stop before receiver's 1.1MB bound.
    while (count($output['records']) > 1 && strlen(json_encode($output, JSON_INVALID_UTF8_SUBSTITUTE)) > 1050000) {
        array_pop($output['records']);
    }
    if (strlen(json_encode($output, JSON_INVALID_UTF8_SUBSTITUTE)) > 1050000)
        throw new RuntimeException('Retained data exceeds the storage safety limit');
    // Remove orphan provenance when size trimming removed the sole dependent record.
    $used = array();
    foreach ($output['records'] as $r) $used[zarafy_ba_source_key($r['job_source'], $r['source_run_id'], $r['dataset_id'])] = true;
    $output['historical_sources'] = array_values(array_filter($output['historical_sources'],
        static function($s) use ($used) {
            return isset($used[zarafy_ba_source_key($s['source'], $s['run_id'], $s['dataset_id'])]);
        }));
    $output['retention']['display_count'] = count($output['records']);
    return $output;
}

