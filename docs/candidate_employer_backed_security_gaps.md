# Missing cybersecurity families — employer-backed discovery, 9 October 2026

This is a **read-only, zero-Apify-spend** research handoff. Source URLs and role
descriptions were observed; no live application path has been completed and no
human has approved classification or publication.

| Family | Candidate | Evidence tier | Reference |
|---|---|---|---|
| Information Security Analysis | Sony Pictures — Analyst, Information Security, London | Employer's own careers page, Apply link present | JR114830 |
| Security Risk & Third-Party Risk | Maritime and Coastguard Agency — Information Security - Risk Analyst (Third Party Risk), Southampton | Public sector vacancy syndicated across job boards; direct Civil Service application flow not confirmed | 482482 |

**Sony** posted date claim is 7 October 2026, source role responsibilities
include security alerts, incident response, threat investigations and documentation.
The title `Analyst, Information Security` is the reverse-wording variant of the
configured Information Security Analysis family; the more operational SOC-like
responsibilities still require human family adjudication.

**MCA** syndicated advert gives a closing-date claim of 19 October 2026. Supplier
security assessments, third-party risk and information security governance
are explicit. This is a proposed Security Risk & Third-Party Risk match, *not*
confirmed active on an employer-native portal. The advertised position reference
is 482482, corroborated by a second independent job-board page. No employee
or recruiter contact details are retained.

Both records are excluded from public market counts, marked
`publication_ready=false`, and kept separate from the 30 historical beta jobs,
the 15-job first Indeed pilot and the 20-job targeted pilots. They cannot be
used to assert representative coverage, current active listings, precision,
recall or volume of UK cybersecurity hiring. Neither the public WordPress data
nor the Salesforce production pipeline changes.

For follow-up, prioritise: verify the employer application process and requisition
status, independently adjudicate role family, check posting and closing dates,
cross-source requisition-level duplicates, and record dated reviewer sign-off.
Exclude old/expired or unverified adverts without inventing status.

See the machine-readable, unapproved evidence file at
`docs/evidence/candidate_employer_backed_security_gaps_2026-10-09.json`.

## 10 October 2026 — application journey status check (read-only)

Evidence recorded in `docs/evidence/candidate_cyber_application_checks_2026-10-10.json`.

| Lead | Listing checked | Official application destination | Outcome |
|---|---|---|---|
| Sony Pictures JR114830 | Employer careers page loads with full role and **Apply** link | Sony Workday `.../Analyst--Information-Security_JR114830/apply` | Automated application page fetch inaccessible. **Do not report live form verified.** |
| MCA 482482 | Jobsgopublic advert and multiple syndicated corroborations readable; 19 October closing date claimed | Civil Service Jobs `https://www.civilservicejobs.service.gov.uk/csr/jobs.cgi?jcode=2015051` | Followed official link, but portal requires human verification. **Do not report live form verified.** |

For Sony, original job title suggests *Information Security Analysis*, but actual alert
triage, EDR/SIEM and incident-response responsibilities overlap *Security Operations
/ SOC*. Human role-family classification must resolve that overlap.

For MCA, the job description clearly centres supplier information-security
assessment and third-party risk, supporting the proposed risk family. The
syndicated employer reference **482482** and Civil Service portal job code
**2015051** are distinct numbering systems; do not claim a fully verified
cross-system mapping until the protected official page is reviewed by a person.

**Manual human reviewer tasks before publication:** open the Sony Workday
application link and official Civil Service Jobs link in a normal browser;
confirm both requisitions are accepting applications; record check timestamp,
actual employer and reference, and separately approve one primary role family;
check exact and cross-source duplicates; record named dated sign-off.
Do not attempt to bypass login, CAPTCHA or site access controls.

To validate the current unapproved evidence without any network calls:

```bash
python -m scripts.assess_candidate_application_evidence --output /private/cyber-application-review.json
```

This creates a **private reviewer handoff**, not publishable jobs. The validator
fails if the checks falsely claim live status, human review or publication.
No new Apify run or website update is authorised by this evidence.
