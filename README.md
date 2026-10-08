# Salesforce Tracker

UK Salesforce hiring-market tracker with multi-source incremental ingestion, vacancy normalisation/deduplication, role and sector classification, assurance gates, persistent state and dashboard-ready aggregates.

## Current status

**Live.** CV-Library, Totaljobs and Reed remain the core daily sources. Indeed UK is validated and active as a fourth enrichment source. JobServe is fully wired and live-schema validated, but temporarily paused until the Apify paid-Actor usage allowance is increased.

The repository contains:

- daily refresh orchestration with a 72-hour overlap window;
- a 3-source minimum publication gate, with enrichment sources allowed to fail without taking the dashboard offline;
- CV-Library, Totaljobs and Reed saved-Task ingestion plus Indeed UK enrichment through Apify;
- integrity-checked persistent SQLite state restored between GitHub runners;
- idempotent vacancy upsert/deduplication;
- master data **v1.4** and role taxonomy **v2.2**;
- Salesforce-relevance filtering to remove incidental CRM mentions;
- advertiser/direct-employer, role-family, seniority, Salesforce-specialism and sector classification;
- review flags for uncertain role/sector classifications;
- built-in assurance validation;
- dashboard aggregate publishing and refresh-status evidence;
- CI tests and the live 07:15 Europe/London daily GitHub Actions schedule.

## Verify the build

```bash
python -m unittest discover -s tests -v
python -m pipeline.daily_refresh --config config/pipeline.json --check
```

## Daily sources

Core:
- CV-Library — `develop_ify/cv-library-scraper-task`
- Totaljobs — `develop_ify/totaljobs-com-scraper-task`
- Reed — `develop_ify/uk-jobs-reed-task`

Enrichment:
- Indeed UK — `wildorigins/indeed-jobs` — active
- JobServe — `solidcode/jobserve-scraper` — staged; enable after Apify paid-Actor usage is available

Only `APIFY_TOKEN` is required as a source secret.

## Scheduling

GitHub Actions checks both UTC equivalents of **07:15 Europe/London**. The pipeline's Europe/London guard selects the correct BST/GMT run and skips the other probe. Manual workflow dispatches force an immediate refresh.

Each run restores the latest verified `tracker-state` artifact before processing and writes a new integrity-checked state snapshot after success.

## Secrets

Never commit `.env`, API keys, tokens or database credentials. Store runtime secrets in GitHub Actions Secrets or the deployment environment.


## Vacancy lifecycle assurance

Vacancies use a conservative three-state lifecycle: `ACTIVE` → `POSSIBLY_EXPIRED` → `CONFIRMED_EXPIRED`.

Absence from the 72-hour incremental search is never expiry evidence. Older active vacancies are rotated through direct job-page checks. A single explicit unavailable response only marks a vacancy `POSSIBLY_EXPIRED`; two separate explicit unavailable checks at least 12 hours apart are required before it becomes `CONFIRMED_EXPIRED` and leaves active-market KPIs. HTTP blocks, timeouts and ambiguous responses are inconclusive and cannot expire a vacancy. Reappearance in any source immediately reactivates it.
