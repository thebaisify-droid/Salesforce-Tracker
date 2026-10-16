# UK Business & Technology Jobs Tracker — $25 acquisition trial

**Status:** implementation staged and CI-tested on a draft feature branch; not merged or deployed live. Paid acquisition remains blocked until all release gates pass.

## Scope
This product covers **all 22 registered families** in `config/business_product_delivery_security_taxonomy_v1.0.json`. The old Business Analysis label is not the acquisition scope. Neither volume of BA ads nor raw total job count substitutes for family coverage.

## Approved shared trial budget
- Stay on the existing **Apify Starter $19/month subscription** (includes $19 monthly prepaid platform usage). Configure the separate **Custom usage limit to $25/month** in Apify Console > Billing > Limits > Edit limit. This permits at most $6 additional pay-as-you-go usage after prepaid usage, before applicable taxes, assuming no separate extras. No Scale upgrade is needed. Repository changes **cannot** change the account limit. Source: https://docs.apify.com/account/subscriptions#pay-as-you-go
- Preserve **$8** for Salesforce. BA allocation must remain <= **$17/month**.
- BA currently schedules nine Tuesday/Friday 07:35 UK slots at most; each may request up to **$1.80**, therefore scheduled upper bound **$16.20/month**. Per-source caps: CV-Library $0.65; Totaljobs $0.35; Reed $0.20; Indeed $0.35; JobServe $0.25.
- **$50 is a future option, not an approved or active limit.** It needs separate billing review and authorisation. Charge floors, platform usage, other Apify activities and source-level actual receipts must be audited.
- Zero auto retries; all five sources must succeed and pass QA; previous published data remains if anything fails. Keep the source-observed (not employer-confirmed-open) wording.

## Acquisition experiment
- Starting upper bound: **up to 30 requested items per source per slot**, not the blanket 10. The result request is reduced automatically for any per-dataset-item Actor when 30 items would exceed that Actor's charge cap.
- Five sources get **different family-specific queries** per scheduled slot; all 22 have an acquisition opportunity within five eligible slots. Individual Actors still run once each per refresh; no blanket assumption that they accept multi-keyword query syntax.
- `maxItems`, source input result caps, `maxTotalChargeUsd`, a live pre-POST account-usage read, and the $8 reserve are applied for every Actor. Completed dataset item counts must not exceed the requested maximum. Cap-exhaustion and failed Actors are **not** automatically retried.
- **Limitations:** This is acquisition *coverage across time*, not yet 22-family *display coverage*. The current WordPress receiver and current QA path require every displayed record to match only the five current run IDs. Publishing just the latest rotated slot would remove other families from the public dashboard.

## Remaining deployment gates

The WordPress receiver **v0.3 implementation is now committed and tested on the branch**, including `rolling-retention.php`. It retains the most recent 30 days of source-observed advertisements, bounds display to 450 records, preserves the original run and dataset ID, exposes original last-observed dates and expires old records without inventing current-open status.

**It has not been installed on the live WordPress site.** `rolling_coverage_enabled=false` intentionally prevents paid collection before a safe deployment.

Before enabling the trial:
1. Take a WordPress files/database backup, install both updated v0.3 PHP files, and verify server syntax and a controlled **staging-only** two-snapshot end-to-end retention/rollback test. Do not inject synthetic data into the live page.
2. Verify Apify console account's independent hard spending limit is **exactly $25**; repository code cannot update the Apify setting. Confirm current usage and enough headroom for the $8 Salesforce reserve and $1.80 requested refresh cap.
3. Reconcile the earlier JobServe cap-versus-actual count discrepancy, confirm live per-Actor pricing and monthly headroom, and validate all five source inputs.
4. Only then enable the rolling-coverage flag under the tested schedule. Preserve zero retries and independent WordPress authentication; do not merge before full site acceptance.
5. After multiple real refreshes, report accepted unique ads, direct advert URLs, last-observed age, source failures, per-family coverage and cost per relevant deduplicated advert. No assurance of 22 non-empty families is inferred from the search plan.

## Commercialisation decision gates
Track paid Actor cost per **accepted, relevant, deduplicated** advertisement, distribution across the 22 families, source and job-link quality, posting-date availability, source freshness, missing sectors, and external advert link validity. Review at least several UK scheduled cycles before budget expansion.

A paid service requires verified job-board data licensing/redistribution rights, UK GDPR/privacy and retention review, resilient source quality, real user value, subscription billing, refund/cancellation policy and server-side **authenticated entitlements**. Do not rely on hiding public WordPress HTML/JSON or JavaScript-only controls to protect premium vacancies. Keep the Salesforce product separate until business terms and service tiers are defined.
