# UK Business & Technology Jobs Tracker — 16 October offline acquisition-quality audit

**Status:** read-only post-run review. **Not approved for publication; recurring BA paid acquisition remains paused.**  
Evidence: five previously completed Actor datasets from [failed manual workflow #38887998367](https://github.com/thebaisify-droid/Salesforce-Tracker/actions/runs/38887998367); the privacy-trimmed dataset snapshot is on this feature branch. Existing source-observed WordPress snapshot remains unaffected.

## What was collected and what was relevant?

| Job board | Raw rows from completed dataset | Title-family matches | Match rate | Planned query family |
| --- | ---: | ---: | ---: | --- |
| CV-Library | 30 | 8 | 26.7% | Security Management |
| Totaljobs | 25 | 4 | 16.0% | IT Security |
| Reed UK | 30 | 12 | 40.0% | Business Analysis |
| Indeed UK | 30 | 17 | 56.7% | Data Analysis |
| JobServe | 46 | 41 | 89.1% | Business Intelligence |
| **Total** | **161** | **82** | **50.9%** | Five rotating searches |

The 82 are **candidate title-family matches** under the existing 22-family classifier, not employer-confirmed current vacancies. The 79 excluded rows failed that title-family classification. This count is not an independently verified job-board market census.

### Distribution of 82 candidate titles

| Family | Candidates |
| --- | ---: |
| Business Analysis | 46 |
| Data Analysis | 17 |
| Information Security Analysis | 4 |
| Data & Analytics Management | 3 |
| Security Management | 3 |
| Security Consulting & Advisory | 2 |
| Delivery Management | 2 |
| Business Change & Transformation | 1 |
| Business Process & Operational Analysis | 1 |
| Product Management | 1 |
| Project Management | 1 |
| Service Management & Design | 1 |

**12 of 22** families have matching titles in these datasets. The ten missing families are: Business Intelligence, Product Ownership, Agile / Scrum, Programme & Portfolio Management, Agile Leadership, Product Strategy & Operations, Security Operations / SOC, Security Architecture, Security Risk & Third-Party Risk, and IT Security.

In particular, the JobServe `business intelligence analyst` search produced 41 candidate matches but **none classified as the Business Intelligence family**; many matches belong to the Business Analysis or Data Analysis families. This is an evidence-based sign that search phrases and title taxonomy need targeted QA, not a reason to force all results into their requested query family.

### Commercial data-quality defects

- Evidence-supported advertiser sector: **0 / 82**. Do not fabricate end-client industries based on occupation or recruiter.
- Posting date: **82 / 82** retained candidates have a usable source date; source-observed is not the same as employer-confirmed open.
- Working arrangement: **9 / 82** available by current strict mapping. Hybrid arrangements may exist in free-text excerpts, but require explicitly evidenced extraction.
- One retained candidate matched the non-vacancy/training promotional pattern; review separately rather than treating it as a confirmed employer vacancy.
- Zero exact-URL or strong three-field (title/advertiser/location) duplicates were flagged by the offline classifier, **not proof** that these are 82 independently unique positions.

## Why did JobServe exceed maxResults?

**Source documentation confirms this is an Actor contract nuance, not necessarily a scraper defect.** The exact installed Actor `solidcode/jobserve-scraper` documents for `maxResults`:

> Results are fetched a page at a time, so a small cap can return up to a full page more than you asked for.

The input was `maxResults:30`; the dataset contained **46** jobs, 46 distinct URLs. A prior run had 24 from 20. The initial GitHub workflow logged 24 JobServe rows, 0 Reed and 29 Indeed, but post-run read-only datasets settled at 46, 30 and 30 respectively. These observations demonstrate temporal dataset-count drift, **not** why the data changed after its first read.

At the observed Bronze event pricing, JobServe advertises **$0.00285 per result** plus **$0.005 per Actor Start event**. At one minimum start event, 46 records would imply ~$0.1361 of result/start event charges. This is **illustrative, not a paid invoice**, because memory-dependent start charges, other usage and billing credits need exact reconciliation. The Actor run still must use `maxTotalChargeUsd=$0.25`; the account's $25 usage ceiling and $8 Salesforce reserve remain separate non-negotiable controls.

## Proposed future safeguard (review branch only)

1. Retain **30 requested items** and allow **up to 60 observed JobServe rows**, solely because page-based overfetch is documented. This is a hard *dataset-acceptance* bound, **not** an increase in its $0.25 API run-charge cap. Other Actors remain bound to their requested item limit.
2. For per-result-priced models, reduce both requested and accepted item ceilings to the number affordable under that Actor's cap; do not assume the same JobServe page allowance remains valid after a pricing-model change.
3. Verify the source's final dataset count before and **after** reading its complete items, reject any count drift/partial response, and reject over 60 rather than hiding the excess.
4. Continue applying the independent 22-family title classifier, safe HTTPS advert requirement, date/provenance checks, duplicate marking and fail-closed WordPress publication gate. Do not promote "trainee/no experience needed" advertisements without review.
5. Preserve **zero automatic Actor retries**, shared acquisition concurrency, the **$25 shared account ceiling**, **$8 Salesforce reserve**, **$1.80 refresh charge cap**, and WordPress v0.3.1 rolling retention.
6. Actual post-run Apify usage/invoice costs require independent billing checks. No source records or charges are approved for commercial redistribution yet.

The branch includes regression tests for JobServe 46/30 and 61/30 outcomes, consistent versus drifting metadata reads, and an offline review of the 161 previously collected records.

**Deployment position:** Do not merge/reenable the paid BA schedule until the source-output policy and quality gates receive a deliberate release review. No new Actor runs or WordPress writes were performed to produce this audit.
