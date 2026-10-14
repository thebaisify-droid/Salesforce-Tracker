# Salesforce snapshot receiver — security review and staging evidence

Status: **tested in isolated staging harness, NOT installed/activated on WordPress**. Date: 14 October 2026.

## Scope
PR #85 contains a WordPress receiver in `wordpress/salesforce-snapshot-receiver/salesforce-snapshot-receiver.php`, a one-time sender `scripts/send_salesforce_wordpress_snapshot_once.py`, and offline safety tests. No GitHub Actions workflow, schedule, Apify Actor, WordPress plugin activation or live data publication was executed.

## Security controls reviewed
- **Authentication:** REST endpoint requires both an authenticated WordPress identity and the narrowly scoped `sf_deliver_snapshot` capability. This capability is **not automatically assigned**; a dedicated account/capability assignment is required before activation. Administrator permission alone is not sufficient.
- **Transport:** Sender pins the HTTPS host and REST endpoint. Basic Application Password authentication is supplied only by environment variables after explicit `--send` and `SF_DELIVERY_APPROVED=yes`. Redirects are refused; no retry loop. Do not log or commit credentials.
- **Integrity:** Receiver compares SHA-256 to the exact JSON bytes and caps decoded JSON at 400,000 bytes, request envelope at 560,000 bytes. Sender checks acknowledgement digest.
- **Quality/freshness:** Requires `salesforce-hiring-dashboard/v1`, boolean QA pass, successful refresh, bounded count and a timestamp between 36 hours old and 15 minutes in the future.
- **Atomic writes:** Blocks symlinked target/lock, serializes uploads with nonblocking `flock`, rejects rollback against the existing snapshot and writes via same-directory temporary file then rename; cleans up temp files and clears only the Salesforce dashboard transient on success.
- **Fail closed:** Existing historical WordPress fallback stays untouched. No traffic is sent when dry-run sender is invoked.

## Executed isolated integration checks
GitHub CI test `tests/test_salesforce_wp_receiver_integration.py` executes a PHP WordPress-stub harness against a randomly named temporary directory, including:
1. Unauthenticated request denied; scoped-capability identity accepted.
2. Bad SHA-256 rejected.
3. Valid snapshot accepted and exact file bytes verified.
4. Equal-timestamp replay accepted idempotently.
5. Older-timestamp rollback rejected.
6. Lock contention rejected.
7. Temporary staging files cleaned up and Salesforce-only cache cleared.

Other tests cover PHP syntax, quality-gate failure, stale/future data rejection, sender target validation, one-request behaviour and mismatched acknowledgement. **These are isolated integration tests, not a real WordPress REST/Apache/hosting staging deployment.**

## Remaining gates before installing or activating
- Site administrator must create/approve a *real non-production WordPress staging site* with appropriate permissions and a fresh backup; current WPVibe connection is to production only.
- Review Application Password handling and provision dedicated identity with only `sf_deliver_snapshot` and any minimum WordPress app-password permissions. Do not grant `manage_options`.
- Confirm uploads are protected from arbitrary public listing / script execution, TLS + credential handling and local filesystem ownership; test HTTP status codes and proxy limits.
- Test actual WordPress staging plugin activation/REST authentication, atomic replace, concurrent updates and rollback under the hosting runtime. No claims of production-ready staging verification until completed.
- Test caching/last-good option precedence and make sure production viewer never hides an invalid or stale feed as current.
- Use only a **new independently quality-passed current snapshot**, not the stale 10 October 91-record GitHub file.
- Run sender only after separate user approval, account-budget check if acquisition is required, and end-to-end checksum verification. Keep $19 shared Apify ceiling and internal $8 Salesforce reserve.

**Conclusion:** The component passes isolated security tests. Live activation and transmission are **not approved or performed**.
