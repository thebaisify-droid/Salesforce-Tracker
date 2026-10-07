# Source configuration

The confirmed daily sources are saved Apify Tasks:

- CV-Library — `develop_ify/cv-library-scraper-task`
- Totaljobs — `develop_ify/totaljobs-com-scraper-task`
- Reed — `develop_ify/uk-jobs-reed-task`

## Apify Task

```json
{
  "ready": false,
  "provider": "apify_task",
  "task_id": "develop_ify/cv-library-scraper-task",
  "token": "env:APIFY_TOKEN",
  "timeout_seconds": 300
}
```

The collector accepts either the console-style `owner/task-name` reference or Apify's API-style `owner~task-name` reference. Saved Task input is used unchanged unless an explicit `input` object is added to the source config, in which case it is sent as a run-time override.

## Incremental window

The pipeline itself runs with a 72-hour overlapping window. After the first live Task validation, each source config may also specify `window_field` so the collector can trim a wider Task result to the exact pipeline window.

## Go-live rule

Do not set a source to `ready=true` until its Task has been run independently and the returned dataset has been inspected for:

- stable source record ID;
- title;
- advertiser/company where available;
- location;
- description;
- canonical job URL;
- posting timestamp/date where available.

The real `APIFY_TOKEN` must remain outside Git.
