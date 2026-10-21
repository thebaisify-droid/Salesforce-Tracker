# Phase 4 production-readiness evidence (read-only, 21 Oct 2026)

## Confirmed

- WPVibe read-only site and WordPress REST namespace metadata on 21 Oct:
  jobs.zarafytek.com has both Salesforce receiver 0.2.0 and Business
  Analysis receiver 0.3.6 active. The namespaced snapshot routes exist
  and accept POST only. GET on these POST-only routes is not a delivery
  test. Plugin source requires dedicated Salesforce capability
  sf_deliver_snapshot and BA capability ba_deliver_snapshot; these
  delivery permissions were not independently authenticated in this
  Phase 4 probe. Existing Salesforce controlled workflow run 39388674098
  had previously authenticated its sender and delivered on 20 Oct.
  BA sender authenticated live capability remains unproven this run.

- FINANCIAL STOP: authenticated prior GitHub Actions Salesforce budget
  preflight log from run 39388674098, 20 Oct 2026 at 07:46:01 UTC:
  account_limit_usd = 25, account_usage_usd = 10.866026027112321.
  Actual configured Apify hard cap was $25, not the approved $19.
  These old values are not a live reading and must not be used for
  next-run headroom decisions. The strict $19 check is in draft PR #153
  only, not main. Change actual Apify account spending limit to $19,
  then obtain a fresh authenticated users/me/limits reading immediately
  before every paid Actor while preserving $8 Salesforce and $11 BA
  allocations. No paid activation while mismatch persists.

- Independent Apify run read-only checks confirmed:
  Indeed run i6unDcLG8Qh1XSftt SUCCEEDED, dataset ssJHtekdlbvmP2UCZ
  with 10 items, finished 15 Oct 13:39:51 UTC; CV-Library run
  qo9YEfFlbYaV31MkK SUCCEEDED, dataset OD5lSdCGHaw4q1D4j
  with 10 items, finished 15 Oct 13:38:38 UTC; JobServe run
  q43qj80CzgOjKP3Qb FAILED, 0 rows. The successful datasets are too
  old for the maximum 24h reuse window today; original effective
  search input and full canonical SHA still require separate GET
  checks before a ledger receipt can be recorded.

- Actor Store pricing metadata (Bronze, read-only) identifies a
  per-start Totaljobs event of $0.07, JobServe start $0.005,
  Indeed result $0.0036, CV-Library result $0.0015, Reed result
  $0.00085. This does not establish actual billed charge or fresh
  account usage. BA JobServe historically overshot maxResults;
  its paid schedule remains hard disabled.

- scripts.ba_acquisition_planner plans five distinct searches per
  refresh across a 22-family rolling taxonomy. Five idealized slots
  offer 22 distinct role-family search opportunities, but DO NOT prove
  all role families have fresh matching vacancies. Existing configured
  Salesforce/BA source requests have zero exact full-input matches.

- GitHub CI verified Phase 3 source-replay and archive unit tests,
  NOT a real successful workflow_dispatch checkpoint restore
  on main with previous Actions artifact. Manual shadow rehearsal
  remains outstanding; the draft PR workflow is not live.

## Release decision

BLOCKED. Keep PR draft, current production schedules unchanged,
BA paid collection paused, zero new Apify or WordPress POSTs.
No verified monetary savings should be claimed.

New offline command:
python -m scripts.shared_phase4_readiness --output state/phase4-readiness.json

Current pre-release requirements: user corrects actual Apify limit from
$25 to $19; perform fresh authenticated account/Actor price check;
complete two sequential manual no-spend ledger checkpoint tests on
the release branch; verify both dedicated WordPress delivery identities
without publishing; test actual full existing-run input+dataset SHA;
measure BA family coverage and source overlap before any dual reuse;
prepare an atomic paid-schedule cutover after all other gates pass.
