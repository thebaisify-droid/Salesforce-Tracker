# Five-source Business Analysis refresh — ready for guarded pilot

## What is ready

A dedicated UK **Business Analysis / Product / Delivery / Cyber** acquisition plan for exactly:

| Source | Actor | BA pilot query | Max rows |
|---|---|---|---:|
| CV-Library | `blackfalcondata/cv-library-scraper` | business analyst | 10 |
| Totaljobs | `abotapi/totaljobs-com-scraper` | business analyst | 10 |
| Reed UK | `wildorigins/uk-jobs-reed` | business analyst | 10 |
| Indeed UK | `wildorigins/indeed-jobs` | business analyst | 10 |
| JobServe | `solidcode/jobserve-scraper` | business analyst | 10 |

These are **separate BA-specific Actor inputs**, not reused Salesforce saved tasks. The Actor-specific input names/types were inspected from the Apify Store on 15 October 2026. The initial cap is **up to 50 source records** across five queries for a pilot, not 50 matched/deduplicated vacancies. It does not imply full coverage of the 22 role families; a later budgeted acquisition needs rotating family-specific queries.

### What remains blocked

- **No paid Actor run has been launched**, no recurring schedule added, no publishing path enabled and no Salesforce code changed.
- Account's actual October usage and independently enforced $19 monthly limit **not yet read** by this conversation. Published Actor details did not expose confirmed live charge schedules for all five Actors.
- No per-Actor hard charge caps have been selected or user-approved. Paid five-source launch is therefore **not authorised**.
- WordPress public page 49 remains the historic **36 source-observed advertisements**; the independent 5-board feed must not overwrite it until genuinely fresh validated data exists.

### Manual read-only preflight

GitHub Actions -> **Business Analysis five-source read-only preflight** -> Run workflow. It runs once on manual request and performs **no paid Apify calls**.

1. Validate independent source payload shape, all-five contract, and $19/$8 budget guard in CI.
2. Perform a single authenticated **GET** to Apify's `users/me/limits` endpoint using the existing GitHub `APIFY_TOKEN` secret. Report account limit, current spend and remaining headroom after preserving the $8 Salesforce reserve.
3. Read-only only: no Actor starts, no retries, no schedule, no source task edits and no dashboard publication.

Locally without a token:

```bash
python -m scripts.ba_five_source_preflight
python -m scripts.validate_ba_five_source_contract
python -m unittest discover -s tests -p 'test_ba_*' -v
```

The existing five-source contract remains disabled; a **one-time priced acquisition pilot** needs a fresh usage reading, Actor pricing and separately explicit approval of total and per-source hard caps. Never silently equate 'proceed' to approving an unspecified charge.

### Five-source data staging and QA

When completed source run data becomes available in a local file with schema `ba-five-source-completed-batch/v1`, supply each source under `sources`:

```json
{
  "schema": "ba-five-source-completed-batch/v1",
  "sources": [
    {
      "name": "CV-Library", "status": "SUCCEEDED", "attempted": true,
      "run_id": "previously-completed-id", "dataset_id": "source-dataset",
      "observed_at": "2026-10-15T10:00:00Z",
      "records": [{"title": "Business Analyst", "canonicalUrl": "https://www.cv-library.co.uk/job/example"}]
    }
  ]
}
```

The real batch must contain the same metadata and independently acquired records for **all five** distinct sources. `scripts/ba_stage_five_source_data.py` is offline-only: it maps the five different schemas, rejects missing HTTPS links/off-scope titles/expiry events, classifies roles, retains provenance and sector evidence, filters exact URL duplicates, and flags possible cross-board duplicates without merging legitimate distinct postings. It creates a **staged** snapshot, never a published one.

```bash
python -m scripts.ba_stage_five_source_data --input /path/to/completed-five-source-batch.json
```

An incomplete source manifest preserves the prior live snapshot. A successful staging run still requires a separately approved publication handoff before any WordPress update. No assertion that unverified source postings are employer-confirmed currently open vacancies.

## Guardrails

The current Salesforce controlled twice-weekly acquisition and WordPress delivery remain isolated. Both pipelines must respect the **same $19 Apify account limit** and reserve at least **$8** for Salesforce. No shared saved Task mutations. No new recurring workflows before a verified bounded pilot.

Only the single read-only preflight workflow can be manually invoked at this stage; it has no schedule, push trigger or actors. The existing research snapshot remains visible if a new source fails.
