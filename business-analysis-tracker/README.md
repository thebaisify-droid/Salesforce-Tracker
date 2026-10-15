# Business Analysis Vacancy Explorer — isolated pilot

This is a separate WordPress **draft** preview for the UK Business Analysis, Product, Delivery and Cyber job families, matching the Salesforce Tracker display pattern. It does **not** change Salesforce production. WordPress draft ID: **155**, site: `https://jobs.zarafytek.com`.

## Source-of-truth and current results

- Input: existing 8 October 2026 Apify three-source pilot snapshot (`candidate-beta/data/pilot-snapshot.json`).
- 30 source-observed historical records from Totaljobs, Indeed UK and JobServe; 25 match the title-based BA/Product/Delivery/Cyber taxonomy. Five are excluded.
- **22 specific role families**, plus the screenshot's **Information Security / Cyber Security** umbrella group filter. The umbrella combines seven security families without double-counting.
- Lack of source dates, job descriptions, employment details, skills and sectors is shown as *Not specified*, **never invented**.
- Dashboard is labelled historical **source-observed**, not currently live, not employer-verified and not representative of current UK demand.
- One-click links go to original advertisements, which may no longer be active.

## Reproduce and test locally

```bash
python -m scripts.build_ba_tracker_existing_pilot
python -m unittest discover -s tests -p test_ba_tracker_existing_pilot.py -v
```

The snapshot builder is offline and uses zero Apify calls. It refuses a purported publication-approved pilot and does not touch Salesforce production files, existing WordPress pages or Actor inputs.

## Rollout boundaries

1. Preview and test filters, URL links, text overflow, security umbrella and mobile layout.
2. Link richer existing completed BA/Cyber Apify datasets only when their precise run IDs and schema are known. Keep the source query scope documented and deduplicate across boards.
3. For a **fresh** automated BA acquisition feed, first verify non-Salesforce keyword configurations and charging, preserve the shared **$19 monthly account cap and $8 Salesforce reserve**, then secure express authorisation for any new paid Apify activity. No BA paid schedule is enabled by this change.
4. Publish the BA page separately after preview QA; report collection timestamp and freshness honestly. This does not require independently verifying individual advertisements, but it must not claim a source listing is confirmed active without current status evidence.

The existing published Business Analysis research beta (WordPress ID 49) stays unchanged. The user can inspect draft 155 from WordPress admin and decide when to replace/promote the page.
