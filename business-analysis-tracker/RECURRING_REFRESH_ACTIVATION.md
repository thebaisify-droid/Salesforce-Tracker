# UK Business Analysis controlled recurring acquisition — activation gate

## Deployment state (15 October 2026)

A dedicated GitHub workflow now has *twice-weekly* Tuesday/Friday schedules at **07:35 Europe/London**, expressed as two UTC cron candidates with a timezone/DST gate. It runs a **no-cost preflight by default** and shares the acquisition concurrency group with Salesforce.

**Paid recurring acquisition is not active until all four independent controls are true:**

1. `business-analysis-tracker/config/automated_refresh_pipeline.json`: `enabled=true`, `paid_acquisition_enabled=true`, `scheduling_enabled=true`, `recurring_budget_approved=true`, `pricing_guard_verified=true`, and `wordpress_delivery_enabled=true` only if approved for automatic publishing.
2. The optional GitHub Actions repository variable `BA_CONTROLLED_REFRESH_ENABLED` must not be `false` (emergency pause). Otherwise committed approval flags control activation; disabled paid steps are automatically skipped.
3. Live Apify GET confirms the account limit is exactly $19 and that the $8 Salesforce reserve plus the remaining per-run BA cap are available.
4. Current per-Actor pricing definitions validate the declared result-charge limits before the first Actor launch, or no paid request is sent.

**Proposal, not standing authorisation:** up to $1.20 per successful full five-source refresh, 10 requested results per source, with per-source caps CV-Library $0.50, Totaljobs $0.20, Reed UK $0.15, Indeed UK $0.20, JobServe $0.15. Up to nine Tue/Fri slots per calendar month = $10.80 in requested ceiling amounts, under an $11 BA allocation, within the shared $19 Apify limit with an $8 protected Salesforce reserve. This is not a guarantee of actual billing for actors whose charging model is unknown. Actual account and actor charge details must satisfy the runtime guards before every paid launch.

## What happens after approval and activation

- Two UTC cron events accommodate UK daylight saving; only the one matching 07:35 UK executes a paid run. GitHub workflow reruns and manual dispatch **cannot** start paid acquisition.
- Acquire each source **once** using the standard Apify API (never JobServe MCP), no retries and no shared Salesforce saved Task changes.
- Verify account balance and protected Salesforce reserve immediately before every individual Actor POST. The workflow uses the same GitHub Actions concurrency group as Salesforce.
- GET completed source datasets, confirm Actor ID, run success and item-count integrity. Normalize/classify only the 22-family role taxonomy, preserve original HTTPS advert links, include source-based sectors, flag possible duplicates instead of deleting uncertain cases.
- Require all five sources to yield matching qualifying records. A failed/empty/incomplete source, invalid URLs, unsupported price model or WordPress rejection **preserves the last published snapshot**.
- If WordPress delivery is separately enabled: build the schema `ba-live-snapshot/v1` with genuine current run IDs, observed timestamps and explicit source-observed-not-employer-confirmed caveat. Send a single checksum-verified snapshot to the isolated, authenticated BA receiver. Page 49's installed v0.2 bridge renders it and retains its embedded content as a fallback.
- No destructive changes to Salesforce, no refunds or retries invented, no fabricated "verified currently open" status.

## Limitations

The initial refresh query is `business analyst` on each board. This does not yet provide balanced coverage of the remaining product, delivery, data and cyber families. A future approved acquisition plan must rotate family-specific searches, with distinct cost controls. The original 57 published advertisements remain available until a truly fresh five-source QA-passed snapshot replaces them.

**Current status: scheduled no-cost preflight staged, but recurring spending and automatic publishing intentionally disabled pending explicit ongoing monetary authorisation and verification of each Actor's charge model.** Past pilot approvals were one-time only and cannot be repurposed into standing recurring spend.
