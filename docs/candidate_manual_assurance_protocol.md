# Manual review of 30-record pilot

The pilot evidence contains vacancy titles, source names and URLs only. It does not establish employer, UK location, posting date, full description, active status or confirmed taxonomy relevance.

Download the evidence artifact from [successful pilot run](https://github.com/thebaisify-droid/Salesforce-Tracker/actions/runs/37849106137). Unzip candidate-pilot-evidence.json, then execute:

```
python -m scripts.candidate_human_review_queue --pilot candidate-pilot-evidence.json --queue reports/candidate-human-review.json
```

The output contains 30 records with stable source/URL review identifiers, original source URLs, missing-evidence flags, and PENDING review decisions. A human reviewer should verify the employer and UK location, inspect a description, record posted date, capture a time-stamped URL confirming that the vacancy is active, label taxonomy relevance, and flag duplicates across sources. Inaccessible adverts must not be considered active.

The queue never enables automatic publication. Even a completed review is subject to independent QA and explicit release approval. No paid acquisition or scheduled execution is introduced.
