"""Read-only metadata inspection of an existing Apify run."""
import json
import os
from urllib.request import Request, urlopen

RUN_ID = "vYVznbV67JxKMBqbo"

def summarise(payload):
    data = payload.get("data", {})
    if data.get("id") != RUN_ID:
        raise ValueError("Unexpected run identifier")
    return {
        "run_id": data["id"],
        "status": data.get("status"),
        "started_at": data.get("startedAt"),
        "finished_at": data.get("finishedAt"),
        "usage_total_usd": data.get("usageTotalUsd"),
        "status_message_available": bool(data.get("statusMessage")),
        "exit_code": data.get("exitCode"),
        "run_options": {"maxTotalChargeUsd": (data.get("options") or {}).get("maxTotalChargeUsd")},
        "read_only": True,
        "cause_confirmed": False,
    }

def main():
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ValueError("APIFY_TOKEN missing")
    request = Request(
        "https://api.apify.com/v2/actor-runs/" + RUN_ID,
        headers={"Authorization": "Bearer " + token},
        method="GET",
    )
    with urlopen(request, timeout=40) as response:
        report = summarise(json.load(response))
    with open("cv-library-run-metadata.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("Read-only metadata obtained; status:", report["status"])

if __name__ == "__main__":
    main()
