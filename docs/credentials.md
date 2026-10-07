# Source credentials

CV-Library, Totaljobs and Reed all run through saved Tasks in the same Apify account.

## Required secret

Only one production secret is required:

- `APIFY_TOKEN`

Add it under **GitHub → Settings → Secrets and variables → Actions → Secrets**.

The Task references are already stored in the repository and are not secrets:

- `develop_ify/cv-library-scraper-task`
- `develop_ify/totaljobs-com-scraper-task`
- `develop_ify/uk-jobs-reed-task`

## Local development

Copy `.env.example` to `.env` and set the token. The real `.env` is ignored by Git.

## Activation sequence

1. Add `APIFY_TOKEN`.
2. Run each saved Task independently from the pipeline.
3. Inspect the returned fields and confirm the saved Task input is still Salesforce + UK.
4. Add any source-specific field mapping/window field required by the observed output.
5. Set each source's `ready` flag to `true` after validation.
6. Run the pipeline preflight.
7. Run a forced three-source refresh and review the assurance evidence.
8. Only then enable scheduled live execution.
