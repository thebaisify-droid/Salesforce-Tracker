# Daily source architecture

The confirmed daily production sources are the three saved Apify Tasks already created for this project:

1. **CV-Library** — `develop_ify/cv-library-scraper-task`
2. **Totaljobs** — `develop_ify/totaljobs-com-scraper-task`
3. **Reed** — `develop_ify/uk-jobs-reed-task`

Earlier references to Indeed, Lightcast or Adzuna are superseded for the daily production feed.

## Why these three

They give direct UK job-board coverage and reuse the collection assets already configured in Apify. Each board remains a separate source for lineage, source counts, deduplication and assurance.

## Saved Tasks

The pipeline calls the saved Tasks rather than raw Actors. This means each Task's stored input configuration remains the source of its scraper settings. Apify's API accepts a task by opaque ID or by the owner's username plus task name separated by `~`; the collector also accepts the slash-style references shown in the Apify console and converts them internally.

## Common-mode dependency

CV-Library, Totaljobs and Reed are separate underlying datasets, but all three run through Apify. A platform-wide Apify failure is therefore recorded as a common ingestion dependency failure.

## External assurance

Lightcast or Adzuna may still be added later as periodic validation benchmarks. They are not required for the daily refresh.

## Activation

The Task references are now wired. The three configs remain `ready=false` until the Apify token is available and each Task has been run once to validate the current output schema and verify that its saved input still represents the intended Salesforce/UK search.
