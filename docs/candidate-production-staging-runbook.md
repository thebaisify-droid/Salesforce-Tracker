# Candidate staging and production release runbook

Status: **NO-GO for public release**. This is an operational checklist, not approval.

## Verified baseline — 9 October 2026

- Candidate research beta is separate from the live Salesforce dashboard.
- The snapshot contains 30 historical records, zero publication-approved vacancies, and no verified representative coverage.
- Private-preview ZIP creation and full browser filter checks still need recorded run evidence.
- A minimum of 100 independently human-labelled representative records is required by the existing release gate, together with 22-family coverage, cross-source deduplication, date/live-status evidence, source authenticity and independent reviewer sign-off.

## Safe staging procedure

1. Keep `candidate-beta/` on a private GitHub preview artifact or an access-controlled staging destination; do not expose a public URL or route.
2. Record the successful workflow run URL and downloaded ZIP manifest. Serve the ZIP's extracted `candidate-beta/` folder locally using a static web server.
3. Test source/title/family/evidence filters, zero-results message, narrow-screen layout, external link safety and visible unverified-data warning. Record screenshots and reviewer sign-off; do not infer a pass from unit tests alone.
4. Export the original 30-row review handoff with `python -m scripts.export_candidate_beta_review --output artifacts/candidate-human-review.csv`. Preserve unverified status until independent evidence is recorded.
5. Perform independent review: job title, employer, UK location, posting date, live vacancy, family mapping, duplicates and source-linked evidence. Escalate or exclude uncertain records.
6. For representative validation, obtain a fresh Apify usage reading, price/input schema confirmation, account spending cap of $19 with $8 protected Salesforce reserve, then obtain separately explicit authorisation for any paid collection. No automatic retries.
7. Run the release-readiness evaluator, full GitHub CI, database restore and browser navigation tests. Independent QA signs the results.
8. Open a separate deployment PR specifying staging/production hostname, security, rollback, monitoring, data provenance and approval. Do not deploy merely because checks pass.

## Release decisions

- **Current Salesforce tracker:** unchanged and remains live.
- **Private candidate beta:** limited internal review may continue, never describe its 30 unverified records as verified live hiring.
- **Public candidate dashboard:** blocked until the evidence and human approval gates above pass.

## Rollback

If later separately approved public deployment shows incorrect data, broken filtering or security issues, disable the candidate route/deployment, restore the previous artifact, and leave the Salesforce dashboard untouched. Preserve audit evidence and notify reviewers.
