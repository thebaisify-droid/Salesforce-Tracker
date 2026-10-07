# Salesforce Tracker

UK Salesforce hiring-market tracker with a daily incremental refresh pipeline, source assurance, vacancy classification, and dashboard publishing.

## Current implementation status

The repository has been created and connected to ChatGPT.

The daily refresh orchestration layer is being integrated with the existing tracker codebase. Before the scheduled refresh is enabled, the repository still needs the existing:

- three source collectors;
- transform / normalise / deduplicate / upsert process;
- role and sector classification logic;
- dashboard publisher;
- database/configuration integration.

The refresh pipeline uses a 72-hour overlapping incremental window and requires 3/3 sources by default. Publication is blocked if source evidence or quality checks fail.

## Safety

Do not commit secrets, API tokens, passwords, .env files, database backups, or private credentials. Use GitHub Actions secrets / environment variables for runtime credentials.
