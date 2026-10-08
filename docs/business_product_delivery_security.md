# Business, Product, Delivery & Cyber Security — classifier-only proposal

This branch contains an **inactive** role taxonomy and candidate relevance rules.
It does **not** connect to Apify, add sources, change any existing collectors,
change the Salesforce inclusion gate, or publish a second dashboard.

## Scope

The established 15 families cover business analysis, analytics/BI, product,
delivery, programme/project, change, Agile, services and process improvement.
Security adds 7 more:
- Information Security Analysis (includes cyber security analysts)
- Security Operations / SOC
- Security Architecture
- Security Consulting & Advisory
- Security Risk & Third-Party Risk (TPRM)
- Security Management
- IT Security

Title phrases are matched as bounded phrases, prioritising the longest match.
Specific exclusions reject physical/site security titles. Security Architect,
Security Advisor, Security Risk Manager and Technology Risk Manager require cyber/
IT/information security signals to avoid unrelated vacancies. Some generic
product/service/reporting titles are placed in the review queue.

## Next phase — not implemented

1. Run and review unit tests and a labelled sample of real UK vacancies.
2. Tune false positives, ambiguous titles and role-family precedence.
3. Add independent database, normalisation and dashboard feed with QA gates.
4. Fix and verify global **$19** Apify reservation ceiling and account spending limit.
5. Enable low-volume incremental acquisition **only via a reviewed follow-on PR**.
6. Deploy the separate web page after data quality is demonstrated.

## Safety invariants

- `config/business_product_delivery_security.example.json` explicitly disables
  collection and publishing, and defines **no sources**.
- No scheduled GitHub Action or live dataset is created.
- Existing Salesforce taxonomy, pipeline config, and collector logic stay unchanged.

## Offline dashboard candidate build

Only from an existing local JSON array of records (no network/acquisition):

```sh
python -m scripts.build_candidate_market_dashboard --input /path/to/labelled-vacancies.json --output dashboard/business-product-delivery-security-candidate.json
python -m unittest discover -s tests -v
```

The generated file is **not** uploaded or automatically deployed. It contains separate
BUSINESS_PRODUCT_DELIVERY and SECURITY tracks, per-family aggregates, records
flagged for review, URL-based deduplication and basic validation counts.

This prototype does not provide historical trends or real UK vacancy figures.
Before launch: validate against representative multi-source samples, verify
advertiser/location canonicalization, design cross-board deduplication, and
add an independent persisted store plus quality gate. Strictly prohibit
published use until the quality review and acquisition account limit are signed off.
