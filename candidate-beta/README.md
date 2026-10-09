# Candidate market — isolated research beta

## Scope

This beta is a **separate static preview** at `candidate-beta/index.html`, using only `candidate-beta/data/pilot-snapshot.json`. It does not modify `dashboard/live-data.json`, Wordpress, the existing Salesforce production publishing workflow, or any scheduled Apify execution.

The 30 source records were gathered in the successful one-off three-source pilot, with 10 each from Totaljobs, Indeed UK and JobServe. Employer/location are displayed only where observed in the previous review. **All 30 remain unverified for publication**, and the beta is not representative of UK hiring activity across the 22 planned role families.

For local preview: `python -m http.server 8000`, then open `http://localhost:8000/candidate-beta/`.

A separate hosting deployment must be reviewed and approved before exposing this page publicly. No production hostname or Wordpress route is changed by this PR.

## Integrated from the draft candidate tracker

This integration brings the offline taxonomy, classifier, isolated candidate store and candidate dashboard builder from draft PR #28, plus a standalone browser preview. Original PR #28 remains draft and may be closed or refactored **only after** confirming that all desired capabilities are represented. No automatic merge of PR #28 into Salesforce production is permitted.

## Release constraints

This is a research beta, not a go-live declaration. The separate 22-family release gate still requires unbiased sampling, validated active vacancies and posting dates, real-world precision/recall, cross-source deduplication, database restore testing, website filter testing and independent review. Any future paid Apify collection needs new budget/authorisation.

## Private preview artifact verification

On merges to `main` that modify files under `candidate-beta/`, the `Candidate beta offline preview` GitHub Actions workflow should run and retain a `candidate-beta-preview` ZIP artifact for 14 days. The ZIP is a **private review deliverable**, not a public deployment or evidence of verified job listings.

Reviewers should confirm the run is green, the artifact contains `candidate-beta/index.html`, `candidate-beta/data/pilot-snapshot.json`, and `candidate-beta/README.md`, then serve the extracted directory with a local static server and exercise title, source, provisional family and evidence filters. Confirm the beta warning persists and **zero** records display as publication-verified. Do not share the preview publicly.

A successful archive build alone does not prove browser rendering, links, vacancies or representative coverage. Record human browser QA and independent source evidence separately before requesting release approval.

## Beta handoff (9 October 2026)

The candidate beta is available as a **private GitHub Actions artifact**, not as a public hiring-data website. Open the latest successful **Candidate beta offline preview** workflow and download the **candidate-beta-preview** ZIP. Serve its extracted folder with `python -m http.server 8000` from the containing directory; then open `/candidate-beta/` in a browser. GitHub pull requests affecting this beta also build an artifact for review.

The dashboard's 30 listings are a historical demonstration only. All remain unverified for publication; do not make live hiring or market-share claims based on them.
