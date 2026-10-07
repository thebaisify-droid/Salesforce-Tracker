# Daily source architecture

The daily production tracker uses the three UK job-board sources already selected and available through the user's Apify account:

1. **CV-Library**
2. **Totaljobs**
3. **Indeed**

These replace the temporary Lightcast/Adzuna/LinkedIn proposal that was added only because the earlier Apify Actor details were not recoverable from the project chat.

## Why these three

They give direct coverage of the UK vacancy market relevant to the tracker and avoid adding new provider accounts solely to make the daily pipeline work. Each board is treated as a separate underlying data source, while Apify is treated as the shared ingestion platform.

## Common-mode dependency

Three successful Actor runs do not mean three independent technical collection paths: all three rely on Apify. The run evidence therefore records each board separately but operational monitoring must also distinguish an **Apify platform failure** from a board-specific scraper/schema failure.

## External assurance

Lightcast or Adzuna may still be added later as a weekly/monthly validation benchmark. They are **not required for the daily refresh**.

## Activation

The three source configs remain `ready=false` until the exact existing Actor or Task IDs and their working input configurations are wired in and validated. Do not put the Apify token in Git.
