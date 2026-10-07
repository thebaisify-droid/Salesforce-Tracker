# Source credentials

The three daily sources — CV-Library, Totaljobs and Indeed — run through Apify.

## Required secret

- `APIFY_TOKEN`

Add it under **GitHub → Settings → Secrets and variables → Actions → Secrets**.

## Actor IDs

The Actor IDs are not passwords. Until the exact IDs are placed in the source config files, the workflow reads these repository variables:

- `APIFY_CV_LIBRARY_ACTOR_ID`
- `APIFY_TOTALJOBS_ACTOR_ID`
- `APIFY_INDEED_ACTOR_ID`

If the existing Apify setup uses saved **Tasks** rather than raw Actors, the collector also supports `provider: "apify_task"` and a Task ID.

## Local development

Copy `.env.example` to `.env`. The real `.env` is ignored by Git.

## Activation sequence

1. Add the Apify token.
2. Supply the three existing Actor/Task URLs or IDs.
3. Wire each actor's known Salesforce/UK input configuration.
4. Run each source independently and inspect its raw output.
5. Set that source's `ready` flag to `true` only after validation.
6. Run the pipeline preflight.
7. Run a forced three-source refresh and review quality/deduplication evidence.
8. Only then enable scheduled live execution.
