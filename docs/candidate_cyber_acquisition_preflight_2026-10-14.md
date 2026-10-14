# Proposed isolated two-source UK cybersecurity pilot — NOT AUTHORISED

Reviewed: **14 October 2026**, using published Apify Actor Store input schemas and BRONZE pricing.

The next useful experiment is two **one-off** UK-wide searches, each capped at **10 results** with a separately enforced run-charge setting of **$0.10**, combined maximum **$0.20**:

| Source | Query | Schema | BRONZE price observation |
| --- | --- | --- | --- |
| Indeed UK | `information security analyst` | `query`, `country=uk`, `maxResults=10` | $0.0036 per unique job |
| JobServe | `third party risk analyst` | `keywords` array, `country=gb`, `postedSince=7`, `maxResults=10` | $0.00285 per result + $0.005 Actor start minimum |

**Important:** These per-result rates are informational; they are not an account invoice. The JobServe Actor can return up to a full additional page beyond `maxResults`. The API-level `maxTotalChargeUsd` setting is a separate run option, not an Actor input field; hitting the cap can abort an Actor rather than produce a complete dataset. Failed and aborted runs **must not be retried without a new approval**. Provider charges, platform resources, Account limits and spending headroom must all be checked immediately before any execution.

Other Actors: Totaljobs has a published BRONZE start charge of $0.07 and $0.00173/listing (optional detail enrichment $0.0007/job); CV-Library publishes $0.005/start plus $0.0015/result but previous MAX_TOTAL_CHARGE failures require charging-constraint review; Reed publishes $0.00005/start plus $0.00085/job and remains optional enrichment. These are not part of the $0.20 pilot.

The shared Apify account limit remains **$19** and the protected Salesforce reserve **$8**. A fresh, authenticated account-usage/balance reading and confirmation of the independent account spending limit are **not yet available** through the currently connected tools. Therefore `approved_spend_usd=0` and `actor_runs_allowed=0`; no source is permitted to run, and no workflow, schedule, mutation, or publication is enabled.

**Before approval:** confirm fresh account usage and remaining unreserved balance, verify the account cap, assess the latest Actor charging behavior, present the exact two-run proposal, and obtain explicit *new* one-time approval for a maximum $0.20. Keep the live Salesforce tracker unchanged. Following a permitted acquisition, run isolated ingestion, 22-family relevance classification, freshness, cross-board duplicate review, employer-side checks and independent labelling. Never claim representative UK demand or publish unverified records.
