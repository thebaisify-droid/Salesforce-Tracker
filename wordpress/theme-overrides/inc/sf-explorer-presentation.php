<?php
/**
 * Phase 2 Salesforce live-feed presentation.
 *
 * Overrides only the Phase 1 shortcode renderer. The installed plugin retains
 * all snapshot safety checks (schema, QA, freshness, symlink protection).
 * Missing source material is never fabricated or interpreted as zero vacancies.
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }

function ukba_sf2_date( $raw ) {
    if ( ! is_string( $raw ) || ! preg_match( '/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/', $raw, $m ) ) {
        return 'Not specified';
    }
    if ( ! checkdate( (int) $m[2], (int) $m[3], (int) $m[1] ) ) { return 'Not specified'; }
    return $m[3] . '/' . $m[2] . '/' . $m[1];
}

function ukba_sf2_value( $value, $fallback = 'Not specified' ) {
    if ( ! is_string( $value ) || ! trim( $value ) ) { return $fallback; }
    return trim( $value );
}

function ukba_sf2_render_shortcode() {
    if ( ! function_exists( 'sfex_snapshot' ) || ! function_exists( 'sfex_safe_link' ) ) {
        return '<section class="sfex-notice" role="status">Source snapshot renderer unavailable. Existing research archive remains available.</section>';
    }
    $data = sfex_snapshot();
    if ( ! $data ) {
        return '<section class="sfex-notice" role="status"><strong>Verified refresh unavailable.</strong> The existing Phase 1 research archive remains available; no new vacancy count is displayed.</section>';
    }
    $rows = array();
    foreach ( $data['vacancies'] as $vacancy ) {
        if ( ! is_array( $vacancy ) || empty( $vacancy['title'] ) ) { continue; }
        $names = array();
        foreach ( (array) ( $vacancy['sources'] ?? array() ) as $source ) {
            if ( is_array( $source ) && ! empty( $source['label'] ) && is_string( $source['label'] ) ) {
                $names[] = $source['label'];
            }
        }
        $source_name = implode( ', ', array_unique( $names ) ) ?: 'Not specified';
        $specialisms = array_filter( (array) ( $vacancy['specialisms'] ?? array() ), 'is_string' );
        $summary = is_array( $vacancy['job_summary'] ?? null ) ? $vacancy['job_summary'] : array();
        $tools = array_filter( (array) ( $summary['tools'] ?? $specialisms ), 'is_string' );
        $tools = array_slice( array_unique( $tools ), 0, 12 );
        $skills = implode( ', ', $tools );
        $title = ukba_sf2_value( $vacancy['title'] );
        $advertiser = ukba_sf2_value( $vacancy['advertiser'] ?? null );
        $client = ukba_sf2_value( $vacancy['end_client_name'] ?? null, '' );
        $sector = ukba_sf2_value( $vacancy['sector'] ?? null );
        $role = ukba_sf2_value( $vacancy['role_family'] ?? null, 'Unresolved' );
        $location = ukba_sf2_value( $vacancy['location'] ?? null );
        $employment = ukba_sf2_value( $vacancy['employment_type'] ?? $vacancy['contract_type'] ?? null );
        $working = ukba_sf2_value( $vacancy['work_mode'] ?? null );
        $posted_iso = substr( (string) ( $vacancy['posted_at'] ?? '' ), 0, 10 );
        $posted_uk = ukba_sf2_date( $vacancy['posted_at'] ?? null );
        $responsibilities = ukba_sf2_value( $summary['responsibilities'] ?? null, 'Not specified in the captured advert.' );
        $requirements = ukba_sf2_value( $summary['requirements'] ?? null, 'Not specified in the captured advert.' );
        $excerpt = ukba_sf2_value( $summary['advert_excerpt'] ?? null, '' );
        $url = sfex_safe_link( $vacancy['url'] ?? $vacancy['apply_url'] ?? '' );
        if ( ! $url ) {
            foreach ( (array) ( $vacancy['sources'] ?? array() ) as $item ) {
                if ( is_array( $item ) ) {
                    $url = sfex_safe_link( $item['url'] ?? '' );
                    if ( $url ) { break; }
                }
            }
        }
        $haystack = strtolower( implode( ' ', array(
            $title, $advertiser, $client, $sector, $role, $location,
            $source_name, $employment, $working, $skills,
            $responsibilities, $requirements, $excerpt,
        ) ) );
        $rows[] = compact(
            'title', 'advertiser', 'client', 'sector', 'role', 'location',
            'employment', 'working', 'posted_iso', 'posted_uk',
            'source_name', 'skills', 'responsibilities', 'requirements',
            'excerpt', 'url', 'haystack'
        );
    }
    if ( ! $rows ) {
        return '<p class="sfex-notice">No source-observed records were supplied. This does not mean zero open jobs.</p>';
    }
    $id = 'sfex2-' . wp_unique_id();
    $source_options = array_unique( array_column( $rows, 'source_name' ) );
    $employment_options = array_unique( array_column( $rows, 'employment' ) );
    $working_options = array_unique( array_column( $rows, 'working' ) );
    $sector_options = array_unique( array_column( $rows, 'sector' ) );
    $role_options = array_unique( array_column( $rows, 'role' ) );
    sort( $source_options ); sort( $employment_options ); sort( $working_options );
    sort( $sector_options ); sort( $role_options );

    ob_start();
    ?>
    <section class="sfex sfex2" id="<?php echo esc_attr( $id ); ?>">
        <h2>Salesforce Vacancy Explorer</h2>
        <p class="sfex-notice"><strong>Source-observed Salesforce vacancies.</strong>
            Last quality-passed refresh: <?php echo esc_html( (string) $data['refresh']['finished_at'] ); ?>.
            Check each original advert for current availability; missing fields are not inferred.
        </p>
        <div class="sfex-controls">
            <label>Search title, client, sector, skill or description
                <input class="sfex-q" type="search" placeholder="Search vacancies…" aria-label="Search vacancies">
            </label>
            <?php foreach ( array(
                'source' => array( 'Job source', $source_options ),
                'employment' => array( 'Employment', $employment_options ),
                'work' => array( 'Working arrangement', $working_options ),
                'sector' => array( 'Sector', $sector_options ),
                'role' => array( 'Role family', $role_options ),
            ) as $filter => $option ) : ?>
                <label><?php echo esc_html( $option[0] ); ?>
                    <select class="sfex-<?php echo esc_attr( $filter ); ?>">
                        <option value="">All</option>
                        <?php foreach ( $option[1] as $name ) : ?>
                            <option value="<?php echo esc_attr( strtolower( $name ) ); ?>"><?php echo esc_html( $name ); ?></option>
                        <?php endforeach; ?>
                    </select>
                </label>
            <?php endforeach; ?>
            <label>Posted date
                <select class="sfex-date">
                    <option value="">Any date</option>
                    <option value="7">Last 7 days</option>
                    <option value="14">Last 14 days</option>
                    <option value="30">Last 30 days</option>
                    <option value="90">Last 90 days</option>
                    <option value="unknown">Not specified</option>
                </select>
            </label>
            <label>Sort
                <select class="sfex-sort">
                    <option value="newest">Newest first</option>
                    <option value="oldest">Oldest first</option>
                    <option value="title">Title A–Z</option>
                </select>
            </label>
            <button class="sfex-apply" type="button">Apply filters</button>
            <button class="sfex-reset" type="button">Reset</button>
        </div>
        <p class="sfex-count" aria-live="polite"><?php echo (int) count( $rows ); ?> source-observed records</p>
        <div class="sfex-table">
            <table>
                <thead><tr>
                    <th>Vacancy / description</th><th>Advertiser / sector</th>
                    <th>Role family</th><th>Location / working</th>
                    <th>Employment</th><th>Job source</th><th>Posted</th><th>Original job advert</th>
                </tr></thead>
                <tbody>
                <?php foreach ( $rows as $row ) : ?>
                    <tr class="sfex-row" data-search="<?php echo esc_attr( $row['haystack'] ); ?>"
                        data-source="<?php echo esc_attr( strtolower( $row['source_name'] ) ); ?>"
                        data-employment="<?php echo esc_attr( strtolower( $row['employment'] ) ); ?>"
                        data-work="<?php echo esc_attr( strtolower( $row['working'] ) ); ?>"
                        data-sector="<?php echo esc_attr( strtolower( $row['sector'] ) ); ?>"
                        data-role="<?php echo esc_attr( strtolower( $row['role'] ) ); ?>"
                        data-posted="<?php echo esc_attr( 'Not specified' === $row['posted_uk'] ? '' : $row['posted_iso'] ); ?>">
                        <td><strong><?php echo esc_html( $row['title'] ); ?></strong>
                            <details class="sfex-summary">
                                <summary>Job description summary</summary>
                                <p><b>Responsibilities:</b> <?php echo esc_html( $row['responsibilities'] ); ?></p>
                                <p><b>Requirements summary:</b> <?php echo esc_html( $row['requirements'] ); ?></p>
                                <p><b>Technical tools mentioned:</b> <?php echo esc_html( $row['skills'] ?: 'Not specified in captured advert.' ); ?></p>
                                <?php if ( $row['excerpt'] ) : ?>
                                    <p><b>Source advert excerpt:</b> <?php echo esc_html( $row['excerpt'] ); ?></p>
                                <?php endif; ?>
                            </details>
                        </td>
                        <td><?php echo esc_html( $row['advertiser'] ); ?>
                            <small>Sector: <?php echo esc_html( $row['sector'] ); ?></small>
                            <?php if ( $row['client'] && $row['client'] !== $row['advertiser'] ) : ?>
                                <small>Client: <?php echo esc_html( $row['client'] ); ?></small>
                            <?php endif; ?>
                        </td>
                        <td><?php echo esc_html( $row['role'] ); ?></td>
                        <td><?php echo esc_html( $row['location'] ); ?><small>Working: <?php echo esc_html( $row['working'] ); ?></small></td>
                        <td><?php echo esc_html( $row['employment'] ); ?></td>
                        <td><?php echo esc_html( $row['source_name'] ); ?></td>
                        <td><?php echo esc_html( $row['posted_uk'] ); ?></td>
                        <td><?php if ( $row['url'] ) : ?>
                            <a href="<?php echo esc_url( $row['url'] ); ?>" target="_blank" rel="noopener noreferrer">View original advert ↗</a>
                            <?php else : ?>Link unavailable<?php endif; ?>
                        </td>
                    </tr>
                <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </section>
    <style>
    .sfex2{background:#0b182f;color:#e8effb;padding:22px;border-radius:14px;font-family:system-ui,sans-serif}
    .sfex2 h2{color:#fff}.sfex2 .sfex-notice{color:#ffe4a8;border:1px solid #a58035;border-radius:9px;padding:12px}
    .sfex2 .sfex-controls{display:flex;gap:9px;flex-wrap:wrap;align-items:end;margin:15px 0}
    .sfex2 .sfex-controls label{font-size:12px;flex:1 1 145px;min-width:135px}
    .sfex2 .sfex-controls label:first-child{flex:2 1 260px}
    .sfex2 input,.sfex2 select{box-sizing:border-box;display:block;background:#142944;color:#fff;border:1px solid #3c5476;border-radius:8px;padding:11px;width:100%}
    .sfex2 button{border:0;border-radius:8px;padding:11px;background:#b7fe52;color:#091a30;cursor:pointer;font-weight:700}
    .sfex2 .sfex-count{font-size:13px;color:#c6d7ef}
    .sfex2 .sfex-table{overflow-x:auto}.sfex2 table{border-collapse:collapse;width:100%;min-width:1000px}
    .sfex2 th,.sfex2 td{text-align:left;vertical-align:top;border-bottom:1px solid #314963;padding:13px;font-size:13px}
    .sfex2 th{background:#1a2d4b}.sfex2 small{display:block;color:#adbed1;margin-top:5px}
    .sfex2 a,.sfex2 .sfex-summary summary{color:#b7fe52}.sfex2 .sfex-row[hidden]{display:none}
    .sfex2 .sfex-summary{border-top:1px solid #314963;margin-top:9px;padding-top:7px;max-width:340px}
    .sfex2 .sfex-summary summary{font-weight:700;font-size:12px;cursor:pointer}
    .sfex2 .sfex-summary p{font-size:12px;line-height:1.45;margin:8px 0}
    .sfex2 .sfex-summary b{display:block;color:#dce9fa}
    </style>
    <script>
    (function(){
        const root=document.getElementById(<?php echo wp_json_encode( $id ); ?>);
        if(!root)return;
        const q=root.querySelector('.sfex-q'),body=root.querySelector('tbody'),rows=[...root.querySelectorAll('.sfex-row')];
        const filters=['source','employment','work','sector','role'].map(key=>[key,root.querySelector('.sfex-'+key)]);
        const date=root.querySelector('.sfex-date'),sort=root.querySelector('.sfex-sort'),count=root.querySelector('.sfex-count');
        function apply(){
            const words=q.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
            const today=new Date(),utcToday=Date.UTC(today.getFullYear(),today.getMonth(),today.getDate());
            let visible=0;
            rows.forEach(row=>{
                const posted=row.dataset.posted,age=posted?Math.round((utcToday-Date.parse(posted+'T00:00:00Z'))/86400000):null;
                const inDate=!date.value||(date.value==='unknown'?!posted:posted&&age>=0&&age<=Number(date.value));
                const ok=words.every(w=>row.dataset.search.includes(w))
                    &&filters.every(([key,select])=>!select.value||row.dataset[key]===select.value)
                    &&inDate;
                row.hidden=!ok;if(ok)visible++;
            });
            rows.sort((a,b)=>sort.value==='title'
                ?a.cells[0].querySelector('strong').textContent.localeCompare(b.cells[0].querySelector('strong').textContent)
                :sort.value==='oldest'?(a.dataset.posted||'9999').localeCompare(b.dataset.posted||'9999')
                :(b.dataset.posted||'').localeCompare(a.dataset.posted||'')).forEach(row=>body.appendChild(row));
            count.textContent=visible+' of '+rows.length+' source-observed records';
        }
        root.querySelector('.sfex-apply').addEventListener('click',apply);
        root.querySelector('.sfex-reset').addEventListener('click',()=>{
            q.value='';filters.forEach(([key,select])=>select.value='');date.value='';sort.value='newest';apply();
        });
        [q,date,sort,...filters.map(([key,select])=>select)].forEach(input=>input.addEventListener(input===q?'input':'change',apply));
        apply();
    })();
    </script>
    <?php
    return ob_get_clean();
}

add_action( 'init', static function() {
    if ( function_exists( 'sfex_snapshot' ) && function_exists( 'sfex_safe_link' ) ) {
        add_shortcode( 'sf_phase1_live_explorer', 'ukba_sf2_render_shortcode' );
    }
}, 50 );
