from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main() -> int:
    p = argparse.ArgumentParser(description="Show the dashboard-facing refresh status")
    p.add_argument("--state", default="state/dashboard_status.json")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    path = Path(args.state)
    if not path.exists():
        print("No refresh status exists yet.")
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    tz_name = data.get("timezone", "Europe/London")
    last = data.get("last_successful_refresh")
    attempt = data.get("latest_attempt", {})
    success = data.get("latest_success", {})
    if last:
        dt = datetime.fromisoformat(last.replace("Z", "+00:00")).astimezone(ZoneInfo(tz_name))
        last_display = dt.strftime("%d %b %Y, %H:%M %Z")
    else:
        last_display = "Never"

    print(f"Last successful refresh: {last_display}")
    print(f"Latest attempt: {attempt.get('status') or 'none'}")
    if attempt.get("reason"):
        print(f"Reason: {attempt['reason']}")
    print(f"Sources: {success.get('sources_succeeded')}/{success.get('sources_configured')}")
    print(
        "Changes: "
        f"+{success.get('inserted_rows') or 0} inserted, "
        f"{success.get('updated_rows') or 0} updated, "
        f"{success.get('rejected_rows') or 0} rejected"
    )
    print(f"Quality passed: {success.get('quality_passed')}")
    print(f"Master data: {success.get('master_data_version') or 'unknown'}")
    print(f"Role taxonomy: {success.get('role_taxonomy_version') or 'unknown'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
