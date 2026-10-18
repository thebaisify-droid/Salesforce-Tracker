<?php
/**
 * Plugin Name: Salesforce Phase 1 Snapshot Explorer
 * Description: Read-only shortcode for locally delivered, QA-passed Salesforce source observations.
 * Version: 0.1.0
 */
if (!defined('ABSPATH')) { exit; }

function sfex_snapshot() {
    $upload = wp_get_upload_dir();
    if (!empty($upload['error']) || empty($upload['basedir'])) { return null; }
    $dir = trailingslashit($upload['basedir']) . 'salesforce-tracker';
    $path = $dir . '/live-data.json';
    if (is_link($dir) || is_link($path) || !is_file($path) || !is_readable($path)) { return null; }
    $size = filesize($path);
    if ($size === false || $size < 64 || $size > 400000) { return null; }
    $data = json_decode((string) @file_get_contents($path), true);
    if (!is_array($data) || ($data['schema'] ?? '') !== 'salesforce-hiring-dashboard/v1'
        || ($data['pipeline']['quality_passed'] ?? null) !== true
        || ($data['refresh']['status'] ?? '') !== 'success'
        || !is_array($data['vacancies'] ?? null)
        || !is_int($data['active_vacancies'] ?? null)
        || $data['active_vacancies'] < 0
        || $data['active_vacancies'] > count($data['vacancies'])) { return null; }
    $stamp = $data['refresh']['finished_at'] ?? null;
    $when = is_string($stamp) ? strtotime($stamp) : false;
    if ($when === false || $when > time() + 900 || $when < time() - 36 * HOUR_IN_SECONDS) { return null; }
    // "ACTIVE" is a source-reported lifecycle designation, not direct availability proof.
    return $data;
}

function sfex_safe_link($candidate) {
    if (!is_string($candidate) || strlen($candidate) > 1500) { return ''; }
    $p = wp_parse_url($candidate);
    if (!is_array($p) || ($p['scheme'] ?? '') !== 'https' || empty($p['host'])
        || isset($p['user']) || isset($p['pass'])) { return ''; }
    $host = strtolower($p['host']);
    $domains = array('cv-library.co.uk','totaljobs.com','reed.co.uk','indeed.com','jobserve.com');
    foreach ($domains as $domain) {
        if ($host === $domain || substr($host, -(strlen($domain) + 1)) === '.' . $domain) {
            return esc_url($candidate);
        }
    }
    return '';
}

