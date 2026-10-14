"""Validate an INACTIVE two-source cybersecurity acquisition proposal offline.

Never launches Apify, approves paid acquisition, schedules a run, or publishes
any records. A successful validation says only that the PROPOSAL is internally
consistent, NOT that money may be spent.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

PROPOSED = {
    "Indeed UK": ("wildorigins/indeed-jobs", "BkcKc9frZp43LeRM7"),
    "JobServe": ("solidcode/jobserve-scraper", "iEeTOwSjZDvAshw7Y"),
}
PER_RUN_CAP = Decimal("0.10")
COMBINED_CAP = Decimal("0.20")


def usd(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("invalid amount")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError("invalid amount")
        return amount
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("invalid amount") from exc


def validate(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValueError("Expected a configuration object")
    issues = []
    if (config.get("status") != "PROPOSAL_NOT_AUTHORISED"
            or config.get("enabled") is not False
            or config.get("paid_acquisition_enabled") is not False
            or config.get("publication_enabled") is not False
            or config.get("actor_runs_allowed") != 0
            or config.get("actor_retries_allowed") != 0
            or config.get("scheduled_runs") != []
            or config.get("no_automatic_retries") is not True
            or config.get("production_salesforce_tasks_immutable") is not True):
        issues.append("unsafe_activation_or_production_mutation")
    try:
        if usd(config.get("approved_spend_usd")) != 0:
            issues.append("paid_spend_must_remain_zero")
        if usd(config.get("shared_account_limit_usd")) != 19:
            issues.append("shared_account_limit_must_remain_19")
        if usd(config.get("protected_salesforce_reserve_usd")) != 8:
            issues.append("salesforce_reserve_must_remain_8")
        if usd(config.get("pilot_max_total_charge_usd")) != COMBINED_CAP:
            issues.append("wrong_two_run_total_cap")
    except ValueError:
        issues.append("invalid_budget_fields")
    if (config.get("current_apify_usage_verified") is not False
            or config.get("account_limit_independently_confirmed") is not False
            or config.get("unreserved_remaining_balance_usd") is not None):
        issues.append("unverified_account_usage_cannot_be_accepted")
    searches = config.get("source_searches")
    if not isinstance(searches, list) or len(searches) != 2:
        issues.append("require_exactly_two_proposed_sources")
        searches = []
    names = [x.get("source") if isinstance(x, dict) else None for x in searches]
    if set(names) != set(PROPOSED) or len(set(names)) != 2:
        issues.append("wrong_or_duplicate_source")
    combined = Decimal("0")
    for entry in searches:
        if not isinstance(entry, dict):
            issues.append("invalid_source_entry")
            continue
        source = entry.get("source")
        if source not in PROPOSED:
            continue
        if (entry.get("actor"), entry.get("actor_id")) != PROPOSED[source]:
            issues.append("actor_identity_mismatch:" + source)
        if entry.get("actor_schema_verified") is not True:
            issues.append("actor_schema_unverified:" + source)
        if entry.get("non_salesforce_execution_verified") is not False:
            issues.append("cannot_claim_executed_pilot:" + source)
        if entry.get("separate_saved_task_required") is not True:
            issues.append("production_task_mutation_risk:" + source)
        cap = (entry.get("run_options") or {}).get("maxTotalChargeUsd")
        try:
            amount = usd(cap)
            if amount != PER_RUN_CAP:
                issues.append("invalid_run_cap:" + source)
            combined += amount
        except ValueError:
            issues.append("invalid_run_cap:" + source)
        data = entry.get("input")
        if not isinstance(data, dict):
            issues.append("missing_source_input:" + source)
            continue
        if source == "Indeed UK":
            if (set(data) != {"query", "location", "country", "maxResults"}
                    or data.get("country") != "uk"
                    or data.get("query") != "information security analyst"
                    or data.get("location") != ""
                    or type(data.get("maxResults")) is not int
                    or data["maxResults"] != 10):
                issues.append("invalid_indeed_input")
        elif source == "JobServe":
            if (set(data) != {"keywords", "location", "country", "distance",
                              "postedSince", "includeDescription",
                              "onlyUniqueJobs", "maxResults"}
                    or data.get("keywords") != ["third party risk analyst"]
                    or data.get("country") != "gb"
                    or data.get("location") != ""
                    or data.get("distance") != "50"
                    or data.get("postedSince") != "7"
                    or data.get("includeDescription") is not False
                    or data.get("onlyUniqueJobs") is not True
                    or type(data.get("maxResults")) is not int
                    or data["maxResults"] != 10):
                issues.append("invalid_jobserve_input")
    if combined != COMBINED_CAP:
        issues.append("run_caps_do_not_sum_to_proposed_total")
    return {
        "schema": "candidate-cyber-acquisition-preflight-validation/v1",
        "proposal_valid": not issues,
        "issues": issues,
        "paid_acquisition_authorised": False,
        "safe_to_start_actors": False,
        "publication_approved": False,
        "pilot_cost_ceiling_usd": str(COMBINED_CAP),
        "blocking_external_evidence": [
            "current_authenticated_apify_usage",
            "confirmed_account_limit_and_salesforce_reservation",
            "new_explicit_one_time_paid_run_approval",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fail-closed acquisition preflight")
    parser.add_argument("--config", default="config/candidate_cyber_acquisition_preflight.example.json")
    args = parser.parse_args()
    result = validate(json.loads(Path(args.config).read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["proposal_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
