"""Prepare an auditable offline review queue from real job-board exports.

No network requests or automatically assigned ground-truth labels.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from scripts.build_candidate_market_dashboard import _clean_url, _field, ALLOWED, URL_KEYS, SOURCE_KEYS
from tracker.business_product_delivery_security import classify_raw

def prepare(records, max_per_stratum=20):
    if not isinstance(records, list) or max_per_stratum < 1:
        raise ValueError("records must be a list and max_per_stratum positive")
    strata = defaultdict(list)
    seen = set()
    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            continue
        title = _field(raw, ALLOWED)
        url = _clean_url(_field(raw, URL_KEYS))
        if not title or not url:
            continue
        if url.lower() in seen:
            continue
        seen.add(url.lower())
        decision = classify_raw(raw)
        description = _field(raw, ("description", "descriptionText", "job_description", "jobDescription", "summary", "snippet", "body")) or ""
        source = _field(raw, SOURCE_KEYS) or "unattributed"
        stratum = decision.get("track") if decision["included"] else "EXCLUDED_OR_AMBIGUOUS"
        key = hashlib.sha256(url.lower().encode("utf-8")).hexdigest()[:16]
        strata[(source, stratum)].append({
            "sample_id": key, "source": source, "job_url": url,
            "title": title, "description_excerpt": description[:1200],
            "predicted_included": decision["included"],
            "predicted_track": decision.get("track") or "",
            "predicted_family": decision.get("role_family") or "",
            "predicted_review_required": decision["review_required"],
            "expected_included": "", "expected_family": "",
            "reviewer": "", "reviewed_at": "", "evidence_notes": ""
        })
    selected = []
    for stratum, items in sorted(strata.items()):
        selected.extend(sorted(items, key=lambda r: r["sample_id"])[:max_per_stratum])
    return selected

FIELDS = ("sample_id", "source", "job_url", "title", "description_excerpt",
          "predicted_included", "predicted_track", "predicted_family",
          "predicted_review_required", "expected_included", "expected_family",
          "reviewer", "reviewed_at", "evidence_notes")

def main():
    parser = argparse.ArgumentParser(description="Create an unlabelled real-vacancy review sample offline")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-per-stratum", type=int, default=20)
    args = parser.parse_args()
    source, output = Path(args.input).resolve(), Path(args.output).resolve()
    if source == output or output in {Path("dashboard/live-data.json").resolve(), Path("dashboard/data.json").resolve()}:
        parser.error("Cannot overwrite input or existing Salesforce dashboard")
    raw = json.loads(source.read_text(encoding="utf-8"))
    review = prepare(raw, args.max_per_stratum)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(review)
    print(json.dumps({"review_rows": len(review), "output": str(output),
                      "ground_truth_labels_supplied": False, "real_world_validated": False}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
