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
