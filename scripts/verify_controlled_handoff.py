"""Proof that the delivered snapshot comes from *this* successful scheduled run.

Read only. Do not infer freshness from wall clock alone: restored old artifacts
can remain within the 36h WordPress transport window.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts.validate_salesforce_wordpress_delivery import inspect


def validate_handoff(snapshot, attempt, status):
    if not isinstance(attempt, dict) or not isinstance(status, dict):
        raise ValueError("Missing run status")
    run_id = status.get("run_id")
    if not isinstance(run_id, str) or not run_id or attempt.get("run_id") != run_id:
        raise ValueError("Latest attempt is not the successful run")
    if attempt.get("status") != "success" or status.get("status") != "success":
        raise ValueError("Current run skipped or failed")
    if (attempt.get("summary") or {}).get("quality_passed") is not True:
        raise ValueError("Quality did not pass this attempt")
    if snapshot.get("run_id") != run_id:
        raise ValueError("Snapshot run ID differs from current successful run")
    if snapshot.get("refresh", {}).get("status") != "success":
        raise ValueError("Snapshot refresh status is not success")
    return {"ready_for_single_delivery": True, "run_id": run_id}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="dashboard/live-data.json")
    p.add_argument("--status", default="state/latest_refresh.json")
    p.add_argument("--attempt", default="state/latest_attempt.json")
    args = p.parse_args()
    raw = Path(args.input).read_bytes()
    inspect(raw)
    report = validate_handoff(json.loads(raw), json.loads(Path(args.attempt).read_text()),
                              json.loads(Path(args.status).read_text()))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
