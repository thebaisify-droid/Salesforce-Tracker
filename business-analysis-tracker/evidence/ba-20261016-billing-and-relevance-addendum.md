# 16 October 2026: verified charges and quality refinements

**Review-only supplement.** Source: the previously completed five Apify Actor runs from GitHub Actions run #38887998367, with authenticated GET-only cost reconciliation in [run #38902702663](https://github.com/thebaisify-droid/Salesforce-Tracker/actions/runs/38902702663). **No additional paid acquisition and no WordPress publication.**

## Actual charged amounts

| Actor source | Authenticated run charge (USD) | Authorised cap (USD) |
| --- | ---: | ---: |
| CV-Library | 0.050439 | 0.65 |
| Totaljobs | 0.113250 | 0.35 |
| Reed UK | 0.025550 | 0.20 |
| Indeed UK | 0.108000 | 0.35 |
| JobServe | 0.136100 | 0.25 |
| **Five-run total** | **0.433339** | **1.80** |

All five runs' `usageTotalUsd` were available from their authenticated completed-run records, and all were within their individually recorded `maxTotalChargeUsd` options. This reconciles billed run costs, not a tax-inclusive invoice or proof that the JobServe `maxResults` input capped item output. JobServe recorded 46 charged output-item events and one start event.

At the check, the Apify account's **actual current usage was $9.593858**, the **custom usage limit $25**, and available account headroom **after the $8 Salesforce reserve $7.406142**. The account billing cycle runs from 8 October to 7 November 2026, so this is a cycle limit—not automatically a calendar-month reset. Total account consumption on 16 October was $0.447523; it includes unrelated usage and should **not** be called the cost of these five Actors. The earlier preflight's $9.1599 usage value was rounded.

**Observational acquisition cost per preliminary matched advert:** $0.433339 / 87 = **about $0.00498**. This is not a commercial cost-of-service measure: 87 records are classified source observations, and licensing, quality verification, hosting, staff time and payment charges are excluded.

## Precision before spending again

The exact stored searches were:

| Source | Search term | Earlier matching titles / source rows | Issue |
| --- | --- | ---: | --- |
| CV-Library | `information security manager` | 8 / 30 | Returned legal, sponsorship-sales, pensions and other unrelated roles |
| Totaljobs | `IT security analyst` | 4 / 25 | Returned training placements and unrelated cyber/security specialisms |
| Reed UK | `business analyst` | 12 / 30 | Broader analyst titles beyond registered 22-family taxonomy |
| Indeed UK | `data analyst` | 17 / 30 | Includes occupationally adjacent, not strictly data-analysis, titles |
| JobServe | `business intelligence analyst` | 41 / 46 | Strong related-role relevance but several BI titles missed the narrow taxonomy |

The proposed alternative keywords **`cyber security manager`** for CV-Library's Security Management search and **`cyber security engineer`** for Totaljobs' IT Security search are **untested hypotheses**. They are recorded in `source_query_experiments_20261016.json` but have **not been activated**. They must not justify additional paid test runs while the account reserve/quality release hold is active.

## Reviewed classifier and training-promotion correction

Draft PR #135 now adds conservative Business Intelligence title aliases (BI developers, managers, `BI & Data Analyst`, and an observed commercial-modelling BI title) and `Cyber Sec Analyst` shorthand. Generic `Security Consultant` remains **excluded without independent cyber/IT context**.

A new publication-stage gate excludes source advertisements that clearly market self-funded courses or guaranteed placements. It does not exclude genuine paid junior vacancies simply for mentioning on-the-job training. This follows repeated Totaljobs results advertising trainee ethical-hacking training schemes rather than straightforward employer roles.

After these proposed changes, on the **same 161 previously collected source rows**, the offline QA result is:

| Metric | Before proposed refinements | After proposed refinements |
| --- | ---: | ---: |
| Preliminary taxonomy/URL matched records | 82 | **87** |
| Role families represented | 12 / 22 | **13 / 22** |
| Excluded or filtered observations | 79 | **74** |
| Business Intelligence titles | 0 | **5** |
| Data Analysis titles | 17 | **16** (one explicit BI hybrid reassigned) |
| Information Security Analysis titles | 4 | **4** |
| Security Consulting & Advisory titles | 2 | **3** |
| Candidate source counts | CV 8, Totaljobs 4, Reed 12, Indeed 17, JobServe 41 | CV **8**, Totaljobs **5**, Reed **12**, Indeed **17**, JobServe **45** |
| Training / nonvacancy promotions excluded | Previously largely out of scope but at least one candidate flagged | **6** safely filtered from all source observations |
| Advertiser-sector evidence | 0 / 82 | **0 / 87** |
| Known working arrangements | 9 / 82 | **9 / 87** |
| Usable source posting dates | 82 / 82 | **87 / 87** |

The revised 87 are **not employer-verified open roles**, not approved for WordPress, and not necessarily 87 distinct real-world positions. The remaining nine families and sector/work-mode gaps need further work. This illustrates why simply acquiring more advertisements is not the first priority.

## Deployment decision

- **Do not merge the draft PR automatically** or reactivate BA paid acquisition while source-output stabilisation and publication QA are under review.
- Retain the revised bounded JobServe page-overfetch guard (30 requested / at most 60 observed, with unchanged $0.25 run-charge cap); reject source-count drift between dataset metadata reads.
- Keep existing **$25** account ceiling, **$8** Salesforce reserve, **$1.80** BA refresh ceiling, no Actor retries and independently protected Salesforce.
- The public WordPress receiver retains the last published 57-record snapshot until a valid source-observed, quality-approved handoff.

No $50 spending change or commercial paywall activation is authorised.
