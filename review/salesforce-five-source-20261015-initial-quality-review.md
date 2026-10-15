# Five-source one-time pilot: initial read-only quality review (2026-10-15)

All rows retrieved by GET from the five successful, immutable Apify datasets.
No new Actors, production database writes or WordPress publication.

| Source | Dataset ID | Raw | Advert records | Expiry events | Explicit Salesforce title signals |
|---|---|---:|---:|---:|---:|
| CV-Library | RTMRMZthaZ8BeVbli | 15 | 6 | 9 | 0 |
| Totaljobs | mkF6Ck2YNOA6pDK1r | 20 | 20 | 0 | 11 |
| Reed UK | eAzDgMOr4l1O16uv4 | 20 | 20 | 0 | 19 |
| Indeed UK | 3TrVqYn3rDsP8eyf6 | 20 | 20 | 0 | 2 |
| JobServe | 1VUnFLW3aSR5YefTY | 22 | 22 | 0 | 21 |
| **Total** | | **97** | **88** | **9** | **53** |

**Important:** `title signals` are string-based preliminary indicators; not approved role taxonomy CORE classifications. Company and title duplicate keys, normalised for punctuation and legal suffixes, give **80 provisional distinct title/employer pairs among 88 advert rows** (8 excess repeated records). Title relevance in provisional deduplicated rows is **47**; the remaining 33 need taxonomy review/adjacent/irrelevant handling, not automatic CORE claims. Cross-board differences can conceal more duplicate vacancies.

### Quality findings
- CV-Library produces lifecycle EXPIRED events with only `jobId`, `changeType`, `expiredAt`, `stateKey`. These are not vacancies. Process separately with explicit event semantics; do not infer availability for other sources.
- Six CV-Library adverts have no explicit Salesforce signal in the title; descriptions might contain generic Salesforce references. They must pass taxonomy checks before inclusion.
- Indeed UK includes non-Salesforce job titles; many results are from Salesforce as an employer, which is not evidence of Salesforce-platform hiring.
- JobServe returned 22 records despite the planned requested maximum 20; check count caps and per-run charge metadata, but do not rerun.
- Approximate initial deduplication uses normalised title+advertiser, not verified same job URLs or source job IDs. Do not overstate unique vacancy count.
- Publication remains blocked pending source-native mapping, proper taxonomy and quality report, plus separate handoff approval.

### Decision
**REVIEW_ONLY — NO PUBLICATION.** Do not send this unqualified pilot material to the WordPress receiver. Keep page #85's research content unchanged. The next step is a deterministic offline/GET-only classifier using the 5 dataset IDs, explicitly excluding lifecycle events and emitting a QA report plus provenance for each row; no new Apify calls are necessary.

Actual Apify invoiced cost has **not** been independently established from these data. $0.90 was the maximum authorised charge.
