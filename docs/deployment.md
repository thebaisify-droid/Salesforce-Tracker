# Deployment

## Before go-live

1. Select and configure all three live sources.
2. Keep secrets in environment variables or GitHub Actions Secrets.
3. Run `python -m pipeline.daily_refresh --config config/pipeline.json --check` until preflight is green.
4. Run a forced refresh and inspect `state/dashboard_status.json`, the run metrics and quality report.
5. Confirm the database location is persistent.

The bundled SQLite store is suitable for development and a single persistent host. GitHub-hosted runners have ephemeral disks, so production scheduling needs either a persistent database/storage strategy or execution on persistent hosting.

## Schedule

The workflow checks 06:15 and 07:15 UTC and lets the Europe/London guard select the correct BST/GMT slot. Scheduled runs remain disabled until repository variable `TRACKER_LIVE_ENABLED=true` is set.
