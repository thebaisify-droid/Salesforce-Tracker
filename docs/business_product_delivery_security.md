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

## Synthetic fixture assurance gate

The classifier now has an offline validator with explicit precision, recall and
role-family accuracy thresholds (90% each by default):

```sh
python -m scripts.validate_candidate_market \
  --input tests/fixtures/candidate_labelled_synthetic.json \
  --report runs/candidate_synthetic_assurance.json
```

**Important:** the 30 manually authored synthetic cases validate deterministic
behaviour only. They are not independent UK job-board samples, cannot prove
real-world accuracy, and never grant publication approval. Before production,
collect a representative, labelled and auditable real vacancy evaluation set,
including ambiguous cyber/physical security ads, cross-family titles, recruitment
agency duplicates and descriptions missing from source responses. Independently
review disagreements and measure performance separately for both tracks.

## Preparing real-world review evidence — acquisition remains disabled

The repository itself currently has no raw cross-market vacancy sample.
When a lawful real-source export becomes available, prepare a **blind-labelling**
CSV (prediction columns are provided separately from still-empty human labels):

```sh
python -m scripts.prepare_candidate_review \
  --input /path/to/real-uk-job-board-export.json \
  --output runs/candidate_review_unlabelled.csv \
  --max-per-stratum 20
```

This creates deterministic samples by source and predicted track, including
excluded/ambiguous cases, and retains source URL evidence. It removes only
identical canonical URLs, not cross-board lookalikes. **Do not treat predicted
labels as ground truth.** Have a reviewer complete `expected_included`,
`expected_family`, reviewer name/date and evidence notes after reviewing the
full advertisement. Resolve disagreements and independently check a subset.

Sampling caveat: balanced/stratified samples evaluate different error types but
do not estimate population-wide job market volumes or unbiased aggregate
precision/recall. Supplement with a random sample of the full acquisition frame
before release. The existing synthetic assurance report is not a deployment gate
for real-world quality.

## Human-labelled evaluation (still offline)

Once the exported review CSV has been independently labelled with
`expected_included`, `expected_family`, `reviewer`, and `reviewed_at`,
run:

```sh
python -m scripts.evaluate_candidate_reviews \
  --input runs/candidate_review_unlabelled.csv \
  --report runs/candidate_human_review_report.json \
  --minimum-samples 100
```

The command fails closed for missing reviewer evidence, duplicate sample IDs,
invalid labels, or fewer than 100 reviewed cases (default). It reports
precision, recall and role-family accuracy, plus source counts and error cases.
Passing these thresholds is **not** production approval; independently audit
source authenticity, sample selection, cross-board duplicate handling, and
representativeness. At present no independently labelled UK market sample
has been supplied or verified. The report always sets
`publication_approved=false` and `real_world_accuracy_validated=false`.
