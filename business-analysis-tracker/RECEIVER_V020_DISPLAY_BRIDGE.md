# Business Analysis receiver 0.2.0 — read-only dashboard bridge

The standalone receiver at `wordpress/business-analysis-snapshot-receiver/business-analysis-snapshot-receiver.php` now adds **server-side rendering of previously accepted snapshots for WordPress page 49 only**.

## Verified controlled receiver test

GitHub Actions run 38802092234 completed a one-time checksum-verified delivery of the **existing 57 source-observed advertisements** to the dedicated BA receiver, receiving `accepted=true` and a 57-row acknowledgement. No paid Apify Actors were run. The source-observed time is the real last completed source run's time; it is not a new scrape.

A direct browser request to `/wp-content/uploads/business-analysis-tracker/live-data.json` returned **403 from LiteSpeed**. Do not remove upload protection or open the directory publicly. This update instead uses a private local PHP file read inside WordPress, with no external HTTP requests.

## How display works

- The bridge is a `the_content` filter restricted to `is_page(49)` and page ID 49.
- It reads the locally stored JSON only if present, below the size limit and not a symlink.
- It checks schema, success and QA status, exactly five distinct successful source receipts, matching per-row provenance, valid HTTPS original advert URLs and unique row IDs.
- It replaces only the existing BA table body and embedded JSON data, with escaped fields. The existing client-side search, filters and sort use the new embedded JSON automatically.
- It shows **Last source observation**, not a false live-refresh timestamp.
- Any missing, invalid or unreadable file returns the existing 57-record page unchanged.
- Salesforce page 31, Salesforce receiver, WordPress DB content, Apify billing, schedules and permissions are untouched.

## Deployment and rollback

**The GitHub plugin update is not automatically installed on WordPress.** The installed receiver is still version 0.1.0 until updated by the administrator. Upload the version 0.2.0 plugin ZIP through Plugins → Add New → Upload Plugin, confirm replacement of the existing plugin, then verify the page displays `ba-snapshot-observed`, retains 57 table rows and 57 original advert links, and its filters still work. For rollback, reinstall 0.1.0; the current static page content remains untouched.

Do not use a draft-theme publish for this change: the active theme registers activation/deactivation actions unrelated to BA. The plugin-only upgrade is the safer isolation boundary.

**The plugin can display accepted snapshots, but recurring paid acquisition and automatic WordPress delivery remain disabled.** Future approved snapshots can use the same isolated authenticated endpoint.
