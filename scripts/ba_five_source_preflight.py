"""Five-source Business Analysis actor-input and budget preflight (zero paid calls).

No Actor-launch endpoints or scheduling. --account makes one authenticated GET
to Apify's account usage endpoint; every other operation is offline.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from scripts.validate_ba_five_source_contract import EXPECTED, validate_config

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "business-analysis-tracker" / "config" / "actor_search_plan.json"
CONTRACT = ROOT / "business-analysis-tracker" / "config" / "five_source_refresh.json"
ACCOUNT_URL = "https://api.apify.com/v2/users/me/limits"
SLOT = ("CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe")
ACTORS = {
    "CV-Library": ("blackfalcondata/cv-library-scraper", "maxResults", "query"),
    "Totaljobs": ("abotapi/totaljobs-com-scraper", "maxListings", "keywords"),
    "Reed UK": ("wildorigins/uk-jobs-reed", "maxResults", "keywords"),
    "Indeed UK": ("wildorigins/indeed-jobs", "maxResults", "query"),
    "JobServe": ("solidcode/jobserve-scraper", "maxResults", "keywords"),
}
KEYS = {
    "CV-Library": {"query", "country", "maxResults", "maxPages", "postedWithinDays",
                   "sortBy", "includeDetails", "incrementalMode", "emitExpired"},
    "Totaljobs": {"mode", "keywords", "maxListings", "maxPages", "postedWithin",
                  "sortBy", "fetchDetails", "incrementalMode"},
    "Reed UK": {"keywords", "maxResults", "datePosted", "fetchDetails"},
    "Indeed UK": {"query", "country", "maxResults"},
    "JobServe": {"keywords", "country", "maxResults",
                 "includeDescription", "onlyUniqueJobs"},
}

def validate_plan(plan: dict, contract: dict) -> dict:
    problems = list(validate_config(contract)["issues"])
    p = plan.get("source_profiles", [])
    if len(p) != 5 or [row.get("name") for row in p if isinstance(row, dict)] != list(SLOT):
        problems.append("FIVE_ACTORS_NOT_IN_EXACT_ORDER")
    for row in p:
        if not isinstance(row, dict):
            problems.append("MALFORMED_SOURCE")
            continue
        name, actor, args = row.get("name"), row.get("actor"), row.get("input")
        if name not in ACTORS or not isinstance(args, dict):
            problems.append("UNKNOWN_SOURCE_OR_PAYLOAD")
            continue
        expected_actor, cap_key, keyword_key = ACTORS[name]
        if actor != expected_actor:
            problems.append(name + ":WRONG_ACTOR")
        if set(args) - KEYS[name]:
            problems.append(name + ":UNINSPECTED_INPUT_FIELDS")
        limit = args.get(cap_key)
        if type(limit) is not int or not 1 <= limit <= 10:
            problems.append(name + ":RESULT_CAP_NOT_1_TO_10")
        terms = args.get(keyword_key)
        if terms not in ("business analyst", ["business analyst"]):
            problems.append(name + ":NOT_BA_SEARCH")
        if args.get("maxPages", 1) != 1:
            problems.append(name + ":PAGES_EXCEED_PILOT")
        if args.get("incrementalMode", False) is not False or args.get("emitExpired", False) is not False:
            problems.append(name + ":SHARED_OR_EXPIRY_STATE")
        if name == "Totaljobs" and args.get("mode") != "search":
            problems.append("TOTALJOBS_REQUIRES_SEARCH_MODE")
        if name == "Indeed UK" and args.get("country") != "uk":
            problems.append("INDEED_NOT_UK")
        if name == "JobServe" and args.get("country") != "gb":
            problems.append("JOBSERVE_NOT_GB")
        if name == "CV-Library" and args.get("country") != "GB":
            problems.append("CVLIBRARY_NOT_GB")
    budget = plan.get("budget") or {}
    if budget.get("account_limit_usd") != 19 or budget.get("salesforce_reserve_usd") != 8:
        problems.append("LIMIT_OR_SALESFORCE_RESERVE_MISMATCH")
    if (plan.get("execution_enabled") is not False
            or plan.get("apify_actions", {}).get("actor_runs_to_launch") != 0
            or plan.get("apify_actions", {}).get("publish_on_success") is not False
            or budget.get("approved") is not False
            or budget.get("max_total_charge_usd") is not None
            or budget.get("per_source_max_charge_usd") != {}):
        problems.append("EXECUTION_MUST_REMAIN_BLOCKED")
    if set(ACTORS) != EXPECTED:
        problems.append("FIVE_SOURCE_CONTRACT_MISMATCH")
    return {
        "valid": not problems,
        "problems": problems,
        "actors": list(SLOT),
        "advertisements_requested_maximum": sum(
            row.get("input", {}).get(ACTORS[row["name"]][1], 0)
            for row in p if isinstance(row, dict) and row.get("name") in ACTORS
            and isinstance(row.get("input"), dict)
            and type(row["input"].get(ACTORS[row["name"]][1])) is int),
        "actor_runs_started": 0,
        "paid_acquisition_enabled": False,
        "publication_enabled": False,
    }


def check_account(limits_payload: dict, *, proposed_cap_usd: float = 0.0) -> dict:
    data = limits_payload.get("data") or {}
    limit = (data.get("limits") or {}).get("maxMonthlyUsageUsd")
    used = (data.get("current") or {}).get("monthlyUsageUsd")
    if type(limit) not in (int, float) or type(used) not in (int, float):
        raise ValueError("Apify account usage or configured limit unavailable")
    if abs(limit - 19) > 0.000001 or used < 0 or used > limit:
        raise ValueError("Apify account limit must equal $19, usage must be valid")
    if type(proposed_cap_usd) not in (int, float) or not 0 <= proposed_cap_usd <= 11:
        raise ValueError("Proposed cap is invalid")
    remaining = round(limit-used, 4)
    return {
        "account_limit_usd": limit,
        "account_used_usd": used,
        "account_remaining_usd": remaining,
        "salesforce_reserved_usd": 8,
        "remaining_after_salesforce_reserve_usd": round(max(0, remaining-8), 4),
        "sufficient_for_proposed_cap": remaining >= 8 + proposed_cap_usd,
        "actor_runs_started": 0,
        "usage_read_only": True,
    }


def read_account(token: str) -> dict:
    if not token:
        raise ValueError("Missing APIFY_TOKEN; cannot establish current billing headroom")
    request = Request(ACCOUNT_URL, method="GET",
                      headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=25) as response:
        return json.load(response)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, default=PLAN)
    ap.add_argument("--contract", type=Path, default=CONTRACT)
    ap.add_argument("--account", action="store_true", help="One read-only Apify account limit GET")
    args = ap.parse_args()
    report = validate_plan(
        json.loads(args.plan.read_text(encoding="utf-8")),
        json.loads(args.contract.read_text(encoding="utf-8")))
    if not report["valid"]:
        print(json.dumps(report, sort_keys=True))
        raise SystemExit(2)
    if args.account:
        report["account_usage"] = check_account(read_account(os.environ.get("APIFY_TOKEN", "")))
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
