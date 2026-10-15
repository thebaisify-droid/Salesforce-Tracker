# Independent Business Analysis automated refresh — staged, disabled

This release provides an executable **five-board acquisition module**, quality-gated WordPress delivery package builder, separate one-shot WordPress sender and manual preflight GitHub workflow. It does **not** enable paid scraping or periodic delivery.

## Pipeline

1. GitHub Actions `ba-controlled-refresh.yml` is **manual preflight-only**; no `schedule` event.
2. `scripts/ba_controlled_refresh.py` has source-specific inputs for CV-Library, Totaljobs, Reed UK, Indeed UK and JobServe. All use the standard Apify API, including JobServe (to avoid `meta.origin=MCP` SDK incompatibility).
3. Paid launch requires an explicit distinct `BA_PAID_REFRESH_APPROVAL` environment flag, `enabled:true` in an audited configuration and fresh account headroom. The previous one-time pilot authorisations **do not authorise future recurring costs**.
4. Per-source result limits and proposed capped maximum charges total $1.20 **for planning only**. This is not a verified estimate of actual costs. Apify may ignore some charge parameters for Actors using different billing models; verify billing semantics before enabling.
5. Collection fails closed on unavailable account usage, any failed source, polling timeout or missing dataset provenance. No retries and no Salesforce task modification.
6. `scripts/ba_wordpress_delivery_package.py` creates HTML and JSON fragments only when all five source run receipts are separately present, all succeeded, and required row fields pass QA. Current historical publication candidate does not satisfy the fresh-receipt requirement and cannot silently refresh itself.
7. `scripts/ba_wordpress_sender_once.py` operates on WordPress page **49 only**, with independent `BA_WP_USERNAME`, `BA_WP_APPLICATION_PASSWORD` credentials, `BA_WP_DELIVERY_APPROVAL` flag, no retries, and GET/update readback requirement. This transport is not included in a scheduled workflow or invoked by the preflight. Prior to real activation, complete a WordPress receiver/preflight and ensure atomic delivery and concurrent edit protection; direct WordPress page PUT is not suitable for unattended updates without those safeguards.

## Remaining integration work before activation

- Implement completion from five successful Apify run receipts through dataset retrieval, source normalisation, classification, sector evidence, deduplication and QA to the final package on each refresh. **The acquisition and offline delivery builder are separate components; there is currently no automatic handoff.**
- Introduce a dedicated BA WordPress snapshot receiver or equivalent safe, atomic, authenticated delivery mechanism. Do not re-use the Salesforce receiver. The prototype sender is disabled and must not be wired to a recurrence as is.
- Verify monthly Apify account limit $19 and reserve at least $8 for Salesforce, and confirm each source's actual charging semantics, as well as refresh caps within remaining headroom.
- Obtain explicit approval for recurring paid acquisitions and a cadence. Do not infer continuous authorisation from past individual pilots.
- Test a no-cost end-to-end handoff and then a user-approved bounded live refresh with a rollback.
- Add a dynamic last-successful-refresh time and per-source freshness indicators. Keep source-observed jobs labelled as such, not employer-confirmed vacancies.

Live page https://jobs.zarafytek.com/?page_id=49 remains at 57 advertisements. The Salesforce workflow is untouched.
