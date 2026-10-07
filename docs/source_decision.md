# Proposed three-source architecture

This repository could not recover the exact source names from the earlier project chat, so the following is a **proposed, explicit source architecture**, not a claim about a previous decision.

## 1. Lightcast UK Job Postings — primary analytical source

Lightcast exposes a dedicated UK Job Postings API, OAuth2 authentication with the `postings:uk` scope, date-window filtering and structured/enriched posting fields. It is the strongest analytical baseline when account access is available.

Documentation: https://docs.lightcast.io/lightcast-api/reference/overview-uk-job-postings

## 2. Adzuna Jobs API — official API cross-check

Adzuna has an official UK job-search API using `app_id` and `app_key`. It provides listing-level job data and gives us an independently collected source for reconciliation.

Documentation: https://developer.adzuna.com/docs/search

## 3. LinkedIn Jobs via Apify — independent market cross-check

The selected Apify Actor accepts title/keyword and location filters, exposes structured job/company fields and returns public LinkedIn job listings without requiring LinkedIn credentials. Because this is a scraper rather than a first-party job API, it is deliberately assigned a lower trust tier and should be monitored for schema/drift failures.

Actor: https://apify.com/bebity/linkedin-jobs-scraper

## Assurance rule

The dashboard remains unpublished unless all three configured sources succeed. Source 3 should corroborate and extend coverage; it should not silently override higher-trust structured evidence. Duplicate listings are merged through canonical URLs and source lineage is retained.

All three configs remain `ready=false` until the necessary credentials/access are supplied and a first-source validation run passes.
