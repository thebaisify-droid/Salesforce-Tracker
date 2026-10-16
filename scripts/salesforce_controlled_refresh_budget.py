"""Fail-closed account preflight for controlled Salesforce refresh.

Read-only: this script cannot launch Actors or publish data.
"""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen

LIMIT_USD = 25.0
LEGACY_LIMIT_USD = 19.0
PROTECTED_RESERVE_USD = 8.0
SOURCE_CAPS_USD = (0.15, 0.15, 0.15, 0.20, 0.25)
MAX_RUN_USD = round(sum(SOURCE_CAPS_USD), 2)
API = "https://api.apify.com/v2/users/me/limits"


def check_account(payload):
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("Apify billing data absent")
    maximum = (data.get("limits") or {}).get("maxMonthlyUsageUsd")
    usage = (data.get("current") or {}).get("monthlyUsageUsd")
    if type(maximum) not in (float, int) or type(usage) not in (float, int):
        raise ValueError("Apify account limit/usage absent")
    if all(abs(maximum - cap) > 0.00001 for cap in (LEGACY_LIMIT_USD, LIMIT_USD)) or usage < 0 or usage > maximum:
        raise ValueError("Unexpected account limit or usage")
    remaining = round(maximum - usage, 4)
    if remaining + 0.000001 < PROTECTED_RESERVE_USD + MAX_RUN_USD:
        raise ValueError("Insufficient balance after $8 Salesforce reserve and five-source worst-case cap")
    return {"schema": "salesforce-controlled-refresh-budget/v1",
            "account_limit_usd": maximum, "account_usage_usd": usage,
            "protected_reserve_usd": PROTECTED_RESERVE_USD,
            "five_source_worst_case_usd": MAX_RUN_USD,
            "headroom_after_reserve_usd": round(remaining-PROTECTED_RESERVE_USD, 4),
            "actors_started": 0, "automatic_publication": False}


def main():
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        raise SystemExit("Missing APIFY_TOKEN; fail closed")
    request = Request(API, method="GET", headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        result = check_account(json.load(response))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
