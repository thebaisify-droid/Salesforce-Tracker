"""Evaluate independently labelled, real-source vacancy review CSV offline."""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from scripts.validate_candidate_market import evaluate

TRUE = {"true", "1", "yes"}
FALSE = {"false", "0", "no"}

def load_reviewed_csv(path):
    rows = []
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"sample_id", "source", "job_url", "title", "description_excerpt",
                    "expected_included", "expected_family", "reviewer", "reviewed_at"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("review CSV missing required evidence columns")
        ids = set()
        for number, row in enumerate(reader, start=2):
            sid = (row.get("sample_id") or "").strip()
            label = (row.get("expected_included") or "").strip().lower()
            reviewer = (row.get("reviewer") or "").strip()
            reviewed_at = (row.get("reviewed_at") or "").strip()
            if not sid or sid in ids or label not in TRUE | FALSE or not reviewer or not reviewed_at:
                raise ValueError(f"row {number}: missing or duplicate evidence, reviewer, date, or valid label")
            ids.add(sid)
            included = label in TRUE
            family = (row.get("expected_family") or "").strip() or None
            if included != bool(family):
                raise ValueError(f"row {number}: family required exactly when included")
            if not (row.get("job_url") or "").startswith(("https://", "http://")):
                raise ValueError(f"row {number}: source job URL missing")
            rows.append({"title": row["title"], "description": row.get("description_excerpt") or "",
                         "expected_included": included, "expected_family": family,
                         "source": row["source"], "sample_id": sid})
    return rows

def evaluate_reviewed(rows, *, minimum_samples=100):
    if not rows:
        raise ValueError("No independently reviewed records")
    report = evaluate(rows)
    source_counts = Counter(r["source"] for r in rows)
    report["evidence_level"] = "human_labelled_source_records"
    report["real_world_accuracy_validated"] = bool(report["passed"] and len(rows) >= minimum_samples)
    report["publication_approved"] = False
    report["minimum_samples"] = minimum_samples
    report["sample_size_gate_passed"] = len(rows) >= minimum_samples
    report["sources"] = dict(sorted(source_counts.items()))
    report["passed"] = bool(report["passed"] and report["sample_size_gate_passed"])
    report["sampling_note"] = ("Source-stratified review samples do not establish unbiased "
                              "market-level precision, recall or total vacancy coverage.")
    return report

def main():
    p = argparse.ArgumentParser(description="Offline evaluation of independently reviewed job adverts")
    p.add_argument("--input", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--minimum-samples", type=int, default=100)
    args = p.parse_args()
    if args.minimum_samples < 1:
        p.error("minimum-samples must be positive")
    target = Path(args.report)
    if target.resolve() in {Path("dashboard/live-data.json").resolve(), Path("dashboard/data.json").resolve()}:
        p.error("cannot overwrite Salesforce live dashboard")
    report = evaluate_reviewed(load_reviewed_csv(args.input), minimum_samples=args.minimum_samples)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "sample_size": report["sample_size"],
                      "precision": report["precision"], "recall": report["recall"],
                      "family_accuracy": report["family_accuracy"],
                      "publication_approved": False}))
    return 0 if report["passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