function sfex_render_shortcode() {
    $data = sfex_snapshot();
    if (!$data) {
        return '<section class="sfex-notice" role="status"><strong>Verified refresh unavailable.</strong> '
            . 'The existing Phase 1 research archive remains available; no new current-vacancy count is displayed.</section>';
    }
    $rows = array();
    foreach ($data['vacancies'] as $vacancy) {
        if (!is_array($vacancy)) { continue; }
        $title = (string) ($vacancy['title'] ?? '');
        if ($title === '') { continue; }
        $url = sfex_safe_link($vacancy['url'] ?? $vacancy['apply_url'] ?? '');
        $source_items = $vacancy['sources'] ?? array();
        $names = array();
        if (is_array($source_items)) {
            foreach ($source_items as $source) {
                if (is_array($source) && is_string($source['label'] ?? null)) {
                    $names[] = sanitize_text_field($source['label']);
                }
            }
        }
        $source = implode(', ', array_unique($names)) ?: 'Not specified';
        $employment = (string) ($vacancy['employment_type'] ?? $vacancy['contract_type'] ?? '');
        $work = (string) ($vacancy['work_mode'] ?? '');
        $sector = (string) ($vacancy['sector'] ?? '');
        $specialisms = $vacancy['specialisms'] ?? array();
        $skills = is_array($specialisms) ? implode(', ', array_filter($specialisms, 'is_string')) : '';
        $employer = (string) ($vacancy['end_client_name'] ?? $vacancy['advertiser'] ?? '');
        $location = (string) ($vacancy['location'] ?? '');
        $posted = substr((string) ($vacancy['posted_at'] ?? ''), 0, 10);
        $relevance = (string) ($vacancy['relevance'] ?? 'REVIEW');
        $search = strtolower(implode(' ', array($title, $employer, $sector, $skills, $location, $source)));
        $rows[] = '<tr class="sfex-row" data-search="' . esc_attr($search) . '" data-source="' . esc_attr($source) .
            '" data-employment="' . esc_attr(strtolower($employment)) . '" data-work="' . esc_attr(strtolower($work)) . '">' .
            '<td><strong>' . esc_html($title) . '</strong></td><td>' . esc_html($relevance) . '</td>' .
            '<td>' . esc_html((string) ($vacancy['role_family'] ?? 'Unresolved')) . '<small>' . esc_html($skills) . '</small></td>' .
            '<td>' . esc_html($employer ?: 'Not specified') . '<small>' . esc_html($sector ?: 'Sector not specified') . '</small></td>' .
            '<td>' . esc_html($location ?: 'Not specified') . '</td><td>' . esc_html($employment ?: 'Not specified') . '</td>' .
            '<td>' . esc_html($work ?: 'Not specified') . '</td><td>' . esc_html($source) . '</td>' .
            '<td>' . esc_html($posted) . '</td><td>' .
            ($url ? '<a href="' . $url . '" target="_blank" rel="noopener noreferrer">View source ↗</a>' : 'Link unavailable') .
            '</td></tr>';
    }
    if (!$rows) { return '<p class="sfex-notice">No quality-approved source observations are available. This does not mean zero open jobs.</p>'; }
    $id = 'sfex-' . wp_unique_id();
    $out = '<section class="sfex" id="' . esc_attr($id) . '"><h2>Vacancy explorer</h2>' .
        '<p class="sfex-notice"><strong>Source-observed, not independently verified open.</strong> ' .
        'Last quality-passed refresh: ' . esc_html($data['refresh']['finished_at']) . '. Original links may have expired.</p>' .
        '<div class="sfex-controls"><label>Search title, client, sector or skill<input class="sfex-q" type="search"></label>' .
        '<label>Source<select class="sfex-source"><option value="">All</option>';
    $sources = array();
    foreach ($data['vacancies'] as $vacancy) {
        foreach (is_array($vacancy['sources'] ?? null) ? $vacancy['sources'] : array() as $source) {
            if (is_array($source) && is_string($source['label'] ?? null)) { $sources[$source['label']] = true; }
        }
    }
    foreach (array_keys($sources) as $source) {
        $out .= '<option value="' . esc_attr($source) . '">' . esc_html($source) . '</option>';
    }
    $out .= '</select></label><label>Employment<select class="sfex-employment"><option value="">All</option>' .
        '<option value="permanent">Permanent</option><option value="contract">Contract</option>' .
        '<option value="temporary">Temporary</option></select></label>' .
        '<label>Working arrangement<select class="sfex-work"><option value="">All</option>' .
        '<option value="remote">Remote</option><option value="hybrid">Hybrid</option>' .
        '<option value="office">Office</option></select></label>' .
        '<button type="button" class="sfex-apply">Apply filters</button>' .
        '<button type="button" class="sfex-reset">Reset</button></div>' .
        '<p class="sfex-count">' . count($rows) . ' source-observed results</p>' .
        '<div class="sfex-table"><table><thead><tr><th>Vacancy</th><th>Relevance</th><th>Role / skills</th>' .
        '<th>Employer / sector</th><th>Location</th><th>Employment</th><th>Work mode</th><th>Source</th>' .
        '<th>Posted</th><th>Apply</th></tr></thead><tbody>' . implode('', $rows) . '</tbody></table></div></section>';
    $out .= '<style>.sfex{background:#0c1930;color:#e8f0fc;padding:20px;border-radius:16px}' .
        '.sfex h2{color:#fff}.sfex-notice{padding:12px;color:#ffe4aa;border:1px solid #a38644;border-radius:9px}' .
        '.sfex-controls{display:flex;flex-wrap:wrap;gap:10px;align-items:end}.sfex-controls label{flex:1;min-width:160px}' .
        '.sfex-controls input,.sfex-controls select{display:block;width:100%;padding:10px}' .
        '.sfex-controls button{padding:10px;background:#b4ff46;color:#09203b;border:0;border-radius:8px}' .
        '.sfex-table{overflow:auto}.sfex table{border-collapse:collapse;min-width:1100px;width:100%}' .
        '.sfex th,.sfex td{text-align:left;padding:12px;border-bottom:1px solid #314963}' .
        '.sfex td small{display:block;color:#adbed1}.sfex a{color:#b4ff46}.sfex-row[hidden]{display:none}</style>';
    $out .= '<script>(function(){const root=document.getElementById(' . wp_json_encode($id) . ');' .
        'if(!root)return;const rows=[...root.querySelectorAll(".sfex-row")],q=root.querySelector(".sfex-q"),' .
        'src=root.querySelector(".sfex-source"),e=root.querySelector(".sfex-employment"),w=root.querySelector(".sfex-work"),' .
        'c=root.querySelector(".sfex-count");function apply(){let n=0;const terms=q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);' .
        'rows.forEach(r=>{const ok=terms.every(t=>r.dataset.search.includes(t))&&(!src.value||r.dataset.source.includes(src.value))' .
        '&&(!e.value||r.dataset.employment.includes(e.value))&&(!w.value||r.dataset.work.includes(w.value));r.hidden=!ok;if(ok)n++});' .
        'c.textContent=n+" source-observed results"}root.querySelector(".sfex-apply").addEventListener("click",apply);' .
        'root.querySelector(".sfex-reset").addEventListener("click",()=>{q.value="";src.value="";e.value="";w.value="";apply()})})();</script>';
    return $out;
}

add_shortcode('sf_phase1_live_explorer', 'sfex_render_shortcode');
