# Salesforce WordPress receiver — test and release record

The receiver implementation is in `wordpress/salesforce-snapshot-receiver/salesforce-snapshot-receiver.php`. It is a **standalone, inactive plugin** committed to the repository; it is **not installed or activated** in WordPress.

## Security controls

- REST route `POST /wp-json/salesforce-tracker/v1/snapshot` requires authenticated WordPress users with `manage_options`. WordPress application passwords may authenticate over HTTPS, but admin-level credentials are high privilege. **Do not create or store such credentials without separate approval and credential-scope review.**
- Requires SHA-256 checksum and bounded raw JSON size (64–400,000 bytes), JSON schema, quality pass, successful refresh and valid active counts.
- Rejects data older than 36 hours or future-dated more than 15 minutes; refuses rollback to an older recorded snapshot or replacement of invalid prior data.
- Restricts local storage to the WordPress uploads `salesforce-tracker/live-data.json`, checks symlinks, stages temporary output and atomically renames.
- Invalid payloads never cause the dashboard to present a false zero-vacancy market. Viewer fallback remains independent.

## Validation

Run `python -m unittest tests.test_salesforce_wp_receiver` on a machine with PHP installed for full coverage. The test suite checks the permission/checksum contract, runs `php -l`, and executes the PHP validator in a subprocess with minimal WordPress stubs against valid, QA-failed, stale and future-dated fixtures. All tests are offline and do not send network requests.

## Open security and deployment gates

1. Independent review of WordPress authentication privileges (prefer dedicated narrow-scoped capability rather than broadly granting `manage_options` to a transfer identity).
2. Confirm WordPress hosting write permissions; test local storage and atomic replace on staging.
3. Test unauthorized request rejection and replay behaviour; assess potential concurrent uploads and stale cache/last-good option precedence.
4. Resolve GitHub source refresh scheduling separately and establish genuine current source evidence.
5. Wire a separately authorised one-shot sender only after secure credential provision, a full backup, and new freshness/assurance confirmation.
6. Do **not** transfer the 10 October 91-record snapshot: stale as of 14 October.
7. Verify publisher end-to-end against exact SHA-256 and counts before any automatic schedule is considered.

No Apify calls, GitHub workflow triggers, live data writes or WordPress plugin changes are part of this PR.
