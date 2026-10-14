# Salesforce WordPress snapshot transport — deployment specification

This is **planning and offline preflight only** for [Issue #84](https://github.com/thebaisify-droid/Salesforce-Tracker/issues/84). No WordPress changes, paid calls, schedules, or deployment are enabled.

## Source and destination

Source: GitHub Actions quality-passed `dashboard/live-data.json`, with versioned schema `salesforce-hiring-dashboard/v1`. Destination: the existing WordPress viewer's local `wp-content/uploads/salesforce-tracker/live-data.json`. The current GitHub workflow commits only to GitHub; it does **not** deliver to WordPress.

## Proposed secure delivery contract

Implement a site-side authenticated REST receiver separately, with a narrowly scoped identity, HTTPS, bounded upload size, SHA-256 integrity verification, strict schema and quality validation, freshness checks and timestamp rollback prevention. Stage uploads to a temporary file in the existing permitted local directory, verify its checksum, atomically rename, and clear only the Salesforce dashboard transient after success. Fail closed if local state is missing, invalid or older; never equate missing data to zero jobs.

GitHub publisher must be a separately reviewed **one-time** operation until current source acquisition and WordPress authentication are established. Do not store WordPress credentials in source code or publish them in Actions logs. Do not allow automatic retries, unsupervised schedules or live publication based solely on source-reported ACTIVE status.

## What can be validated now

Run `python -m scripts.validate_salesforce_wordpress_delivery --input dashboard/live-data.json`; this offline check rejects data older than 36 hours, unsuccessful refreshes, failed quality evidence, invalid counts and malformed payloads. It **cannot** prove an individual vacancy remains open.

The 10 October 2026 91-record GitHub snapshot is stale on 14 October and must not be transferred as current data. The WordPress 23-record historical archive must remain visible until a newly validated feed is approved. Preserve the $19 shared Apify cap and internal $8 Salesforce reserve.

## Release gates

Independent security review of the proposed receiver; WordPress backup; WordPress host staging install; authentication and atomic-upload testing; error-path/rollback test; independently quality-passed new source observation; authorised fresh acquisition if needed; verified end-to-end dashboard counts, filters and source links. No work on this branch activates these steps.
