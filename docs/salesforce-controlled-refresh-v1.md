# Controlled Salesforce refresh v1 — release status

Purpose: refresh five UK Salesforce sources periodically and run the existing
taxonomy/normalisation/deduplication/quality/lifecycle gates, without spending
uncontrolled Apify charges or silently replacing live WordPress data.

## Deployment and enablement
- New workflow `.github/workflows/salesforce-controlled-refresh.yml`.
- Schedule: Tuesday/Thursday, 06:15 and 07:15 UTC. Existing
  `pipeline.daily_refresh --scheduled` checks 07:00 **Europe/London** local
  time and successful-refresh-today, so normally only one slot is due across DST.
- **OFF by default**: job requires repository variable
  `SF_CONTROLLED_REFRESH_ENABLED=true`. Do **not** set it until separately
  approved and operational acceptance criteria pass.
- Legacy `daily-refresh.yml` now requires
  `SF_LEGACY_REFRESH_ENABLED=true`; keep unset.
- Shared Apify-acquisition concurrency group avoids overlap with other
  workflows using the same group. Apify's actual $19 spending limit remains
  the independent hard cap.
- Immediately before collection, read authenticated Apify account usage/limit
  and reject any reading not showing the exact $19 cap and at least
  **$8 protected reserve + $0.90 worst-case five-source charges** headroom.
  The collector retains per-source maxTotalChargeUsd caps.
- Restore checksum-verified state; keep existing source gates (required
  CV-Library, Totaljobs, Reed), taxonomy, deduplication, lifecycle and QA.
  Save private state and review evidence as GitHub artifacts.
- No workflow Git push and no WordPress REST delivery. The pre-existing PHP
  receiver is separate, and page #85 is a static Phase 1 research explorer.
  **This change does not automatically update either WordPress page.**
- Errors fail closed and preserve the previous site presentation.
- No automatic retry code, no scheduled job unless enable flag set.

## Open items before production enablement
1. Confirm GitHub Actions scheduled run delivery; runs last observed Oct 10
   for legacy workflow, so job schedule reliability must be monitored.
2. Confirm collector's sequential per-source billing safety on actual live
   account usage, and that original Task input limits are appropriate.
3. Address the 22 versus requested 20 JobServe items discrepancy and
   source-specific malformed URLs using explicit normalisation gates.
4. Confirm accepted source-observed snapshot schema and WordPress page #85
   data rendering contract. Page #85 currently contains static rows;
   delivering live-data.json to the receiver alone will not refresh it.
5. Agree a publication policy, integrate and test snapshot handoff, then
   separately authorise `SF_CONTROLLED_REFRESH_ENABLED=true`.

**This PR is an installed, testable automation pipeline definition, not
authorisation for scheduled paid acquisition.**
