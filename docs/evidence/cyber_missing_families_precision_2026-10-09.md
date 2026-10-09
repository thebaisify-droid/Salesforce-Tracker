# Cybersecurity missing-family acquisition: precision review (9 October 2026)

**Evidence**: two already authorised, completed Indeed UK searches, exactly 10 rows per run, with no additional collection here.

| Query | Run | Rows | Clear target family from title/snippet | Human-review possible | Off-scope or insufficient |
|---|---|---:|---:|---:|---:|
| information security analyst | `lhAIJ1XaBm7vPB9sw` | 10 | 1 | 1 | 8 |
| third party risk analyst | `cfBxgqXh3BgqsSgoc` | 10 | 0 | 1 | 9 |

Classification is **screening judgment only**, not human-approved ground truth. The clear security candidate is Deloitte's *Cybersecurity Controls Testing Analyst* (ID `1e2c1aacae2968b9`), potentially Information Security Analysis, but it could instead map to security assurance/risk after full-description review. Deloitte's *Insider Threat Analyst* (ID `50f1061b80b6ee7a`) is a possible information-security/SOC role pending confirmation. The *Risk and Control Analyst* at BAM (ID `1e2005a09707a403`) requires context review; the snippet alone does not establish a cyber/third-party technology-risk role.

Clear non-target examples in Information Security search: Defence & Security **Business Analyst** titles, Workday Analyst, HR Oracle consultant, general Service Desk Analyst, UX designer and GMI migration BA. A sector called Defence & Security or a security clearance requirement does not turn a vacancy into a cyber-security job family.

The second search predominantly returned generic Risk Assessor, Risk Specialist, Risk Analyst and Quantitative Risk Analyst titles without third-party/vendor/ICT security-risk evidence, including multiple SThree adverts. These should not be counted as verified Third-Party Risk vacancies.

## Search design improvements — proposal only (no runs authorised)

Information Security Analysis:
- `information security analyst ISO 27001`
- `cyber security governance analyst`
- `information security assurance analyst`

Third-Party Risk:
- `third party cybersecurity risk analyst`
- `supplier information security risk`
- `technology vendor risk analyst TPRM`

Prioritise employer vacancy pages and original descriptions, require cyber/infosec/technology-risk context and distinct requisitions. Capture employer/advertiser separately, posting dates, and duplicate references. Use smaller balanced stratified searches; **do not equate a query string with a family label**. Any further paid acquisition requires a fresh budget check and new exact authorisation.

Both 10-row datasets remain **private in Apify**. No public beta or Salesforce pipeline changes. `publication_approved=false` for all records.
