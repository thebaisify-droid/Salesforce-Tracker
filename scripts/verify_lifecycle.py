from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tracker.lifecycle import run_verification
from tracker.store import Store


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def main() -> int:
    p = argparse.ArgumentParser(description="Verify active vacancy lifecycle using conservative direct job-page evidence")
    p.add_argument("--database", default=os.environ.get("TRACKER_DATABASE_PATH", "data/salesforce_tracker.db"))
    p.add_argument("--report", required=True)
    p.add_argument("--metrics")
    p.add_argument("--min-age-days", type=int, default=14)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--confirmations", type=int, default=2)
    p.add_argument("--min-confirmation-hours", type=float, default=12.0)
    p.add_argument("--timeout-seconds", type=int, default=8)
    p.add_argument("--max-workers", type=int, default=6)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    with Store(args.database) as store:
        report = run_verification(
            store,
            min_age_days=max(0, args.min_age_days),
            limit=max(1, args.limit),
            confirmations=max(2, args.confirmations),
            min_confirmation_hours=max(0.0, args.min_confirmation_hours),
            timeout_seconds=max(1, args.timeout_seconds),
            max_workers=max(1, args.max_workers),
            dry_run=args.dry_run,
        )

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.metrics:
        metrics_path = Path(args.metrics)
        metrics = load_json(metrics_path)
        metrics["lifecycle"] = {
            "passed": report["passed"],
            "checked_at": report["checked_at"],
            "candidates_selected": report["candidates_selected"],
            "observations": report["observations"],
            "transitions": report["transitions"],
            "counts": report["lifecycle_counts"],
            "dry_run": report["dry_run"],
        }
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
