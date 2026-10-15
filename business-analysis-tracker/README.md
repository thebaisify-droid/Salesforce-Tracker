# Business Analysis Tracker — published historical vacancy explorer

**Public WordPress page:** https://jobs.zarafytek.com/?page_id=49 (WordPress post ID 49). The legacy research beta iframe was bypassed on this page only by setting `_wp_page_template=page.php`; WordPress retains the custom historical template as a potential rollback. The duplicate preview page 155 has been returned to **draft** status. No Salesforce theme or source file was altered.

## Dataset — 15 October 2026 publication

The displayed snapshot is **historical, source-observed and not guaranteed open**. It is not a live refresh and must not be used as a representative hiring-market estimate.

- Existing 8 October three-source pilot: 30 archived rows from Totaljobs, Indeed UK, JobServe; 25 matched the role-family taxonomy.
- Three *already completed* targeted Indeed UK cyber pilots: 15 + 10 + 10 rows. 11 title-matched BA or Cyber roles, 24 excluded.
- **65 historical source rows examined; 36 source-advertisement matches retained; 29 excluded.** URLs are unique within the snapshot, but **cross-job-board identity deduplication is not verified**.
- 22 specific role families, with an umbrella **Information Security / Cyber Security** dropdown grouping seven specific families. Only 10 families have records in this limited sample.
- All 36 original job-board URLs are shown. Some may be closed, stale or redirected.
- Source-posting dates: captured for 11 of 36 advertisements (UK dd/mm/yyyy); the other 25 show *Not specified*.
- Description snippets are shown only when present in the historical source. Working arrangement, contract type and sector remain *Not specified* rather than invented.
- Source advertiser is not independently established to be the actual end employer. Historical QA Ltd apprenticeship rows may describe a training provider, not the hiring organisation.
- **No paid Apify runs** were started, and the protected $19 monthly budget / $8 Salesforce reserve were not changed.

## Reproduce and test

```bash
python -m scripts.build_ba_tracker_existing_pilot
python -m unittest discover -s tests -p test_ba_tracker_existing_pilot.py -v
```

Inputs: `candidate-beta/data/pilot-snapshot.json`, `business-analysis-tracker/data/completed-cyber-pilots.json`. Output: `business-analysis-tracker/data/preview-snapshot.json`. All actions are offline and read-only with respect to Apify. This PR carries neither a scheduled BA collector nor a WordPress publication action.

WordPress public readback confirmed 36 rendered table rows, 36 external advert links and the full selector. The filter JavaScript is present in the page, but browser *click* testing across controls was not independently evidenced by this connector. A static server-rendered row fallback ensures vacancies are visible without JavaScript.

## Rollback

- Restore page 49's prior revision or replace its content with the previous one-paragraph research beta.
- Revert post meta `_wp_page_template` on page 49 to `page-business-analysis-tracker.php` if the legacy iframe must be shown. The theme itself was not changed.
- Existing Salesforce publishing, page 31 and its source pipeline remain untouched.

## Next phase — controlled fresh refresh (NOT enabled)

Independent Business Analysis/Delivery/Product/Cyber keyword search profiles, source-specific schema and costs, the protected $19 Apify ceiling and $8 Salesforce reserve must be checked before new runs. The previous Salesforce-focused datasets cannot be treated as representative BA searches. New paid Apify collection requires separate explicit approval and a bounded one-off pilot. Configure a separate BA feed and delivery path without changing Salesforce workflows. Do not label source-observed advertisements confirmed active without corresponding current evidence; individual employer verification is not a prerequisite for the source-observed dashboard.
