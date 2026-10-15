# UK Business Analysis controlled recurring acquisition — activation gate

## Deployment state (15 October 2026)

A dedicated GitHub workflow has *twice-weekly* Tuesday/Friday schedules at **07:35 Europe/London**, expressed as two UTC cron candidates with a timezone/DST gate. It performs a no-cost preflight before any paid run and shares the acquisition concurrency group with Salesforce.

**Standing authorisation received 15 October 2026:** up to $1.20 per refresh and $11 per month for Business Analysis, under the shared $19 cap and $8 protected Salesforce reserve. The following four controls are required on every scheduled run:

1. The committed active config now sets `enabled=true`, `paid_acquisition_enabled=true`, `scheduling_enabled=true`, `recurring_budget_approved=true`, `pricing_guard_verified=true`, and `wordpress_delivery_enabled=true`. The legacy `five_source_refresh.json` is historical, disabled pilot documentation only.
2. The optional GitHub Actions repository variable `BA_CONTROLLED_REFRESH_ENABLED` must not be `false` (emergency pause). When not paused, committed approval flags control activation.
3. Live Apify GET confirms the account limit is exactly $19 and that the $8 Salesforce reserve plus the remaining per-run BA cap are available.
4. Current per-Actor pricing definitions and publisher-declared minimums validate the caps before the first launch. Apify's current [Run Actor API](https://docs.apify.com/api/v2/actors-runs-post) documents `maxTotalChargeUsd` as a maximum **total run charge for all pricing models**, including Actors which additionally bill platform usage; do not infer an uncapped run solely from `isPPEPlatformUsagePaidByUser=true`. Any unsupported model or minimum above the user-approved cap blocks the entire refresh before launch.

**Authorised standing ceiling:** up to $1.20 per full five-source refresh, 10 requested results per source, with per-source caps CV-Library $0.50, Totaljobs $0.20, Reed UK $0.15, Indeed UK $0.20, JobServe $0.15. Up to nine Tue/Fri slots per calendar month = $10.80 in requested ceiling amounts, under an $11 BA allocation, within the shared $19 Apify limit with an $8 protected Salesforce reserve. This is not a guarantee of actual billing for actors whose charging model is unknown. Actual account and actor charge details must satisfy the runtime guards before every paid launch.

## What happens after approval and activation

- Two UTC cron events accommodate UK daylight saving; only the one matching 07:35 UK executes a paid run. GitHub workflow reruns and manual dispatch **cannot** start paid acquisition.
- Acquire each source **once** using the standard Apify API (never JobServe MCP), with `maxTotalChargeUsd` on every Actor POST, `restartOnError=false`, no automatic retries, and no shared Salesforce saved Task changes.
- Verify account balance and protected Salesforce reserve immediately before every individual Actor POST. The workflow uses the same GitHub Actions concurrency group as Salesforce.
- GET completed source datasets, confirm Actor ID, run success and item-count integrity. Normalize/classify only the 22-family role taxonomy, preserve original HTTPS advert links, include source-based sectors, flag possible duplicates instead of deleting uncertain cases.
- Require all five sources to yield matching qualifying records. A failed/empty/incomplete source, invalid URLs, unsupported price model or WordPress rejection **preserves the last published snapshot**.
- If WordPress delivery is separately enabled: build the schema `ba-live-snapshot/v1` with genuine current run IDs, observed timestamps and explicit source-observed-not-employer-confirmed caveat. Send a single checksum-verified snapshot to the isolated, authenticated BA receiver. Page 49's installed v0.2 bridge renders it and retains its embedded content as a fallback.
- No destructive changes to Salesforce, no refunds or retries invented, no fabricated "verified currently open" status.

## Limitations

The initial refresh query is `business analyst` on each board. This does not yet provide balanced coverage of the remaining product, delivery, data and cyber families. A future approved acquisition plan must rotate family-specific searches, with distinct cost controls. The original 57 published advertisements remain available until a truly fresh five-source QA-passed snapshot replaces them.

**Activation status:** user authorised standing BA caps on 15 October 2026; the committed configuration and scheduled WordPress publication gate are enabled. The first occurrence must pass fresh account usage, price-model minimum, platform-compute fee and dedicated WordPress access checks. If any guard fails, the run stops without publishing and keeps the prior 57-observation snapshot. One-time pilot approvals remain separate.
