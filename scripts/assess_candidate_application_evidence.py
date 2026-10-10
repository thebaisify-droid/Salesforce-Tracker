"""Validate read-only employer/application observations against existing private QA leads.

Never treats merely viewing a page or an Apply link as a confirmed live vacancy.
No HTTP calls, Actor calls, production writes, or automatic release approvals.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

LEAD_SCHEMA = "candidate-employer-security-gap-leads/v1"
CHECK_SCHEMA = "candidate-cyber-application-observation/v1"
ALLOWED_OUTCOMES = {
    "sony-pictures-JR114830": "AUTOMATED_FETCH_INACCESSIBLE",
    "maritime-coastguard-482482": "OFFICIAL_PORTAL_HUMAN_VERIFICATION_GATE",
}
PROTECTED = {
    Path("dashboard/live-data.json").resolve(),
    Path("dashboard/data.json").resolve(),
    Path("candidate-beta/data/pilot-snapshot.json").resolve(),
    Path("docs/evidence/candidate_employer_backed_security_gaps_2026-10-09.json").resolve(),
    Path("docs/evidence/candidate_cyber_application_checks_2026-10-10.json").resolve(),
}


def _https(value: str, host: str) -> bool:
    p = urlsplit(str(value or ""))
    return (p.scheme == "https" and p.hostname == host
            and not p.username and not p.password)


def assess(leads: dict, checks: dict) -> dict:
    if leads.get("schema") != LEAD_SCHEMA or checks.get("schema") != CHECK_SCHEMA:
        raise ValueError("Unexpected source/evidence schemas")
    if leads.get("publication_approved") is not False or checks.get("publication_approved") is not False:
        raise ValueError("Approval cannot be inferred from unreviewed source pages")
    if checks.get("new_apify_paid_runs") != 0:
        raise ValueError("Read-only review must not claim additional paid runs")
    if checks.get("observation_mode") != "READ_ONLY_NON_AUTHENTICATED":
        raise ValueError("Unrecognised acquisition/observation mode")
    try:
        asof = date.fromisoformat(checks["observed_on"])
        if asof < date.fromisoformat(leads["observed_on"]):
            raise ValueError("Application checks precede the original source evidence")
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid observed date") from error
    source_rows = leads.get("leads")
    observed = checks.get("records")
    if not isinstance(source_rows, list) or not isinstance(observed, list):
        raise ValueError("Expected lists of independent evidence records")
    sources = {row["lead_id"]: row for row in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("Duplicate source lead IDs")
    if (set(sources) != set(ALLOWED_OUTCOMES) or len(observed) != len(sources)
            or {x["lead_id"] for x in observed} != set(sources)):
        raise ValueError("Unexpected, missing, or duplicated application evidence lead")
    rows = []
    for row in observed:
        identity = row["lead_id"]
        source = sources[identity]
        if (row.get("employer_reference") != source["employer_reference"]
                or row.get("source_page_url") != source["evidence_url"]
                or row.get("proposed_primary_family") != source["proposed_family"]):
            raise ValueError("Application evidence does not match original lead")
        if (row.get("application_destination_outcome") != ALLOWED_OUTCOMES[identity]
                or row.get("application_status") != "NOT_VERIFIED"
                or row.get("vacancy_live_independently_verified") is not False
                or row.get("role_family_human_approved") is not False
                or row.get("human_publication_signoff") is not False
                or row.get("publication_ready") is not False
                or row.get("source_page_access") != "ACCESSIBLE_WITH_ROLE_DETAILS"):
            raise ValueError("Unsupported claim of vacancy verification or publication")
        url = str(row.get("observed_apply_destination") or "")
        if identity.startswith("sony-"):
            if (not _https(url, "spe.wd1.myworkdayjobs.com")
                    or not urlsplit(url).path.endswith("/apply")
                    or source["employer_reference"] not in urlsplit(url).path
                    or row.get("source_kind") != "EMPLOYER_DIRECT"):
                raise ValueError("Sony Apply link provenance invalid")
        else:
            if (not _https(url, "www.civilservicejobs.service.gov.uk")
                    or urlsplit(url).path != "/csr/jobs.cgi"
                    or parse_qs(urlsplit(url).query).get("jcode") != ["2015051"]
                    or row.get("official_portal_job_code") != "2015051"
                    or row.get("source_kind") != "SYNDICATED_PUBLIC_SECTOR"):
                raise ValueError("MCA Civil Service application route provenance invalid")
        rows.append({
            "lead_id": identity, "employer": source["employer_name"],
            "reference": source["employer_reference"],
            "proposed_family": source["proposed_family"],
            "source_page_access": row["source_page_access"],
            "application_status": "NOT_VERIFIED",
            "human_role_review": "PENDING",
            "human_publication_signoff": "PENDING",
            "publication_ready": False,
        })
    return {
        "schema": "candidate-cyber-application-assurance/v1",
        "observed_on": asof.isoformat(),
        "leads_checked": len(rows),
        "employer_direct_source_count": sum(r.get("source_type") == "EMPLOYER_CAREERS_PAGE"
                                            for r in source_rows),
        "readable_source_pages": len(rows),
        "application_flows_independently_verified": 0,
        "human_role_reviews_completed": 0,
        "publication_approved": False,
        "live_vacancies_confirmed": 0,
        "paid_apify_runs_started": 0,
        "review_queue": rows,
        "limitations": [
            "Readable listing and Apply link are not proof the application form remains open.",
            "Official Civil Service link resolves to a human verification challenge; no bypass attempted.",
            "Sony InfoSec analyst duties also resemble SOC, so human family adjudication remains required.",
            "No market volume, current vacancy status, or publication eligibility inferred."
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Assess two known employer-backed cyber QA leads offline")
    p.add_argument("--leads", default="docs/evidence/candidate_employer_backed_security_gaps_2026-10-09.json")
    p.add_argument("--checks", default="docs/evidence/candidate_cyber_application_checks_2026-10-10.json")
    p.add_argument("--output", required=True, help="Private output outside public dashboard")
    args = p.parse_args()
    target = Path(args.output).resolve()
    if target in PROTECTED or target in {Path(args.leads).resolve(), Path(args.checks).resolve()}:
        p.error("Refusing to overwrite inputs, evidence, public beta, or Salesforce dashboard")
    leads = json.loads(Path(args.leads).read_text(encoding="utf-8"))
    checks = json.loads(Path(args.checks).read_text(encoding="utf-8"))
    result = assess(leads, checks)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ("review_queue","limitations")},sort_keys=True))


if __name__ == "__main__":
    main()
