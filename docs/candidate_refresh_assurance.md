# Candidate tracker — controlled-refresh assurance (inactive)

This change adds **review-only aggregate quality gates** for the UK Business,
Product, Delivery and Cyber Security tracker. It neither schedules scraping nor
publishes a BETA dataset and does not modify the existing Salesforce tracker.

## Quality controls

- Parse known Apify posting-date formats. The proposed freshness window is
  seven days; undated, future-dated and older postings are tallied separately.
  Posting recency is **not** evidence that a vacancy is currently open.
- Preserve URL duplicates and conservative title + employer + location matches
  **as review flags**. Do not silently collapse different job boards' listings
  or infer advertiser identity from missing details.
- Flag ambiguous classifications for independent reviewer assessment.
- Do not count CV-Library expiry events as vacancies or apply them automatically.
- Output only aggregate QA metrics. No emails, contact names or job descriptions
  are embedded in the report.
- Set publication and acquisition flags to false in every response.

The 22-family keyword examples in
\`config/candidate_refresh_search_profiles.example.json\` are proposals only.
They are **not validated Actor inputs** and authorize zero Apify spending.

## Example (offline, no provider calls)

\`\`\`python
from datetime import date
from scripts.candidate_refresh_assurance import assess_refresh_quality
result = assess_refresh_quality(candidate_rows, as_of=date(2026, 10, 14))
assert result["publication_approved"] is False
\`\`\`

This quality assessment must be reviewed alongside authentic source-run
provenance, live employer-side vacancy evidence, cross-source duplicate
adjudication, at least 100 independently labelled records and the existing
release-readiness gates before proposing any publication or scheduled refresh.
The $19 account ceiling and $8 Salesforce reserve remain unchanged.
