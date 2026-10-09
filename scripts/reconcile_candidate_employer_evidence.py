"""Offline provenance overlay for the already-acquired Indeed cybersecurity pilot.

Source 'company' is an advertiser claim, NOT a verified hiring employer.
Official registry observations support an employer identity, not publication,
live vacancy status, or independent classifier accuracy.
No network, acquisition or production mutations.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "candidate-cyber-official-employer-evidence/v1"
GOV_HOST = "www.findapprenticeship.service.gov.uk"
PROTECTED = {
    Path("dashboard/live-data.json").resolve(),
    Path("dashboard/data.json").resolve(),
    Path("candidate-beta/data/pilot-snapshot.json").resolve(),
    Path("config/pipeline.json").resolve(),
}


def normal(value):
    return re.sub(r"\s+", " ", str(value or "").casefold()).strip()


def org_key(value):
    name = re.sub(r"[^a-z0-9 ]+", " ", normal(value))
    return " ".join("limited" if x == "ltd" else x for x in name.split())


def evidence_index(payload, source_rows, *, run_id):
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ValueError("Unexpected independent evidence schema")
    if payload.get("source_run_id") != run_id:
        raise ValueError("Independent evidence belongs to another run")
    if payload.get("publication_approved") is not False:
        raise ValueError("Evidence must never approve publication")
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError("Evidence records must be an array")
    known = {r["job_id"]: r for r in source_rows}
    output = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Invalid evidence record")
        job_id = str(item.get("source_job_id") or "")
        source = known.get(job_id)
        if not source or job_id in output:
            raise ValueError("Unknown or repeated source job ID")
        reference = str(item.get("government_vacancy_reference") or "")
        url = str(item.get("official_evidence_url") or "")
        u = urlsplit(url)
        if not re.fullmatch(r"VAC[0-9]{10}", reference):
            raise ValueError("Invalid government vacancy reference")
        if (u.scheme != "https" or u.hostname != GOV_HOST
            or u.path.rstrip("/") != "/apprenticeship/" + reference
            or u.username or u.password):
            raise ValueError("Evidence URL must match the official GOV.UK reference")
        if str(item.get("source_job_url")) != source["source_url"]:
            raise ValueError("Official evidence attached to the wrong source URL")
        if normal(item.get("official_title")) != normal(source["original_title"]):
            raise ValueError("Official listing title does not match source title")
        for field in ("hiring_employer", "training_provider", "official_title"):
            if not normal(item.get(field)):
                raise ValueError("Missing required official listing metadata")
        for field in ("government_posted_date", "government_closing_date", "observed_on"):
            try:
                date.fromisoformat(str(item[field]))
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("Invalid government evidence date") from error
        if item.get("evidence_type") != "UK_GOV_APPRENTICESHIP_LISTING":
            raise ValueError("Unknown evidence provenance")
        if item.get("live_vacancy_verified") is not False or item.get("human_approved") is not False:
            raise ValueError("Unreviewed evidence cannot establish live or approved status")
        output[job_id] = item
    return output


def reconcile(screen_report, evidence):
    if not isinstance(screen_report, dict) or screen_report.get("publication_approved") is not False:
        raise ValueError("Only unapproved screening reports may be reconciled")
    source_rows = screen_report.get("records")
    if not isinstance(source_rows, list):
        raise ValueError("Missing screened records")
    if len({r["job_id"] for r in source_rows}) != len(source_rows):
        raise ValueError("Duplicate source job identifiers")
    verified = evidence_index(evidence, source_rows,
                              run_id=screen_report.get("source_run_id"))
    enriched = deepcopy(screen_report)
    matched = defaultdict(list)
    by_official_employer = defaultdict(list)
    for row in enriched["records"]:
        source_id = row["job_id"]
        item = verified.get(source_id)
        advertiser = str(row.get("source_employer") or "").strip()
        # Preserve the legacy source_employer field; downstream consumers must
        # use source_advertiser for board claims, never as trusted end employer.
        row["source_advertiser"] = advertiser
        row["source_advertiser_role"] = "UNCONFIRMED"
        row["official_registry_hiring_employer"] = None
        row["training_provider"] = None
        row["official_government_reference"] = None
        row["official_evidence_url"] = None
        row["government_posted_date"] = None
        row["government_closing_date"] = None
        row["government_posting_conflicts_with_board"] = False
        row["registry_supports_hiring_employer"] = False
        row["human_confirmed_employer"] = False
        row["human_confirmed_role_family"] = None
        row["same_official_reference_review_ids"] = []
        row["same_official_employer_site_review_ids"] = []
        row["separate_official_requisition_from"] = []
        row["automatic_dedupe_performed"] = False
        row["publication_ready"] = False
        row["independently_verified"] = False
        if not item:
            continue
        employer = item["hiring_employer"].strip()
        provider = item["training_provider"].strip()
        reference = item["government_vacancy_reference"]
        row.update({
            "source_advertiser_role": (
                "TRAINING_PROVIDER_IN_OFFICIAL_LISTING"
                if org_key(advertiser) == org_key(provider) else "UNCONFIRMED"
            ),
            "official_registry_hiring_employer": employer,
            "training_provider": provider,
            "official_government_reference": reference,
            "official_evidence_url": item["official_evidence_url"],
            "government_posted_date": item["government_posted_date"],
            "government_closing_date": item["government_closing_date"],
            "government_posting_conflicts_with_board": (
                str(row.get("source_posted_at") or "")[:10]
                != item["government_posted_date"]
            ),
            "registry_supports_hiring_employer": True,
        })
        matched[reference].append(source_id)
        by_official_employer[(org_key(employer),normal(row["source_location"]))].append(source_id)

    lookup = {r["job_id"]: r for r in enriched["records"]}
    for row in enriched["records"]:
        sid = row["job_id"]
        reference = row["official_government_reference"]
        employer = row["official_registry_hiring_employer"]
        if reference:
            row["same_official_reference_review_ids"] = sorted(
                other for other in matched[reference] if other != sid
            )
            group = by_official_employer[(org_key(employer),normal(row["source_location"]))]
            row["same_official_employer_site_review_ids"] = sorted(
                other for other in group if other != sid
            )
            # Same title/advertiser/location is only an initial similarity
            # signal; distinct government references supersede it as a reason
            # to keep two listings separate pending human dedupe review.
            row["separate_official_requisition_from"] = sorted(
                other for other in row.get("same_title_employer_location_ids", [])
                if lookup[other].get("official_government_reference")
                and lookup[other]["official_government_reference"] != reference
            )
    enriched["schema"] = "candidate-cyber-employer-review/v1"
    enriched["official_registry_matches"] = len(verified)
    enriched["advertisers_correlated_to_training_providers"] = sum(
        row["source_advertiser_role"] == "TRAINING_PROVIDER_IN_OFFICIAL_LISTING"
        for row in enriched["records"]
    )
    enriched["distinct_official_vacancy_references"] = len(matched)
    enriched["official_employer_counts"] = dict(sorted(Counter(
        row["official_registry_hiring_employer"] for row in enriched["records"]
        if row["official_registry_hiring_employer"]
    ).items()))
    enriched["human_approved_count"] = 0
    enriched["auto_merged_count"] = 0
    enriched["independently_verified_count"] = 0
    enriched["publication_approved"] = False
    enriched["note"] = (
        "Government apprenticeship register corroborates hiring employer, "
        "not current live status, human role-family approval or market coverage. "
        "Separate job-board advertiser from employer, and never auto-merge."
    )
    return enriched


def main():
    p = argparse.ArgumentParser(description="Offline employer-vs-advertiser QA overlay")
    p.add_argument("--screening", required=True, help="Private screened Indeed dataset JSON")
    p.add_argument("--evidence",
        default="docs/evidence/candidate_cyber_gov_apprenticeships_2026-10-09.json")
    p.add_argument("--output", required=True, help="Private reviewer JSON file")
    args = p.parse_args()
    output = Path(args.output).resolve()
    if output in PROTECTED or output in {
        Path(args.screening).resolve(), Path(args.evidence).resolve()
    }:
        p.error("Refusing overwrite of private input or production output")
    screened = json.loads(Path(args.screening).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    result = reconcile(screened, evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ("records","official_employer_counts")},sort_keys=True))


if __name__ == "__main__":
    main()
