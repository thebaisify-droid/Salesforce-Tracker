# Persistent tracker state

GitHub-hosted runners are ephemeral, so the tracker explicitly carries its SQLite state from one successful run to the next.

## Production mechanism

The live daily workflow uses a named GitHub Actions artifact: `tracker-state`.

At the start of a run it:

1. lists non-expired `tracker-state` artifacts;
2. considers only artifacts produced from the `main` branch;
3. restores the newest snapshot when one exists;
4. validates every restored checksum;
5. runs SQLite `PRAGMA integrity_check`;
6. verifies the required tracker tables before processing new vacancies.

After a successful refresh it:

1. validates the database again;
2. writes `state/state_manifest.json` with SHA-256 checksums and row counts;
3. uploads the database, tracker state and dashboard JSON as the next `tracker-state` artifact.

A failed refresh does not replace the last successful persistent snapshot.

## What is persisted

- `data/salesforce_tracker.db`
- `state/`
- `dashboard/data.json`

Raw run payloads are diagnostic evidence rather than durable state and remain in separate per-run artifacts.

## Proven cross-run behaviour

Persistence was validated across two separate GitHub-hosted runners using live CV-Library, Totaljobs and Reed output. Runner B restored runner A's verified database containing 3 vacancies and replayed the identical raw records. The result was:

- 3 vacancies before;
- 3 vacancies after;
- 0 duplicate inserts;
- 3 unchanged matched vacancies.

## Retention

The state artifact is retained for 90 days. Daily operation continually creates a newer snapshot, so normal continuity depends only on the latest successful state. This is operational persistence, not long-term archival; create an external backup before any shutdown expected to exceed the artifact-retention period.

## Schedule

The production workflow is enabled. It checks both UTC equivalents of 07:15 Europe/London and the local-time guard selects the correct BST/GMT slot. A manual workflow dispatch forces an immediate refresh.
