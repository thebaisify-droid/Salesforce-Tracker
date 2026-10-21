"""Read-only Phase 4 safety and release readiness for Salesforce + BA.

NEVER launches paid Actors, authenticates as a snapshot publisher or returns
production spending/publishing approval. Search-slot coverage is not proof
of actual vacancies. A static account JSON cannot authenticate live billing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from scripts.ba_acquisition_planner import coverage_for_slots, role_queries
from scripts.shared_refresh_controller import audit
from scripts.ba_wp_rest_routes import BA_SNAPSHOT_URL
from scripts.send_salesforce_wordpress_snapshot_once import ENDPOINT as SF_SNAPSHOT_URL


def account_readiness(evidence=None, *, now):
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    if evidence is None:
        return {"verified": False, "reason": "CURRENT_APIFY_BILLING_UNAVAILABLE"}
    if not isinstance(evidence, dict):
        raise ValueError("Invalid financial evidence")
    maximum = evidence.get("account_limit_usd")
    used = evidence.get("account_usage_usd")
    if type(maximum) not in (int, float) or type(used) not in (int, float):
        return {"verified": False, "reason": "ACCOUNT_USAGE_AND_LIMIT_REQUIRED"}
    if abs(maximum - 19) > .00001:
        return {"verified": False, "reason": "ACCOUNT_LIMIT_MISMATCH_NOT_19",
                "observed_limit_usd": maximum}
    if used < 0 or used > maximum:
        return {"verified": False, "reason": "INVALID_USAGE"}
    try:
        stamp = datetime.fromisoformat(evidence["observed_at"].replace("Z", "+00:00"))
    except (ValueError, KeyError, AttributeError, TypeError):
        return {"verified": False, "reason": "MISSING_TIMESTAMP"}
    age = now.astimezone(timezone.utc) - stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    if age is None or not timedelta(0) <= age <= timedelta(minutes=15):
        return {"verified": False, "reason": "STALE_OR_FUTURE_READING"}
    return {"verified": False, "reason": "SUPPLIED_JSON_CANNOT_AUTHENTICATE_ACCOUNT"}


def assess(*, now=None, account=None):
    now = now or datetime.now(timezone.utc)
    previous = audit()
    family_definitions = role_queries()
    count = len(coverage_for_slots(5))
    if len(family_definitions) != 22 or count != 22:
        raise ValueError("Business Analysis 22-family rotation plan is broken")
    sf = urlsplit(SF_SNAPSHOT_URL)
    ba = urlsplit(BA_SNAPSHOT_URL)
    if not (sf.scheme == ba.scheme == "https"
        and sf.hostname == ba.hostname == "jobs.zarafytek.com"
        and sf.path == "/wp-json/salesforce-tracker/v1/snapshot"
        and ba.path == "/" and ba.query == "rest_route=/business-analysis-tracker/v1/snapshot"):
        raise ValueError("Distinct HTTPS WordPress delivery destinations changed")
    if not previous["ba_paid_collection_paused"]:
        raise ValueError("Business Analysis paid hold has unexpectedly changed")
    account_state = account_readiness(account, now=now)
    blockers = [
        "SHARED_CONTROLLER_NOT_ACTIVE",
        "SALESFORCE_SYNC_RUNS_MISSING_IMMUTABLE_IDS",
        "CROSS_RUN_ARCHIVE_NOT_LIVE_REHEARSED",
        "REAL_DATA_FAMILY_COVERAGE_UNVERIFIED",
        "BA_DELIVERY_CREDENTIALS_NOT_AUTHENTICATED_IN_CURRENT_RUN",
        "BOTH_RECEIVERS_NOT_END_TO_END_SHADOW_VALIDATED",
        "NO_VERIFIED_IDENTICAL_CROSS_TRACKER_REQUEST",
    ]
    blockers.append(account_state["reason"])
    return {
        "schema": "shared-phase4-readiness/v1",
        "status": "BLOCKED_NO_LIVE_ACTIVATION",
        "as_of_utc": now.astimezone(timezone.utc).isoformat(),
        "account_cap_required_usd": 19, "salesforce_reserve_usd": 8,
        "ba_allowance_usd": 11, "account": account_state,
        "ba_rotation": {"defined_families": 22,
                        "unique_search_opportunities_in_first_five_slots": count,
                        "actual_22_family_vacancy_coverage_evidenced": False},
        "receivers": {"salesforce": {"method": "POST", "host": sf.hostname, "path": sf.path},
                      "business_analysis": {"method": "POST", "host": ba.hostname, "rest_route": ba.query},
                      "authenticated_ba_delivery_proven_now": False},
        "configured_exact_cross_tracker_queries": previous["current_exact_source_input_matches"],
        "verified_avoided_charge_usd": 0,
        "paid_actors_started": 0, "wordpress_requests": 0,
        "paid_acquisition_approved": False, "wordpress_publication_approved": False,
        "blockers": sorted(set(blockers)),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    p.add_argument("--observed-account-json", type=Path,
                   help="Advisory only; supplied JSON cannot authorize paid activity")
    args = p.parse_args()
    evidence = json.loads(args.observed_account_json.read_text()) if args.observed_account_json else None
    report = assess(account=evidence)
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
