# Apify budgeted data acquisition (initial controls)

This rollout does **not** enable any new sources or publish changes. Merge after CI and Apify account controls are checked.

## Proposed budget (USD)
- Target monthly acquisition reservation ceiling: **$30** across this GitHub workflow.
- Mandatory Apify console account-level spending/usage limit: set separately to **$30 or lower** if the plan allows. The repository cannot configure the account limit.
- Per-run maximum charges: CV-Library $0.15, Totaljobs $0.15, Reed $0.15, Indeed UK $0.20, JobServe $0.25.
- Results cap: 100 per core Task, 75 per secondary Actor. Pay-per-result cap is **not** an output size guarantee.
- Salesforce broad query remains configured for the source actors; saved Apify Tasks should be checked in Apify Console to ensure one Salesforce query only.
- Incremental window 48 hours (overlap guards against missed postings). Full scraping may still occur upstream when a saved Task lacks a date filter.
- JobServe runs Monday/Wednesday/Friday in UTC; others daily.

## How it works
Before each Apify call, the collector reserves the **maximum** USD run charge to `state/apify_budget_ledger.ndjson`. If that month's accumulated reservations would exceed $30, the collector emits an empty dataset and does not start that actor. Config validation refuses Apify sources without a positive run charge limit. Existing pipeline metrics remain unchanged.

**Reservations are conservative estimates, NOT actual cost**. They may overcount usage and do not measure unique new vacancies or true cost per vacancy. Source-level `usageTotalUsd`, deduplication yield metrics and accurate monthly invoicing reconciliation remain follow-up work.

**Persistence warning:** The current workflow restores the last successful state artifact; a failed GitHub run can incur Apify spend that is not reflected in the next restored reservation ledger. GitHub state retention is 90 days, and manual/other Apify runs are not represented. For that reason the actual account-level Apify spending/usage limit is essential, and the $30 repository guard must not be described as a guaranteed account spending limit. Treat the system as safety-limited pending billing reconciliation and test-run validation.

Review Actor parameter support, pricing, task saved inputs, and Apify plan minimums before merging. If a low per-run cap prevents collection, do not silently increase caps; review actual yield and cost first.
