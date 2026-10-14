"""One-shot, read-only validation of previously SUCCEEDED Apify datasets.

No actor starts, GitHub workflow orchestration, scheduled refreshes, or publication.
Uses the repository's actual candidate classifier and dashboard builder. Only
aggregated metrics leave a temporary private staging directory.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.import_candidate_apify_runs import acquire, SOURCE_SLUGS
from scripts.build_candidate_market_dashboard import build_snapshot
from scripts.candidate_refresh_assurance import assess_refresh_quality

def posting_day(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        pass
    for fmt in ("%A, %d %B %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def validate_completed_runs(manifest: dict, *, token: str, getter=None, today: date | None = None) -> dict:
    if manifest.get("publication_approved") is not False or manifest.get("actor_runs_to_launch") != 0:
        raise ValueError("Only explicitly disabled, historical-review manifests may be validated")
    from scripts.import_candidate_apify_runs import get_json
    getter = getter or get_json
    today = today or datetime.now(timezone.utc).date()
    with tempfile.TemporaryDirectory(prefix="candidate-apify-readonly-") as folder:
        output = Path(folder) / "review"
        ingestion = acquire(manifest, output, token, getter)
        records = []
        statuses = []
        for item in ingestion["results"]:
            filename = SOURCE_SLUGS[item["source"]] + "-" + item["run_id"] + "-candidate.json"
            rows = json.loads((output / filename).read_text(encoding="utf-8"))
            records.extend(rows)
            days = [posting_day(row.get("posted_at")) for row in rows]
            dated = [day for day in days if day is not None]
            statuses.append({
                "source": item["source"], "run_id": item["run_id"],
                "raw_rows": item["dataset_rows"], "job_rows": len(rows),
                "expiry_events_review_only": item["expiry_events"],
                "invalid_rows": item["invalid_rows"],
                "unknown_posting_date": len(rows) - len(dated),
                "older_than_7_days": sum((today-day).days > 7 for day in dated),
                "future_posting_dates": sum(day > today for day in dated),
                "oldest_posting_date": min(dated).isoformat() if dated else None,
                "newest_posting_date": max(dated).isoformat() if dated else None,
            })
        # This calls the production Python candidate classifier, not a title heuristic.
        snapshot = build_snapshot(records, datetime.now(timezone.utc).isoformat())
        refresh_quality = assess_refresh_quality(records, as_of=today)
        families = [{"family": i["label"], "count": i["value"]} for i in snapshot["by_role_family"] if i["value"]]
        return {
            "schema": "candidate-apify-live-python-validation/v1",
            "mode": "HISTORICAL_REVIEW_ONLY",
            "run_count": len(statuses),
            "source_checks": statuses,
            "raw_rows": sum(i["raw_rows"] for i in statuses),
            "normalized_job_rows": len(records),
            "expiry_events_review_only": sum(i["expiry_events_review_only"] for i in statuses),
            "unique_classified_vacancies": snapshot["total_vacancies"],
            "role_family_counts": families,
            "track_counts": snapshot["by_track"],
            "classification_review_required": snapshot["review_required"],
            "rejections": snapshot["rejections"],
            "refresh_quality": refresh_quality,
            "exact_url_duplicates": snapshot["rejections"].get("duplicate", 0),
            "real_world_accuracy_validated": False,
            "publication_approved": False,
            "acquisition_enabled": False,
            "actor_runs_started": 0,
            "note": "Historical read-only validation. URL deduplication is not cross-board semantic deduplication. Posting dates do not prove currently open vacancies."
        }

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate five previously completed Apify runs, read-only")
    parser.add_argument("--manifest", default="config/candidate_apify_completed_runs_2026-10-10.example.json")
    args = parser.parse_args()
    import os
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        parser.error("APIFY_TOKEN is required; do not print or commit it")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(validate_completed_runs(manifest, token=token), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
