from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tracker.dashboard import merge_with_baseline
from tracker.store import SOURCE_LABELS, Store


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def source_pipeline_summary(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    raw = metrics.get("source_rows") or {}
    relevant = metrics.get("source_relevant_rows") or {}
    irrelevant = metrics.get("source_irrelevant_rows") or {}
    keys = sorted(set(raw) | set(relevant) | set(irrelevant))
    return [
        {
            "key": key,
            "label": SOURCE_LABELS.get(key, key),
            "raw": int(raw.get(key, 0) or 0),
            "relevant": int(relevant.get(key, 0) or 0),
            "irrelevant": int(irrelevant.get(key, 0) or 0),
        }
        for key in keys
    ]


def main() -> int:
    p = argparse.ArgumentParser(description="Publish dashboard-safe Salesforce tracker data")
    p.add_argument("--run-id", required=True)
    p.add_argument("--database", default=os.environ.get("TRACKER_DATABASE_PATH", "data/salesforce_tracker.db"))
    p.add_argument("--output", default="dashboard/data.json")
    p.add_argument("--public-output", default="dashboard/live-data.json")
    p.add_argument("--baseline", default="config/baseline_2026-10-06.json")
    args = p.parse_args()

    with Store(args.database) as store:
        snapshot = store.dashboard_snapshot()

    run_dir_value = os.environ.get("PIPELINE_RUN_DIR")
    run_dir = Path(run_dir_value) if run_dir_value else None
    metrics = load_json(run_dir / "metrics.json") if run_dir else {}
    quality = load_json(run_dir / "quality_report.json") if run_dir else {}

    latest_state = load_json(Path("state/latest_success.json"))
    if not metrics and isinstance(latest_state.get("metrics"), dict):
        metrics = latest_state["metrics"]
    if not quality:
        state_quality = (latest_state.get("quality") or {}).get("report")
        if isinstance(state_quality, dict):
            quality = state_quality

    baseline = load_json(Path(args.baseline))
    snapshot = merge_with_baseline(snapshot, baseline)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    latest = snapshot.get("latest_run") or {}

    snapshot.update({
        "schema": "salesforce-hiring-dashboard/v1",
        "run_id": args.run_id,
        "generated_at": generated_at,
        "refresh": {
            "status": latest.get("status"),
            "started_at": latest.get("started_at"),
            "finished_at": latest.get("finished_at"),
            "inserted": latest.get("inserted_rows", 0),
            "updated": latest.get("updated_rows", 0),
            "unchanged": latest.get("unchanged_rows", 0),
            "rejected": latest.get("rejected_rows", 0),
            "master_data_version": latest.get("master_data_version") or metrics.get("master_data_version"),
            "role_taxonomy_version": latest.get("role_taxonomy_version") or metrics.get("role_taxonomy_version"),
        },
        "pipeline": {
            "quality_passed": quality.get("passed"),
            "raw_records": sum(int(v or 0) for v in (metrics.get("source_rows") or {}).values()),
            "relevant_records": sum(int(v or 0) for v in (metrics.get("source_relevant_rows") or {}).values()),
            "irrelevant_records": int(metrics.get("irrelevant_rows", 0) or 0),
            "rejected_records": int(metrics.get("rejected_rows", 0) or 0),
            "sources": source_pipeline_summary(metrics),
            "lifecycle_assurance": metrics.get("lifecycle") or {},
        },
    })

    write_json(Path(args.output), snapshot)
    write_json(Path(args.public_output), snapshot)
    print(json.dumps(snapshot, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
