# Persistent tracker state

GitHub-hosted runners are ephemeral, so the tracker must explicitly carry its SQLite state from one successful run to the next.

## Production mechanism

The daily workflow uses a named GitHub Actions artifact: `tracker-state`.

At the start of a run it:

1. lists non-expired `tracker-state` artifacts;
2. considers only artifacts produced from the `main` branch;
3. restores the newest snapshot when one exists;
4. validates every restored checksum;
5. runs SQLite `PRAGMA integrity_check`;
6. verifies the required tracker tables before processing any new vacancies.

After a successful refresh it:

1. validates the database again;
2. writes `state/state_manifest.json` with SHA-256 checksums and row counts;
3. uploads the database, tracker state and dashboard JSON as the next `tracker-state` artifact.

A failed refresh does not replace the last successful persistent snapshot.

## What is persisted

- `data/salesforce_tracker.db`
- `state/`
- `dashboard/data.json`

Raw run payloads are diagnostic evidence rather than durable state and remain in the separate per-run artifact.

## Retention

The state artifact is retained for 90 days. Daily operation continuously creates a new snapshot, so normal day-to-day continuity does not depend on artifacts older than one run. This is an operational persistence mechanism, not a long-term archive. If the tracker is expected to be shut down for more than the artifact-retention period, create an external backup first.

## Manual runs

A manual workflow dispatch runs a forced refresh immediately rather than waiting for the 07:15 local schedule window. Scheduled runs still use the Europe/London DST guard.
