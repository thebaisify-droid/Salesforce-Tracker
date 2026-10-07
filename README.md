# Salesforce Tracker

UK Salesforce hiring-market tracker with three-source incremental ingestion, vacancy normalisation/deduplication, role and sector classification, assurance gates, persistent state and dashboard-ready aggregates.

## Current status

**Live.** The confirmed daily sources are CV-Library, Totaljobs and Reed via saved Apify Tasks. Live schemas are validated, persistent state has been seeded and cross-run deduplication has been proven across separate GitHub runners.

The repository contains:

- daily refresh orchestration with a 72-hour overlap window;
- strict 3/3 source gating;
- CV-Library, Totaljobs and Reed saved-Task ingestion through Apify;
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

- CV-Library — `develop_ify/cv-library-scraper-task`
- Totaljobs — `develop_ify/totaljobs-com-scraper-task`
- Reed — `develop_ify/uk-jobs-reed-task`

Only `APIFY_TOKEN` is required as a source secret.

## Scheduling

GitHub Actions checks both UTC equivalents of **07:15 Europe/London**. The pipeline's Europe/London guard selects the correct BST/GMT run and skips the other probe. Manual workflow dispatches force an immediate refresh.

Each run restores the latest verified `tracker-state` artifact before processing and writes a new integrity-checked state snapshot after success.

## Secrets

Never commit `.env`, API keys, tokens or database credentials. Store runtime secrets in GitHub Actions Secrets or the deployment environment.
