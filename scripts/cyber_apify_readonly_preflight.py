"""Read-only Apify account + per-Actor minimum run-charge preflight. No Actor starts."""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

ACTORS = {
    "Indeed UK": ("BkcKc9frZp43LeRM7", Decimal("0.25")),
    "JobServe": ("iEeTOwSjZDvAshw7Y", Decimal("0.25")),
}
SAFE_ENDPOINTS = {"users/me/limits", "users/me/usage/monthly"} | {
    "acts/" + actor_id for actor_id, _ in ACTORS.values()
}
ACCOUNT_LIMIT = Decimal("19")
RESERVE = Decimal("8")
PROPOSED_TOTAL = Decimal("0.50")

def get_only(endpoint, token):
    if endpoint not in SAFE_ENDPOINTS:
        raise ValueError("Unsupported read-only endpoint")
    req = Request("https://api.apify.com/v2/" + endpoint,
                  headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
                  method="GET")
    with urlopen(req, timeout=20) as response:
        return json.load(response)

def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError("Missing numeric billing field")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as error:
        raise ValueError("Invalid numeric billing field") from error
    if not result.is_finite() or result < 0:
        raise ValueError("Invalid numeric billing field")
    return result

def actor_minimum(data):
    candidates = [x for x in data.get("pricingInfos", [])
                  if isinstance(x, dict) and x.get("pricingModel") == "PAY_PER_EVENT"]
    if not candidates:
        return None, False
    latest = max(candidates, key=lambda x: str(x.get("startedAt") or ""))
    if "minimalMaxTotalChargeUsd" not in latest:
        return None, False
    value = latest["minimalMaxTotalChargeUsd"]
    if value is None:
        return Decimal(0), True
    return number(value), True

def assess(limits_record, usage_record, actor_records):
    account = limits_record["data"]
    maximum = number(account["limits"]["maxMonthlyUsageUsd"])
    used = number(account["current"]["monthlyUsageUsd"])
    monthly_total = number(usage_record["data"]["totalUsageCreditsUsdAfterVolumeDiscount"])
    issues = []
    if maximum != ACCOUNT_LIMIT:
        issues.append("monthly_limit_not_19")
    if used + RESERVE + PROPOSED_TOTAL > maximum:
        issues.append("protected_salesforce_reserve_insufficient")
    if abs(used - monthly_total) > Decimal("0.20"):
        issues.append("monthly_usage_reports_disagree")
    checks = []
    for name, (actor_id, cap) in ACTORS.items():
        data = actor_records[name]["data"]
        if data.get("id") != actor_id:
            issues.append("unexpected_actor_identity:" + name)
        floor, known = actor_minimum(data)
        if not known or floor > cap:
            issues.append("minimum_run_charge_not_verified_under_cap:" + name)
        checks.append({"source": name, "run_cap_usd": float(cap),
                       "minimum_run_charge_usd": float(floor) if known else None,
                       "minimum_confirmed_compatible": bool(known and floor <= cap)})
    return {
        "schema": "candidate-cyber-apify-readonly-preflight/v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "account_limit_usd": float(maximum),
        "monthly_usage_usd": float(used),
        "usage_endpoint_total_usd": float(monthly_total),
        "protected_salesforce_reserve_usd": float(RESERVE),
        "proposed_one_time_cap_usd": float(PROPOSED_TOTAL),
        "unreserved_headroom_usd": float(maximum - used - RESERVE),
        "actors": checks, "read_only_checks_pass": not issues,
        "blocked_reasons": issues,
        "paid_runs_started": 0, "paid_execution_authorised": False,
        "note": "GET-only check; no guarantee of keyword yield or charged-event behavior."
    }

def main():
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise SystemExit("Missing APIFY_TOKEN GitHub secret (no runs started)")
    limits = get_only("users/me/limits", token)
    usage = get_only("users/me/usage/monthly", token)
    actors = {name: get_only("acts/" + actor_id, token)
              for name, (actor_id, _) in ACTORS.items()}
    report = assess(limits, usage, actors)
    Path("candidate-cyber-readonly-preflight.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if not report["read_only_checks_pass"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
