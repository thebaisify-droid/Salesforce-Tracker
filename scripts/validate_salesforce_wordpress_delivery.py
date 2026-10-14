"""Offline preflight for future WordPress Salesforce snapshot delivery.

No networking, credentials, publication, or scraping. Fail closed on stale
snapshots and QA inconsistencies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def inspect(raw: bytes, now: datetime | None = None) -> dict:
    if not 64 <= len(raw) <= 400000:
        raise ValueError("Snapshot size outside safety bounds")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema") != "salesforce-hiring-dashboard/v1":
        raise ValueError("Unexpected snapshot schema")
    if not isinstance(data.get("pipeline"), dict) or data["pipeline"].get("quality_passed") is not True:
        raise ValueError("Quality evidence missing or failed")
    vacancies = data.get("vacancies")
    active = data.get("active_vacancies")
    if not isinstance(vacancies, list) or type(active) is not int or active < 0 or active > len(vacancies):
        raise ValueError("Invalid master counts")
    refresh = data.get("refresh")
    if not isinstance(refresh, dict) or refresh.get("status") != "success":
        raise ValueError("Refresh not successful")
    stamp = refresh.get("finished_at")
    if not isinstance(stamp, str):
        raise ValueError("Missing timestamp")
    finished = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if finished.tzinfo is None:
        raise ValueError("Timezone is required")
    asof = now or datetime.now(timezone.utc)
    age = (asof - finished).total_seconds()
    if not -900 <= age <= 36 * 3600:
        raise ValueError("Unusable stale or future-dated snapshot")
    return {
        "schema": "salesforce-wordpress-transport-preflight/v1",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "vacancy_rows": len(vacancies),
        "active_vacancies": active,
        "refresh_finished_at": stamp,
        "locally_validated": True,
        "wordpress_delivery_authorised": False,
        "publication_performed": False,
        "apify_actors_started": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="dashboard/live-data.json")
    args = p.parse_args()
    try:
        report = inspect(Path(args.input).read_bytes())
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"locally_validated": False, "reason": str(error),
                          "publication_performed": False}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
