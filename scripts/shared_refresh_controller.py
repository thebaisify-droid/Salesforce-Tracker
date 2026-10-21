"""Read-only unified Salesforce/BA acquisition controller preflight.

One orchestrator and two consumers are the *target architecture*. This module
makes no paid Actor calls, no dashboard changes, and no schedule changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.shared_dataset_reuse import configured_overlap
from scripts.shared_acquisition_ledger import SharedLedger

ROOT = Path(__file__).resolve().parents[1]


def audit(ledger_path=None):
    sf = json.loads((ROOT / "config/pipeline.json").read_text(encoding="utf-8"))
    ba = json.loads((ROOT / "business-analysis-tracker/config/automated_refresh_pipeline.json").read_text(encoding="utf-8"))
    if (sf.get("apify_budget", {}).get("monthly_usd") != 19
            or ba.get("monthly_limit_usd") != 19
            or ba.get("salesforce_reserve_usd") != 8
            or ba.get("monthly_ba_allowance_usd") != 11
            or ba.get("max_total_charge_usd") != 1.2
            or ba.get("automatic_retries") != 0):
        raise ValueError("Shared acquisition limits must be $19/$8/$11, no retries")
    overlaps = configured_overlap()
    result = {
        "schema": "sf-ba-combined-audit/v1", "status": "READ_ONLY_NO_SPEND",
        "account_cap_expected_usd": 19, "salesforce_reserved_usd": 8,
        "ba_allowance_usd": 11, "salesforce_per_source_cycle_max_usd": 0.90,
        "ba_per_source_cycle_max_usd": 1.20,
        "ba_paid_collection_paused": not (ba.get("paid_acquisition_enabled") is True
                                         and ba.get("scheduling_enabled") is True),
        "current_exact_source_input_matches": overlaps["current_exact_input_matches"],
        "same_actor_but_different_query": overlaps["same_actor_non_reusable"],
        "validated_reuses": [], "measured_avoided_actor_cost_usd": 0,
        "actors_started": 0, "wordpress_requests": 0, "live_activated": False,
        "note": "Current source searches differ; shared reuse requires matched complete run-specific search windows and QA evidence.",
    }
    if ledger_path is not None:
        result["validated_ledger_receipt_count"] = len(SharedLedger(ledger_path).read())
    return result


def main():
    parser = argparse.ArgumentParser(description="Shared acquisition read-only preflight")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--ledger", type=Path, default=None)
    args = parser.parse_args()
    print(json.dumps(audit(args.ledger), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
