"""Validate the disabled BA five-source refresh contract and eventual collection receipts.

Checks are read-only, never launch Apify Actors or trigger GitHub workflows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = {"CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe"}
ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "business-analysis-tracker" / "config" / "five_source_refresh.json"


def validate_config(cfg: dict) -> dict:
    issues = []
    sources = cfg.get("sources", [])
    names = [x.get("name") for x in sources if isinstance(x, dict)]
    if len(sources) != 5 or len(names) != 5 or set(names) != EXPECTED or len(set(names)) != 5:
        issues.append("REQUIRE_EXACTLY_FIVE_DISTINCT_SOURCES")
    if len({x.get("actor") for x in sources if isinstance(x, dict)}) != 5:
        issues.append("ACTOR_ID_COLLISION")
    if cfg.get("shared_account_monthly_limit_usd") != 19 or cfg.get("protected_salesforce_reserve_usd") != 8:
        issues.append("PROTECTED_BUDGET_MISMATCH")
    if cfg.get("require_all_five_sources_attempted") is not True:
        issues.append("MUST_REQUIRE_ALL_FIVE")
    if cfg.get("publication_gate") != "ALL_FIVE_SUCCEEDED_AND_QA_PASSED":
        issues.append("UNSAFE_PARTIAL_PUBLICATION")
    if cfg.get("failure_policy") != "KEEP_LAST_SUCCESSFUL_SNAPSHOT_WITH_SOURCE_STATUS; DO_NOT_PUBLISH_PARTIAL_AS_FULL":
        issues.append("UNSAFE_FAILURE_POLICY")
    if cfg.get("automatic_retries_enabled") is not False:
        issues.append("RETRIES_NOT_PERMITTED")
    if cfg.get("enabled") is not False or cfg.get("paid_acquisition_enabled") is not False or cfg.get("publication_enabled") is not False or cfg.get("actor_runs_to_launch") != 0:
        issues.append("NOT_SAFE_PRE_APPROVAL")
    if cfg.get("ba_spend_approved_usd") != 0 or cfg.get("scheduled_runs") != []:
        issues.append("PRE_APPROVAL_SPENDING_OR_SCHEDULE")
    if any(x.get("mode") != "NEW_ISOLATED_BA_INPUT" or not x.get("family_query_example") or x.get("pilot_authorised") is not False for x in sources if isinstance(x, dict)):
        issues.append("SOURCE_INPUT_NOT_ISOLATED")
    return {"valid": not issues, "issues": issues, "source_count": len(names), "paid_runs_enabled": False}


def validate_run_receipts(receipts: list[dict], *, qa_passed: bool) -> dict:
    statuses = {x.get("source"): x.get("status") for x in receipts if isinstance(x, dict)}
    attempted = [x.get("source") for x in receipts if isinstance(x, dict) and x.get("attempted") is True]
    reasons = []
    if len(receipts) != 5 or len(set(attempted)) != 5 or set(attempted) != EXPECTED:
        reasons.append("NOT_ALL_FIVE_ATTEMPTED")
    if set(statuses) != EXPECTED or any(statuses.get(s) != "SUCCEEDED" for s in EXPECTED):
        reasons.append("NOT_ALL_FIVE_SUCCEEDED")
    if not qa_passed:
        reasons.append("QUALITY_GATE_FAILED")
    return {"publish_fresh_five_source_snapshot": not reasons,
            "reasons": reasons,
            "attempted": sorted(set(attempted)),
            "source_status": statuses,
            "preserve_prior_snapshot": bool(reasons)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=Path, default=DEFAULT)
    args = p.parse_args()
    report = validate_config(json.loads(args.config.read_text(encoding="utf-8")))
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["valid"] else 2)


if __name__ == "__main__":
    main()
