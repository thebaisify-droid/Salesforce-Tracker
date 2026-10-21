# Shared acquisition stage 2: release readiness (21 October 2026)

**Read-only, staged in PR #153.** No new paid refresh, production schedule change or WordPress publication.

## Implemented in staging

- Metadata-only verified dataset ledger: scripts/shared_acquisition_ledger.py.
- Full Apify run/dataset GET verification and content digest before dataset reuse.
- Portable integrity-protected state ZIP: scripts/shared_ledger_archive.py. It contains only the ledger and SHA-256 manifest, validates archive member paths and content and refuses overwriting existing state. It does not automatically download prior GitHub Actions artifacts yet; cross-run persistence is **not yet live**.
- Independent raw-record handoff: scripts/shared_acquisition_handoff.py. Salesforce and BA receive separate copies; neither is approved for publication by this handoff.
- Tue/Fri 07:15 UK, DST aware, no-retry **prospective only** gate in scripts/shared_acquisition_schedule.py.
- Offline unit tests. The original Salesforce Tue/Thu and BA paused Tue/Fri production workflows are unchanged.

## Blocking requirements before activating one paid acquisition scheduler

1. Salesforce synchronous Apify Actor/Task endpoints currently provide rows without authoritative run IDs or dataset IDs. Convert to an explicitly authenticated run-ID/dataset-ID protocol, keeping existing source QA, charge caps and no-retry behaviour. Do not modify existing live collectors until a shadow pipeline passes.
2. Wire the ledger ZIP to artifact upload+verified restore between runs of one serialized workflow. Stop rather than launch a duplicate paid Actor if its prior receipt is missing or unclear.
3. Immediately before EACH paid Actor POST, read actual Apify account cap/usage and supported Actor pricing, enforce EXACT $19 account hard cap, $8 Salesforce reserve, $11 BA allowance and approved per-run/source caps. Do not assume maximum requested results limits actual JobServe output: it can overshoot by a page.
4. Validate business role coverage across all 22 families and Salesforce scope on raw unfiltered datasets, and retain the direct JobServe API where appropriate. Same Actor ID does not prove the same underlying search.
5. Run distinct Salesforce and BA taxonomy, de-duplication and WordPress receiver end-to-end QA with shadow data before any publish. Retain each existing live last-good snapshot on partial failure.
6. Only then replace current production schedules with one Tue/Fri paid acquisition job, while disabling previous triggers in the SAME gated release. Never auto-retry paid runs.
7. Measure actual costs avoided from identical paid Actor starts skipped; with BA currently paused, $0 of verified savings should be claimed.

## Validation

Run offline commands: python -m unittest discover -s tests -v ; python -m scripts.shared_refresh_controller --audit.

No external live Actor/API starts or WordPress writes are implemented in this release.
