# Candidate market evidence quality gate

This is a read-only, offline audit independent of the live Salesforce tracker. Use candidate records containing title, URL, source, employer, location, description, posted_date, active_verified, manual_relevance_verified and verified_role_family where corroborated. Missing metadata is marked **unverified**, never fabricated.

Run: `python -m scripts.candidate_evidence_gate --input records.json --output reports/candidate-evidence-gate.json`.

Output always has `publication_approved: false` and `passed: false` until a separate approved release review is designed. Exact normalized URL identifiers and identical title/employer/location flag duplicates; other cross-source duplicate patterns require human review. Verifying UK location requires more than a source domain, and a valid-looking URL is not proof of a live vacancy.

For the pilot, preserve all 30 original records without pretending the 24 provisional matches are verified. The one-keyword Business Analyst pilot cannot establish 22-family coverage, especially the seven cybersecurity families. Future isolated search profiles should intentionally cover security families, with no paid queries until separately authorised.

No Apify API use; no scheduled or paid execution; no publication.
