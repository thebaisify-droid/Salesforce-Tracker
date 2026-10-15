# Business Analysis sector coverage and five-source collection policy

## Sector incident (15 October 2026)

All 36 historical advertisements on the Business Analysis page previously showed `Not specified` because the preview builder hard-coded `sector` and did not run enrichment. This is a **processing quality defect**, not evidence that no employers have known sectors.

The snapshot contained 18 advertisements with `advertiser="Not specified"` and 18 with an advertiser name. An external official-organisation evidence register resolves 12 advertisements across 7 exact advertisers. Remaining **24 / 36** lack reliable supporting evidence. The sector label on the live page is now **Advertiser sector**, explicitly **not end-client sector**. End-client sector is unknown for all 36 until evidence is available. No industry has been inferred from a job title, cyber occupation, recruitment intermediary, or occupational job-board category.

**Source-evidenced sectors:** Professional Services 6; Public Sector 2; Healthcare & Life Sciences 2; Technology Services 1; Retail & Consumer 1. Each resolved row in `sector-enriched-snapshot.json` includes an official source URL and `sector_basis`. The source list and scripts are in `business-analysis-tracker/config/sector-evidence.json`, `scripts/enrich_ba_advertiser_sector.py`.

The live WordPress page at `https://jobs.zarafytek.com/?page_id=49` was amended independently via surgical content edits. Readback confirmed 36 advert rows, 36 external advert links, 12 evidence-labelled advertiser sectors, 24 unresolved advertiser sectors, and the populated sector dropdown. The original Salesforce page and collector were not edited. This GitHub PR does not publish to WordPress or trigger collection.

## Mandatory **five distinct boards** for future BA refresh

1. **CV-Library** — dedicated BA query input for `blackfalcondata/cv-library-scraper`.
2. **Totaljobs** — dedicated BA query input for `abotapi/totaljobs-com-scraper`.
3. **Reed UK** — dedicated BA query input for `wildorigins/uk-jobs-reed`.
4. **Indeed UK** — dedicated BA query input for `wildorigins/indeed-jobs`.
5. **JobServe** — dedicated BA query input for `solidcode/jobserve-scraper`.

All five should be attempted on each independently authorised refresh. Capture each source's run status, items, accepted rows, duplicates, timestamp and charges. If any source fails, **preserve the previous successful snapshot**, visibly mark that feed stale/partial and do not claim a completed five-source refresh. No retry storm. Distinct job-source labels are mandatory. BA sources must use their own non-Salesforce search terms, never mutate existing Salesforce saved Tasks.

The contract `business-analysis-tracker/config/five_source_refresh.json` is **disabled**: zero authorised paid runs, no collection schedule and no WordPress delivery. The receipt validator `scripts/validate_ba_five_source_contract.py` fails closed on a missing source or QA failure.

Before activating any new paid collection: review per-Actor BA-specific input schemas and live prices; check real-time Apify usage and hard **$19 monthly account ceiling**, preserving the **$8 Salesforce reserve**; request explicit one-time capped authorisation; then establish a separately approved BA schedule and publication process. These controls do not independently establish job status or source reliability. Publication can use source-observed advertisements without an independent human verification requirement, but the dashboard must never misstate source observations as employer-confirmed open vacancies.

## Local checks

```bash
python -m scripts.enrich_ba_advertiser_sector
python -m scripts.validate_ba_five_source_contract
python -m unittest discover -s tests -p 'test_ba_sector_and_five_sources.py' -v
```

This release corrects historic sector display and establishes the five-source contract. **It does not activate refreshed BA data acquisition**.
