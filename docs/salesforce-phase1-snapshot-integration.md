# Phase 1 Salesforce WordPress snapshot integration — staged

Adds standalone, **not yet installed** shortcode plugin at
`wordpress/sf-phase1-snapshot-explorer/sf-phase1-snapshot-explorer.php`.

## Operation
- Read only `wp-content/uploads/salesforce-tracker/live-data.json`, which is
  written atomically by the separate authenticated receiver after source QA.
- Require `salesforce-hiring-dashboard/v1`, QA pass, successful refresh,
  bounded counts and 36-hour freshness; reject symlinks and oversize payloads.
- Render source-observed rows in a Phase 1 dark explorer with search, source,
  employment and work arrangement, Apply and Reset controls.
- Escape rendered values and restrict outgoing job links to known source hosts.
- If local file missing, invalid or stale, render an explicit unavailable
  notice rather than a false current vacancy count.
- **No independent vacancy availability claim**; source ACTIVE means observed
  by collection, not verified currently open.

## Release limitations / follow-up
1. Current public Phase 1 WordPress page #85 remains a static 33-row research
   preview. Installing this addon does NOT modify it. Page can later be edited
   to include shortcode `[sf_phase1_live_explorer]` after safe preview tests.
2. The existing receiver allows only snapshots meeting freshness/quality
   requirements, but the current scheduled workflow produces GitHub artifacts
   only. No automatic handoff/publishing is enabled or approved.
3. If the feed is stale, this shortcode shows an unavailable notice; retaining
   the existing page #85 content as a fallback requires a separate safe
   template integration before replacing that page.
4. All source field values are used as delivered. Unknown employment, skills,
   sector and work mode stay explicitly unspecified.
5. Any future authenticated publication must verify the receiver contract and
   validate a new current snapshot. Do not deliver the stale 10 October JSON.
6. No new paid Apify acquisition is authorised by this PR.

This is **staged integration code**. Deploy only after an administrator
reviews a fresh site backup and the WordPress staging/preview behaviour.
