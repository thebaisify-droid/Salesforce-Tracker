# Phase 3 combined Salesforce + BA shadow bridge

## Staged in draft PR #153; no spending, no live publication

**Step 1 — Ledger checkpoint recovery across Actions runs.**
A manual-only workflow checks the most recent successful, same-branch and
same-workflow Actions artifact via GitHub GET. It downloads exactly that
artifact through actions/download-artifact, restores the checksum-validated
metadata-only ledger, and uploads a new checkpoint. The initial MANUAL
no-spend workflow may bootstrap an EMPTY ledger only. If a previously
reported artifact goes missing, the process blocks. No scheduled paid
workflow has been activated. GitHub Actions artifacts are retained for 30 days;
30-day gaps or 100+ matching artifacts block unsafe assumptions.

**Step 2 — Completed-run provenance integration.**
scripts/shared_completed_run_intake.py is a new GET-only adapter next to
existing paid Salesforce collectors and the paused BA collectors. It verifies
an existing SUCCEEDED run's Actor ID, Task ID if applicable, the full original
Actor INPUT, window timestamps, dataset ID, dataset metadata/count and full
untouched rows before building a reusable metadata receipt. It NEVER
dispatches an Actor. Raw-source quality must pass; then each consumer must
run its own vacancy-quality controls. A saved Task's resolved INPUT digest
must match too. Existing Salesforce run-sync endpoints do not expose a run
ID: migrating to an authenticated asynchronous start+poll+GET protocol is
still necessary before this becomes a fully automated producer.

**Step 3 — End-to-end offline QA.**
The existing Salesforce relevance and normalization functions and the
independent 22-family BA classifier both process the same sample data,
with overlap and taxonomy-family counts reported separately. The existing
five-board BA run_offline pipeline exercises stage, provenance, source QA and
WordPress delivery-preview packaging WITHOUT sending a snapshot. Unit tests
exercise wrong Actor/input, overshoot, failed QA, tampered/expired artifacts
and different consumer scopes. Classified sample success is not proof that
all 22 role families are covered in live acquisition.

**Live release blockers:**
- Stage the asynchronous/ID-preserving paid-source adapter behind the existing
  per-source and account limits; independently check live monthly used charges
  and Actor minimum/pricing before EACH paid launch. Existing direct JobServe
  API is not replaced.
- Demonstrate durable checkpoint recovery in a real manual Actions invocation,
  not just mock-tested code; protect against artifact retention expiry.
- Reconcile actual overlap of Salesforce queries and rotating 22-family BA
  searches with source-specific coverage and billed costs. Current exact
  matching configured queries: ZERO.
- Validate actual Salesforce database refresh and both separate WordPress
  receiver delivery paths in no-publish/shadow environments.
- Activate one Tue/Fri 07:15 UK paid scheduler ONLY after a verified release
  switching off old paid triggers in the same change. Preserve $19 total,
  $8 Salesforce reserve, $11 BA allowance and NO paid retries.

Existing live Salesforce and BA workflows are not modified. PR remains draft.
