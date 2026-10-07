# Source credentials

Keep all live credentials outside Git.

## Required secrets

For the proposed three-source architecture:

- `LIGHTCAST_CLIENT_ID`
- `LIGHTCAST_CLIENT_SECRET`
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`
- `APIFY_TOKEN`

For GitHub Actions, add them under **Settings → Secrets and variables → Actions → Secrets**.

For local or persistent-host execution, copy `.env.example` to `.env` and fill the values. `.env` is ignored by Git.

## Activation sequence

1. Add the credentials.
2. Test each collector independently.
3. Set only that source's `ready` flag to `true` after it returns valid UK Salesforce records.
4. Repeat for all three sources.
5. Run `python -m pipeline.daily_refresh --config config/pipeline.json --check`.
6. Run one forced refresh and review the quality evidence.
7. Only then enable scheduled live execution.
