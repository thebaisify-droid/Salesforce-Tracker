# Salesforce Tracker

UK Salesforce hiring-market tracker with three-source incremental ingestion, vacancy normalisation/deduplication, role and sector classification, assurance gates, and dashboard-ready aggregates.

## Current status

**Core tracker: implemented and tested. Live sources: intentionally not configured yet.**

The repository contains:

- daily refresh orchestration with a 72-hour overlap window;
- strict 3/3 source gating;
- generic HTTP JSON and Apify Actor collector adapters;
- SQLite reference store and idempotent vacancy upsert/deduplication;
- master data **v1.3** and role taxonomy **v2.2**;
- advertiser/direct-employer, role-family, seniority, Salesforce-specialism and sector classification;
- review flags for uncertain role/sector classifications;
- built-in assurance validation;
- dashboard aggregate publishing and refresh-status evidence;
- CI tests and a daily GitHub Actions workflow that remains disabled until live sources are selected.

The three files under `config/sources/` have `"ready": false`. This is deliberate: preflight must remain red rather than pretending the tracker has live data.

## Verify the build

```bash
python -m unittest discover -s tests -v
python -m pipeline.daily_refresh --config config/pipeline.json --check
```

## Configure the three sources

Each source slot supports `http_json`, `apify_actor`, or `fixture`. See `docs/source_configuration.md`.

After selecting the actual three providers, update the three files in `config/sources/`, set `"ready": true`, then run preflight, dry-run and a forced refresh.

## Scheduling

The workflow checks both UTC equivalents of **07:15 Europe/London** and uses a local-time guard to handle BST/GMT safely. Scheduled execution is disabled until the repository variable `TRACKER_LIVE_ENABLED=true` is set.

## Secrets

Never commit `.env`, API keys, tokens or database credentials. Store runtime secrets in GitHub Actions Secrets or the deployment environment.
