# Salesforce Tracker

UK Salesforce hiring-market tracker with three-source incremental ingestion, vacancy normalisation/deduplication, role and sector classification, assurance gates, and dashboard-ready aggregates.

## Current status

**Core tracker: implemented and tested. Confirmed daily sources: CV-Library, Totaljobs and Reed via saved Apify Tasks. Live credentials/validation are still pending.**

The repository contains:

- daily refresh orchestration with a 72-hour overlap window;
- strict 3/3 source gating;
- Apify Actor and saved-Task collector adapters;
- SQLite reference store and idempotent vacancy upsert/deduplication;
- master data **v1.3** and role taxonomy **v2.2**;
- advertiser/direct-employer, role-family, seniority, Salesforce-specialism and sector classification;
- review flags for uncertain role/sector classifications;
- built-in assurance validation;
- dashboard aggregate publishing and refresh-status evidence;
- CI tests and a daily GitHub Actions workflow that remains disabled until live validation is complete.

The Task references are wired under `config/sources/`, but `"ready": false` remains deliberate until each saved Task has been run with the Apify token and its current output schema has been validated.

## Verify the build

```bash
python -m unittest discover -s tests -v
python -m pipeline.daily_refresh --config config/pipeline.json --check
```

## Daily sources

- CV-Library — `develop_ify/cv-library-scraper-task`
- Totaljobs — `develop_ify/totaljobs-com-scraper-task`
- Reed — `develop_ify/uk-jobs-reed-task`

Only `APIFY_TOKEN` is required as a source secret. See `docs/credentials.md`.

## Scheduling

The workflow checks both UTC equivalents of **07:15 Europe/London** and uses a local-time guard to handle BST/GMT safely. Scheduled execution is disabled until the repository variable `TRACKER_LIVE_ENABLED=true` is set.

## Secrets

Never commit `.env`, API keys, tokens or database credentials. Store runtime secrets in GitHub Actions Secrets or the deployment environment.
