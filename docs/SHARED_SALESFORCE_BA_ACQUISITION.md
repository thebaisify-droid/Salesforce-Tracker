# Shared Salesforce + Business Analysis acquisition — cost-controlled consolidation

## Audited state (20 October 2026)

- One repository contains both pipelines. The WordPress vacancy site has separate Salesforce and Business Analysis snapshot receivers.
- Salesforce guarded schedule: Tue/Thu 07:15 Europe/London, maximum five-source requested charge $0.90/cycle. Legacy daily schedule is separately disabled.
- BA guarded schedule: Tue/Fri 07:35 Europe/London, requested ceiling $1.20/cycle and $11/month. **The paid BA step is hard-disabled with `if: ${{ false }}`; the committed BA config is also paused.** Do not remove either stop during exploratory consolidation.
- Both controlled workflows already use concurrency group `shared-apify-acquisition`. This stops overlapping execution, **not double billing**.
- Shared Apify account user-approved ceiling is $19/month with $8 reserved for Salesforce. A legacy Salesforce budget preflight accepted $25 while BA required $19; this PR makes Salesforce fail closed unless the *actual* account limit equals $19.
- Salesforce CV-Library, Totaljobs and Reed run **saved Tasks**, whereas BA specifies different direct Actors. The other two providers name the same Actor IDs (Indeed, JobServe) but have **different role keywords, result limits and input fields**. **Zero currently configured exact input matches.** A claim of immediate financial savings from dataset reuse would be unsupported.

## Target architecture

One paid-acquisition controller owns schedule, headroom, source selection and provider-specific queries. Each resulting completed dataset is stored **once** in an immutable, shared acquisition ledger with:

`actor_or_task_identity`, `canonical_input_hash`, `search_window`, `run_id`, `dataset_id`, `item_count`, `dataset_sha256`, `completed_at`, `cost_evidence`, `source_name`, `QA_status`.

The Salesforce and BA consumers separately classify the very same full dataset, apply their own role taxonomies and QA rules, and atomically deliver to their existing WordPress receivers. They must never share a *filtered Salesforce-only* or *filtered BA-only* output as the general raw feed. On any failure, keep each receiver's last-good snapshot.

`scripts.shared_dataset_reuse` now provides a zero-spend compatibility audit and fail-closed receipt matcher. It is **not yet connected to paid execution**; no Actor launch is removed until end-to-end provenance and coverage are demonstrated.

## Implement in safe stages

1. **Current change, no spend:** lock the $19 cap in Salesforce preflight and config; audit exact request compatibility; assert reuse fails if any hash, time window, completion, dataset verification, QA or immutable record metadata differs. Add offline tests. Do not update live WordPress or turn on BA acquisition.
2. **Shared acquisition ledger:** refactor Salesforce synchronous Actor/Task collectors to retain actual run IDs, dataset IDs, completed metadata, actual input and cost evidence; preserve existing QA, per-provider spend guards and one-run/no-retry semantics. Make both pipelines read completed datasets through a single read-only consumer, keyed by immutable request fingerprint. Protect concurrent access with one ledger and serialization; Github Actions concurrency alone is insufficient for cross-job durable storage.
3. **Query coverage and cost pilot, separate approval:** evaluate source-by-source whether one broader search supports BOTH Salesforce and BA's 22-family rolling scope. Actor identity alone is insufficient. Check exact supported Actor input schema, result limits, minimum charge, overlapping listings, and API terms; retain existing direct JobServe API integration where it demonstrably avoids paid duplicate scrapes. Confirm sample data contains both segments without losing live vacancies. If not, keep distinct paid queries, but use one budget controller and avoid redundant completed requests.
4. **Single scheduler:** target **Tue/Fri 07:15 UK for collection** and publish Salesforce and BA independently as soon as each consumer passes QA. This changes Salesforce's existing Thu slot; require review of cadence and freshness before activation. BA's existing 07:35 UK publication target may be retained as a downstream step. Handle DST once at controller level. Disable original paid schedules *only after* shared workflow dry-run and the two publication routes are proven.
5. **Cost and freshness acceptance:** before EACH paid Actor, independently verify actual account hard cap exactly $19, used charges, residual reserve and current Actor pricing/minimums. Avoid excess item counts and automatic retries; if a result exceeds the authorised count, retain evidence and halt publication. Respect $8 Salesforce allocation and $11 BA monthly ceiling, with $0.90 Salesforce/source-cycle upper bound and $1.20 BA/cycle upper bound (subject to revised shared spend allocation that must not exceed $19). Record actual billed cost and avoided duplicates, not theoretical savings. Both dashboards should show `Last successful refresh`, `Last source observation` and no-change/skip status independently.

## Stop/go gates

**No activation** if: actor input mismatch; a cached dataset has no verified immutable provenance; missing job families; increased duplicate rejection; account limit != $19; reserve shortfall; unsupported billing model; missing source run metadata; unpublished unverified records; broken WordPress receiver; BA safety hold unresolved.

## Verification commands (all offline, free)

```bash
python -m scripts.shared_dataset_reuse --audit
python -m unittest tests.test_shared_dataset_reuse tests.test_salesforce_controlled_refresh_budget -v
```

## Financial reporting

Monthly baseline is *up to* 8–9 Salesforce cycles × $0.90 and 8–9 BA cycles × $1.20 **only if both were actually enabled**; BA is currently paused so do not treat hypothetical BA spend as a saving. Savings = measured cost of equivalent paid requests **not launched** because a qualifying raw dataset is re-used, minus any extra broad-search expense. Report actual account-usage deltas and source coverage side by side.
