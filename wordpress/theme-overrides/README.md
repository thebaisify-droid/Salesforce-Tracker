# Salesforce Phase 2 live-feed presentation

The versioned renderer in `inc/sf-explorer-presentation.php` is deployed into the existing
ZarafyTek Vacancy Radar WordPress theme (not a replacement for the installed
`sf-phase1-snapshot-explorer` plugin).

The theme bootstrap must include this line after its existing inc/actions.php include:

```php
require_once get_theme_file_path( 'inc/sf-explorer-presentation.php' );
```

The renderer overrides only the `[sf_phase1_live_explorer]` shortcode at WordPress
`init` priority 50. It calls the plugin's original `sfex_snapshot()` quality,
freshness and safety gate and `sfex_safe_link()` allowlist. It does not fetch data,
run Apify, rewrite source URLs, mark jobs verified or update stored snapshots.

`tracker/store.py` exports bounded `job_summary` fields from captured advert
descriptions and existing specialisms. Responsibilities and requirements are
filled only from explicitly headed advert sections; missing sections remain
labelled and short source excerpts are shown. No external summarisation call.

For deployment, preview the theme draft, verify the source-observed fallback and
original 47-record archived view, take a host-level backup, then explicitly
approve theme publication. Validate a fresh QA-passed feed separately: UK dates,
no Skills column, expandable descriptions, source URLs, search and filters.
No paid refresh is required for the code change itself.
