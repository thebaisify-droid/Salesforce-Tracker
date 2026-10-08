"""Read local, previously exported job-board datasets without provider requests.

Normalises common column aliases into candidate-review inputs. Does not
claim an export is genuine; source provenance must be verified separately.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from scripts.build_candidate_market_dashboard import _field, ALLOWED, URL_KEYS, COMPANY_KEYS, LOCATION_KEYS, DATE_KEYS

EXTENDED_COMPANY_KEYS = COMPANY_KEYS + ("companyName", "employerName", "recruiter", "organisation")
EXTENDED_URL_KEYS = URL_KEYS + ("jobLink", "applyUrl", "job_url_original")
EXTENDED_DATE_KEYS = DATE_KEYS + ("date_posted", "created", "publicationDate")

DESCRIPTION_KEYS = ("description", "descriptionText", "job_description", "jobDescription", "summary", "snippet", "body")

def load_export(path: str | Path, source: str) -> list[dict[str, Any]]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            for key in ("items", "jobs", "records", "results", "data"):
                if isinstance(payload.get(key), list):
                    payload = payload[key]
                    break
        if not isinstance(payload, list):
            raise ValueError("JSON export must contain an array of job records")
    elif path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            payload = list(csv.DictReader(f))
    else:
        raise ValueError("Only .json or .csv exports are supported")
    records = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        row = {
            "title": _field(raw, ALLOWED),
            "url": _field(raw, EXTENDED_URL_KEYS),
            "description": _field(raw, DESCRIPTION_KEYS),
            "company": _field(raw, EXTENDED_COMPANY_KEYS),
            "location": _field(raw, LOCATION_KEYS),
            "posted_at": _field(raw, EXTENDED_DATE_KEYS),
            "source": source,
        }
        if row["title"] and row["url"]:
            records.append(row)
    return records

def main() -> int:
    p = argparse.ArgumentParser(description="Normalise existing UK job-board exports offline")
    p.add_argument("--input", required=True)
    p.add_argument("--source", required=True, choices=("CV-Library", "Totaljobs", "Reed", "Indeed UK", "JobServe"))
    p.add_argument("--output", required=True)
    args = p.parse_args()
    input_path, output_path = Path(args.input).resolve(), Path(args.output).resolve()
    if input_path == output_path or output_path in {
        Path("dashboard/live-data.json").resolve(), Path("dashboard/data.json").resolve()
    }:
        p.error("input and output must differ; live Salesforce files are protected")
    records = load_export(input_path, args.source)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "read_only_source_export", "source": args.source,
                      "records": len(records), "provider_requests": 0,
                      "authenticity_verified": False}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
