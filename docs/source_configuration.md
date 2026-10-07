# Source configuration

The tracker has three source slots. Their exact providers are deliberately not hard-coded until the live sources are confirmed.

## Apify Actor

```json
{
  "ready": true,
  "provider": "apify_actor",
  "actor_id": "username~actor-name",
  "token": "env:APIFY_TOKEN",
  "timeout_seconds": 300,
  "input": {
    "query": "Salesforce",
    "country": "United Kingdom",
    "from": "{since}",
    "to": "{until}"
  }
}
```

`{since}` and `{until}` are supplied by the 72-hour incremental refresh window. The exact actor input fields must match the chosen Actor.

## HTTP JSON API

```json
{
  "ready": true,
  "provider": "http_json",
  "url": "https://example.invalid/jobs",
  "method": "GET",
  "query": {
    "q": "Salesforce",
    "from": "{since}",
    "to": "{until}",
    "api_key": "env:SOURCE_1_API_KEY"
  },
  "collection_key": "jobs"
}
```

Environment-backed values use `env:VARIABLE_NAME`, keeping secrets out of Git.

## Go-live rule

Do not set a source to `ready=true` until it has been tested independently and its output contains a stable source record ID, title, advertiser/company where available, location, description, URL and posting timestamp where available.
