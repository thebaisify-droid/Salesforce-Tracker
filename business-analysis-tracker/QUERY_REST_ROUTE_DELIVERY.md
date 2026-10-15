# BA WordPress query-route transport (pre-activation)

The origin HTTPS access log on 2026-10-15 recorded HTTP 404 for the pretty REST URL `/wp-json/wp/v2/users/me?context=edit`. The WordPress site's permalink structure was empty, and the existing WPVibe REST access continued to work. The BA-only transport therefore now uses the standard WordPress query-based `?rest_route=` routing form. This change does not touch the Salesforce integration.

## Fixed authenticated URLs

- Identity check (GET only): `https://jobs.zarafytek.com/?rest_route=/wp/v2/users/me&context=edit`
- BA receiver (POST only after separate approval): `https://jobs.zarafytek.com/?rest_route=/business-analysis-tracker/v1/snapshot`
- Historic BA page 49 sender (disabled): `https://jobs.zarafytek.com/?rest_route=/wp/v2/pages/49&context=edit` for GET and `?rest_route=/wp/v2/pages/49` for PUT.

The receiver itself remains gated by dedicated application-password authentication and `ba_deliver_snapshot` capability. All current run paths are read-only; neither automatic publication nor paid Apify acquisition is enabled.

## Narrow Cloudflare Browser Integrity Check skip

Cloudflare's existing BIC Skip custom rule must be extended, **not replaced with an unrestricted allowlist**. Include the exact root-path query URLs, with their methods and hostname. Example conditions to OR into the existing rule:

```
(http.host eq "jobs.zarafytek.com" and http.request.uri.path eq "/" and
 (
   (http.request.method eq "GET" and
    http.request.uri.query eq "rest_route=/wp/v2/users/me&context=edit")
   or
   (http.request.method in {"POST" "OPTIONS"} and
    http.request.uri.query eq "rest_route=/business-analysis-tracker/v1/snapshot")
 )
)
```

Choose **Skip → Browser Integrity Check only**. Keep other protections and logging. Do not skip all custom/managed WAF rules or allowlist broad GitHub/Azure IP blocks. This rule does not allow general `/` browsing to bypass BIC; it matches exact query strings and methods.

The Cloudflare rule must be saved by a user with access to that Cloudflare zone. No Cloudflare configuration change is made by this GitHub PR.

## One read-only check

The one-time GitHub workflow `ba-query-rest-auth-once.yml` performs exactly one authenticated GET using existing `BA_WP_USERNAME` and `BA_WP_APPLICATION_PASSWORD` secrets. It reports HTTP status, WordPress error code if JSON, response content type, and Cloudflare Ray ID if present, but never outputs the credentials, sends a snapshot, runs an Actor or mutates WordPress.

Do not start recurring refresh until the dedicated transport is verified, a controlled test snapshot passes the receiver, and the dashboard has a safe live-data display bridge. The public BA page continues displaying its 57 currently published source advertisements.
