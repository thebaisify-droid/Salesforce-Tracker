"""Export all 161 already-acquired BA source observations for human review.

Strictly offline, no paid Actor requests, WordPress writes or auto publication.
The evidence has source-trimmed descriptions and contacts redacted; original
advert URLs allow reviewers to inspect the upstream listing themselves.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

from scripts.ba_stage_five_source_data import (
    cleaned_excerpt, company, employment, link, location, posted,
    promotional_training_lead, working,
)
from tracker.business_product_delivery_security import classify_market_role

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "business-analysis-tracker/evidence/ba-five-completed-20261016-audit-redacted.json"
OUTPUT = ROOT / "dist/uk-business-technology-161-vacancies-manual-review-2026-10-16.csv"
SOURCES = {"CV-Library": 30, "Totaljobs": 25, "Reed UK": 30, "Indeed UK": 30, "JobServe": 46}

COLUMNS = [
    "Record #", "Review decision (Keep / Exclude / Needs review)", "Reviewer notes",
    "Corrected job family (if needed)", "Review priority", "Suggested review status",
    "Source", "Original job advert URL", "Job title", "Advertiser / agency",
    "Location", "Source posted date (UK)", "Employment type", "Working arrangement",
    "Classifier role family", "Role category", "Classifier matched phrase",
    "Classifier reason", "Classification confidence note",
    "Training / placement promotion flag", "Potential duplicate review",
    "Sector (evidence-backed)", "Sector evidence status",
    "Job description excerpt (truncated in evidence)",
    "Original run ID", "Dataset ID", "Observed at (UTC)", "Source query family",
    "Original source records", "Source count exceeded requested 30",
]

QUERY = {
    "CV-Library": "Security Management",
    "Totaljobs": "IT Security",
    "Reed UK": "Business Analysis",
    "Indeed UK": "Data Analysis",
    "JobServe": "Business Intelligence",
}

def safe_cell(x: object) -> str:
    """Avoid spreadsheet formula execution when a CSV is opened in Excel."""
    if x is None:
        return ""
    value = str(x).replace("\x00", "").replace("\r", " ").replace("\n", " ").strip()
    if value and (value[0] in "=+@-" or value.lstrip()[0] in "=+@-"):
        return "'" + value
    return value

def generate(input_path: Path = INPUT, output_path: Path = OUTPUT) -> dict:
    doc = json.loads(input_path.read_text(encoding="utf-8"))
    sources = doc.get("sources")
    if (doc.get("schema") != "ba-offline-actor-observations/v1"
        or doc.get("publication_approved") is not False
        or doc.get("paid_actor_runs_started_by_audit") != 0
        or not isinstance(sources, list)
        or {x.get("name") for x in sources} != set(SOURCES)):
        raise ValueError("Not the audited, provenance-locked 161-record evidence")
    rows = []
    by_source = Counter()
    proposed = Counter()
    for group in sources:
        source = group["name"]
        if (group.get("status") != "SUCCEEDED"
            or len(group["records"]) != SOURCES[source]
            or not group.get("run_id") or not group.get("dataset_id")
            or not group.get("observed_at")):
            raise ValueError("Missing source provenance or different dataset count: " + source)
        for item in group["records"]:
            if not isinstance(item, dict):
                raise ValueError("Malformed source item")
            title = item.get("title") or item.get("jobTitle") or ""
            snippet = cleaned_excerpt(item)
            decision = classify_market_role(title, snippet)
            training = promotional_training_lead(title, snippet)
            original_url = link(item, source)
            if training:
                suggested = "Needs review: training / placement advert"
                priority = "High"
            elif not original_url:
                suggested = "Needs review: missing safe source URL"
                priority = "High"
            elif not decision["included"]:
                suggested = "Suggest exclude: outside 22 job families"
                priority = "Medium"
            elif decision.get("review_required"):
                suggested = "Needs review: ambiguous role family"
                priority = "High"
            else:
                suggested = "Suggest keep: title matches taxonomy"
                priority = "Normal"
            proposed[suggested] += 1
            by_source[source] += 1
            date = posted(item)
            if date:
                yyyy,mm,dd = date.split("-")
                date = dd + "/" + mm + "/" + yyyy
            row = {
                "Record #": len(rows) + 1,
                "Review decision (Keep / Exclude / Needs review)": "",
                "Reviewer notes": "",
                "Corrected job family (if needed)": "",
                "Review priority": priority,
                "Suggested review status": suggested,
                "Source": source,
                "Original job advert URL": original_url or "",
                "Job title": title,
                "Advertiser / agency": company(item),
                "Location": location(item),
                "Source posted date (UK)": date or "",
                "Employment type": employment(item),
                "Working arrangement": working(item),
                "Classifier role family": decision.get("role_family") or "",
                "Role category": decision.get("track") or "",
                "Classifier matched phrase": decision.get("matched_title") or "",
                "Classifier reason": decision.get("reason") or "",
                "Classification confidence note": (
                    "Ambiguous title: check source description"
                    if decision.get("review_required") else
                    "Automated title-only family match; employer opening not independently confirmed"
                    if decision.get("included") else
                    "Out-of-taxonomy title; reviewer may override"
                ),
                "Training / placement promotion flag": "YES" if training else "No",
                "Potential duplicate review": "Not checked across employer listings",
                "Sector (evidence-backed)": "Not specified",
                "Sector evidence status": "No independent advertiser-sector evidence in source snapshot",
                "Job description excerpt (truncated in evidence)": snippet or "",
                "Original run ID": group["run_id"],
                "Dataset ID": group["dataset_id"],
                "Observed at (UTC)": group["observed_at"],
                "Source query family": QUERY[source],
                "Original source records": SOURCES[source],
                "Source count exceeded requested 30": "YES" if SOURCES[source] > 30 else "No",
            }
            rows.append(row)
    if len(rows) != 161 or set(by_source) != set(SOURCES):
        raise ValueError("CSV must include exactly all 161 original records")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=COLUMNS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: safe_cell(row[col]) for col in COLUMNS})
    with output_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        final = list(reader)
    if len(final) != 161 or len(final[0]) != len(COLUMNS):
        raise ValueError("CSV integrity check failed")
    return {"records": len(rows), "source_counts": dict(by_source),
        "review_suggestions": dict(proposed), "columns": len(COLUMNS),
        "csv_bytes": output_path.stat().st_size,
        "no_actor_runs": True, "no_wordpress_changes": True}

if __name__ == "__main__":
    print(json.dumps(generate(), sort_keys=True))
