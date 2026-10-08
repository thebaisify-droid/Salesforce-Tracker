"""Read-only Apify account limit/usage preflight. Never alters limits or runs Actors."""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen

API="https://api.apify.com/v2/users/me/limits"

def summarise(payload, *, budget=19.0, pilot=0.50):
    data=payload.get("data", {})
    limit=data.get("limits", {}).get("maxMonthlyUsageUsd")
    usage=data.get("current", {}).get("monthlyUsageUsd")
    if isinstance(limit,bool) or not isinstance(limit,(float,int)):
        raise ValueError("Account monthly spending limit absent/invalid")
    if isinstance(usage,bool) or not isinstance(usage,(float,int)) or usage<0:
        raise ValueError("Account current monthly usage absent/invalid")
    remaining=max(0, round(limit-usage, 2))
    safe=limit<=budget and remaining>=pilot
    return {
        "schema":"apify-budget-readonly-preflight/v1",
        "configured_account_limit_usd":round(limit,2),
        "current_monthly_usage_usd":round(usage,2),
        "remaining_to_account_limit_usd":remaining,
        "shared_budget_ceiling_usd":budget,
        "proposed_pilot_usd":pilot,
        "account_headroom_sufficient":safe,
        "pilot_authorised":False,
        "actor_runs_started":0,
        "limits_updated":False,
        "caveat":"Usage can change concurrently. Account headroom is not a reserved pilot allocation."
    }

def inspect(token):
    if not token: raise ValueError("APIFY_TOKEN is missing")
    request=Request(API, method="GET", headers={
        "Authorization":"Bearer "+token,"Accept":"application/json"})
    with urlopen(request,timeout=40) as response:
        payload=json.load(response)
    return summarise(payload)

def main():
    result=inspect(os.environ.get("APIFY_TOKEN",""))
    # Account usage numbers only; never output bearer token or raw account payload.
    print(json.dumps(result,sort_keys=True))
    return 0 if result["account_headroom_sufficient"] else 2

if __name__=="__main__":
    raise SystemExit(main())
