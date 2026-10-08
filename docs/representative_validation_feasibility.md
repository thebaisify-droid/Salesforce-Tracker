# Feasibility gate for 22-family representative sampling

The proposed $1.50 total and $0.15 per Actor run permit **at most ten full-cap invocations**. There are **22 distinct family-specific queries**, so one independent Actor invocation for each family cannot be promised inside this budget. Batching keywords might help, but is neither schema-confirmed nor cost-verified for every Actor. A sample of at least 100 human-reviewed records with at least five per family would need at least 110 records and a sufficient yield of real relevant advertisements, not merely 100 scraped items.

Until Actor multi-keyword compatibility, pricing, projected yield and account-usage headroom are evidenced, the proposed pilot is **NOT READY** for paid execution. This validation is intentionally offline and fail-closed. It never approves a run or publishes PR #28.

Run offline: `python -m scripts.validate_representative_feasibility`. Do not reuse old approval phrases or dispatch older pilot workflows.
