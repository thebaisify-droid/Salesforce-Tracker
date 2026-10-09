# Cyber pilot: employer identity and duplicate evidence

Run in an **offline/private** working directory with an already-acquired
`wildorigins/indeed-jobs` JSON export; do **not** commit the raw dataset.

```bash
python -m scripts.screen_indeed_cyber_pilot \
  --input /private/cyber-indeed-source.json \
  --output /private/cyber-indeed-screened.json \
  --as-of 2026-10-09
python -m scripts.reconcile_candidate_employer_evidence \
  --screening /private/cyber-indeed-screened.json \
  --evidence docs/evidence/candidate_cyber_gov_apprenticeships_2026-10-09.json \
  --output /private/cyber-indeed-employer-review.json
```

The source Actor's `company` is **the job-board's claimed advertiser/company**, not
an independently validated end employer. Official GOV.UK apprenticeship listings
identify Specialist Network Operations as the hiring employer for two Oswestry
apprenticeships while QA LIMITED is the training provider.

The overlay keeps the original source field for compatibility and adds
`source_advertiser`, `official_registry_hiring_employer`,
`training_provider`, independent listing evidence URL and government
reference. It never marks vacancy status, classification or publication as approved.

Two distinct government vacancy references must not be merged automatically just
because the listed training provider, workplace and pay coincide. Same-reference
or same-employer signals remain **review queues**, not automatic database merges.

Any other job without acceptable independent corroboration keeps its employer
and classification unapproved. Historic public beta remains 30 unverified records;
Salesforce production remains untouched. No Apify Actor starts or schedules.

These two government listings were observed 9 October 2026; their published
posting date is 24 August and closing date is 16 October 2026. Those are
source claims, not proof of continuous live application status.

References:

- https://www.findapprenticeship.service.gov.uk/apprenticeship/VAC2000049619
- https://www.findapprenticeship.service.gov.uk/apprenticeship/VAC2000049612
