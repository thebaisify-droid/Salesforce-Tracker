"""Offline labelled-fixture validation for candidate role taxonomy; no network calls."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from tracker.business_product_delivery_security import classify_market_role, taxonomy

def evaluate(fixtures: list[dict[str, Any]], *, minimum_precision: float = 0.90,
             minimum_recall: float = 0.90, minimum_family_accuracy: float = 0.90) -> dict[str, Any]:
    if not fixtures:
        raise ValueError("labelled validation set cannot be empty")
    allowed = {f["name"] for f in taxonomy()["role_families"]}
    confusion = Counter()
    errors = []
    for i, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict) or not isinstance(fixture.get("expected_included"), bool):
            raise ValueError(f"fixture {i} has no boolean expected_included")
        expected_family = fixture.get("expected_family")
        if fixture["expected_included"] and expected_family not in allowed:
            raise ValueError(f"fixture {i} has an invalid expected_family")
        result = classify_market_role(fixture.get("title"), fixture.get("description"))
        actual, expected = result["included"], fixture["expected_included"]
        confusion["tp" if actual and expected else "fp" if actual else "fn" if expected else "tn"] += 1
        if actual and expected:
            confusion["family_total"] += 1
            if result["role_family"] == expected_family:
                confusion["family_correct"] += 1
        if actual != expected or (actual and expected and result["role_family"] != expected_family):
            errors.append({"index": i, "title": fixture.get("title"),
                           "expected_included": expected, "expected_family": expected_family,
                           "actual_included": actual, "actual_family": result.get("role_family"),
                           "reason": result.get("reason")})
    tp, fp, fn = (confusion[k] for k in ("tp", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    accuracy = confusion["family_correct"] / confusion["family_total"] if confusion["family_total"] else 0.0
    passed = (precision >= minimum_precision and recall >= minimum_recall
              and accuracy >= minimum_family_accuracy)
    return {"schema": "candidate-classification-assurance/v1",
            "sample_size": len(fixtures), "counts": dict(confusion),
            "precision": round(precision, 4), "recall": round(recall, 4),
            "family_accuracy": round(accuracy, 4), "thresholds": {
                "precision": minimum_precision, "recall": minimum_recall,
                "family_accuracy": minimum_family_accuracy},
            "passed": passed, "errors": errors,
            "evidence_level": "labelled_fixtures_only",
            "real_world_accuracy_validated": False,
            "publication_approved": False}

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate candidate roles against offline labelled samples")
    parser.add_argument("--input", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    fixtures = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = evaluate(fixtures)
    dest = Path(args.report)
    if dest.resolve() in {Path("dashboard/live-data.json").resolve(), Path("dashboard/data.json").resolve()}:
        parser.error("cannot overwrite existing live Salesforce dashboard")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "errors"}, sort_keys=True))
    return 0 if report["passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
