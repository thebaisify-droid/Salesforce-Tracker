# Salesforce Tracker

UK Salesforce hiring-market tracker with three-source incremental ingestion, vacancy normalisation/deduplication, role and sector classification, assurance gates, and dashboard-ready aggregates.

## Current status

**Core tracker: implemented and tested. Confirmed daily sources: CV-Library, Totaljobs and Reed via saved Apify Tasks. Live source Tasks and schemas have been validated; GitHub-native persistent state is implemented and schedule activation is the remaining go-live switch.**

The repository contains:

- daily refresh orchestration with a 72-hour overlap window;
- strict 3/3 source gating;
- Apify Actor and saved-Task collector adapters;
- SQLite reference store and idempotent vacancy upsert/deduplication;
- master data **v1.4** and role taxonomy **v2.2**;
- advertiser/direct-employer, role-family, seniority, Salesforce-specialism and sector classification;
- review flags for uncertain role/sector classifications;
- built-in assurance validation;
- dashboard aggregate publishing and refresh-status evidence;
- CI tests and a daily GitHub Actions workflow with integrity-checked state restoration; the live schedule remains disabled until its repository variable is enabled.

The three saved Tasks and their live output schemas have been validated, so all three source configs are now marked `"ready": true`. This does not enable scheduled execution.

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
