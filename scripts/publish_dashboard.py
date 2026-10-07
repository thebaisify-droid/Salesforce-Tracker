from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tracker.store import Store


def main() -> int:
    p = argparse.ArgumentParser(description="Publish dashboard-ready Salesforce tracker aggregates")
    p.add_argument("--run-id", required=True)
    p.add_argument("--database", default=os.environ.get("TRACKER_DATABASE_PATH", "data/salesforce_tracker.db"))
    p.add_argument("--output", default="dashboard/data.json")
    args = p.parse_args()

    with Store(args.database) as store:
        snapshot = store.dashboard_snapshot()
    snapshot["run_id"] = args.run_id
    snapshot["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(output)
    print(json.dumps(snapshot, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
