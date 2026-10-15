# WordPress handoff release control

A gated single-attempt delivery step is attached to the controlled refresh workflow.

Two separate GitHub repository variables must be set to the literal string
`true` before any delivery can happen:
- `SF_CONTROLLED_REFRESH_ENABLED`: enables paid acquisition under the $19
  account ceiling and $8 protected reserve.
- `SF_WORDPRESS_DELIVERY_ENABLED`: enables delivery of a fresh, QA-passed
  snapshot from the *same successful workflow run*.

Both remain unset/off by default. The handoff first validates the WordPress
receiver schema and freshness and rejects any restored snapshot not matching
the most recent successful pipeline attempt. Skipped and failed runs never
resend previous data. The sender performs a single authenticated HTTPS request;
no retries or redirects are permitted. Authentication uses existing repository
secrets `SF_WP_USERNAME` and `SF_WP_APPLICATION_PASSWORD`.

Deployment does not alter public page #85. The installed shortcode on draft
page #95 reads the delivered local snapshot, but page #85 still presents the
33-row source-observed research preview.

Before enabling either flag, confirm actual reserve headroom, source cost
caps, and preview usability; verify the plugin's transport contract and a
fresh snapshot on WordPress. No new paid Apify runs were launched by this PR.
