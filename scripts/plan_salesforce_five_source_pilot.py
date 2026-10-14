"""Offline, non-executing UK Salesforce five-source pilot plan.

Approval of this plan is NOT approval of any paid Actor run. No token is read,
no network calls are possible, and no execution command exists in this module.
"""
from __future__ import annotations
import json
from pathlib import Path

SOURCES = (
    ("CV-Library", "apify_task", "develop_ify/cv-library-scraper-task", 0.15, 20),
    ("Totaljobs", "apify_task", "develop_ify/totaljobs-com-scraper-task", 0.15, 20),
    ("Reed UK", "apify_task", "develop_ify/uk-jobs-reed-task", 0.15, 20),
    ("Indeed UK", "apify_actor", "wildorigins/indeed-jobs", 0.20, 20),
    ("JobServe", "apify_actor", "solidcode/jobserve-scraper", 0.25, 20),
)
REQUIRED = ("CV-Library", "Totaljobs", "Reed UK")
CEILING = 19.00
SALESFORCE_RESERVE = 8.00
TOTAL_CAP = 0.90


def plan():
    rows = [{"source": name, "provider": kind, "reference": ref,
             "max_total_charge_usd": cap, "requested_max_results": qty,
             "run_limit": 1}
            for name, kind, ref, cap, qty in SOURCES]
    assert round(sum(row["max_total_charge_usd"] for row in rows), 2) == TOTAL_CAP
    assert {x["source"] for x in rows if x["source"] in REQUIRED} == set(REQUIRED)
    return {"schema": "salesforce-five-source-pilot-plan/v1",
            "state": "PLANNING_ONLY_NOT_EXECUTABLE",
            "sources": rows,
            "aggregate_max_charge_usd": TOTAL_CAP,
            "required_sources": list(REQUIRED),
            "account_ceiling_usd": CEILING,
            "protected_reserve_usd": SALESFORCE_RESERVE,
            "quality_mode": "historical_evidence_review_only",
            "preflight_required": [
                "new_authenticated_account_limit_and_usage_read",
                "confirm_all_source_actor_pricing_and_saved_task_inputs",
                "verify_each_actor_supports_hard_maxTotalChargeUsd",
                "strict per-source and aggregate charge reservation",
                "explicit_user_authorisation_of_this_exact_paid_pilot",
            ],
            "stop_conditions": [
                "missing_or_changed_pricing_or_task_metadata",
                "account_cap_plus_reserve_would_be_breached",
                "unexpected_provider_response_or_failed_actor",
                "any_source_could_exceed_charge_cap",
            ],
            "actor_runs_started": 0,
            "paid_pilot_authorised": False,
            "auto_retries": 0,
            "workflow_dispatch_enabled": False,
            "wordpress_publication_enabled": False,
            "production_database_writes_enabled": False,
            "jobserve_sdk_usage": False}


def main():
    print(json.dumps(plan(), sort_keys=True))


if __name__ == "__main__":
    main()
