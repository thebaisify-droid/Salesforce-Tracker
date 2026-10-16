# UK Business & Technology Jobs Tracker — $25 acquisition trial

**Status:** staged on a feature branch, not live; never merge or enable paid acquisition until every gate below passes.

## Scope
This product covers **all 22 registered families** in `config/business_product_delivery_security_taxonomy_v1.0.json`. The old Business Analysis label is not the acquisition scope. Neither volume of BA ads nor raw total job count substitutes for family coverage.

## Approved shared trial budget
- Account-level Apify hard cap must be **exactly $25/month**, independently configured in the Apify console. Repository changes **cannot** change that limit.
- Preserve **$8** for Salesforce. BA allocation must remain <= **$17/month**.
- BA currently schedules nine Tuesday/Friday 07:35 UK slots at most; each may request up to **$1.80**, therefore scheduled upper bound **$16.20/month**. Per-source caps: CV-Library $0.65; Totaljobs $0.35; Reed $0.20; Indeed $0.35; JobServe $0.25.
- **$50 is a future option, not an approved or active limit.** It needs separate billing review and authorisation. Charge floors, platform usage, other Apify activities and source-level actual receipts must be audited.
- Zero auto retries; all five sources must succeed and pass QA; previous published data remains if anything fails. Keep the source-observed (not employer-confirmed-open) wording.

## Acquisition experiment
- Starting upper bound: **up to 30 requested items per source per slot**, not the blanket 10. The result request is reduced automatically for any per-dataset-item Actor when 30 items would exceed that Actor's charge cap.
- Five sources get **different family-specific queries** per scheduled slot; all 22 have an acquisition opportunity within five eligible slots. Individual Actors still run once each per refresh; no blanket assumption that they accept multi-keyword query syntax.
- `maxItems`, source input result caps, `maxTotalChargeUsd`, a live pre-POST account-usage read, and the $8 reserve are applied for every Actor. Completed dataset item counts must not exceed the requested maximum. Cap-exhaustion and failed Actors are **not** automatically retried.
- **Limitations:** This is acquisition *coverage across time*, not yet 22-family *display coverage*. The current WordPress receiver and current QA path require every displayed record to match only the five current run IDs. Publishing just the latest rotated slot would remove other families from the public dashboard.

## Release blocker: rolling 22-family vacancy retention
`rolling_coverage_enabled=false` is an intentional fail-closed release gate.
Before any paid trial acquisition using the new plan:
1. Design and test multi-refresh accumulation of accepted, source-observed records. Store canonical source IDs, advert URLs, original run IDs/datasets, first/last observation and ageing policy; never fabricate a later observation or open status.
2. Modify the WordPress receiver and QA contracts to accept a current, five-source refresh **plus bounded historical provenance**. Verify checksum, stale-record expiry labels, deduplication, source-specific run identities, authenticated ingestion and rollback. Avoid publishing stale rows as freshly observed or active.
3. Prove all 22 families can remain visible when family-specific searches rotate, even if the latest five source queries are for other families. Coverage dashboards should show 1/7/30-day counts, gap reasons and observed dates by family.
4. Reconcile JobServe's previous requested-versus-delivered item discrepancy and confirm Actor pricing/minimum charge; verify Apify hard account limit **$25**, not $19 and not $50.
5. Confirm Salesforce is not impacted; review GitHub Actions execution and passing tests; enable paid refresh only once the rolling snapshot is safe. Never infer that connecting a paywall itself licenses resale of source adverts.

## Commercialisation decision gates
Track paid Actor cost per **accepted, relevant, deduplicated** advertisement, distribution across the 22 families, source and job-link quality, posting-date availability, source freshness, missing sectors, and external advert link validity. Review at least several UK scheduled cycles before budget expansion.

A paid service requires verified job-board data licensing/redistribution rights, UK GDPR/privacy and retention review, resilient source quality, real user value, subscription billing, refund/cancellation policy and server-side **authenticated entitlements**. Do not rely on hiding public WordPress HTML/JSON or JavaScript-only controls to protect premium vacancies. Keep the Salesforce product separate until business terms and service tiers are defined.
