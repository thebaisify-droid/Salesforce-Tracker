"""No-spend gap coverage report for the UK Business & Technology Tracker.

Pure, offline analysis: no Actor starts, Apify reads, WordPress delivery or
scheduled-workflow dispatch. The gaps come from the independently audited live
dashboard of 18 October, not claims of employer-confirmed vacancies.
"""
from __future__ import annotations
import json
from pathlib import Path
from scripts.ba_acquisition_planner import role_queries, coverage_for_slots
from scripts.ba_controlled_refresh import CONFIG

ROOT=Path(__file__).resolve().parents[1]
ROTATION=ROOT/"business-analysis-tracker/config/role_search_rotation.json"
GAPS=(
    "Agile / Scrum",
    "Programme & Portfolio Management",
    "Agile Leadership",
    "Security Operations / SOC",
    "IT Security",
)
APPROVED_BUDGET={"monthly_limit_usd":19,"monthly_ba_allowance_usd":11,
                 "max_total_charge_usd":1.2,"salesforce_reserve_usd":8}


def check():
    cfg=json.loads(CONFIG.read_text(encoding="utf8"))
    rotation=json.loads(ROTATION.read_text(encoding="utf8"))
    for key, expected in APPROVED_BUDGET.items():
        if cfg.get(key)!=expected:
            raise ValueError("Active budget mismatch: "+key)
    metadata={
        "monthly_limit_usd":"monthly_account_ceiling_usd",
        "monthly_ba_allowance_usd":"ba_monthly_ceiling_usd",
        "max_total_charge_usd":"ba_run_max_usd",
        "salesforce_reserve_usd":"salesforce_reserve_usd",
    }
    for key, alias in metadata.items():
        if rotation.get(alias)!=APPROVED_BUDGET[key]:
            raise ValueError("Rotation budget metadata mismatch: "+alias)
    if cfg.get("automatic_retries")!=0:
        raise ValueError("Automatic retries forbidden")
    if any(cfg.get(flag) is not False for flag in
            ("enabled","paid_acquisition_enabled","scheduling_enabled",
             "wordpress_delivery_enabled","pricing_guard_verified",
             "recurring_budget_approved")):
        raise ValueError("Paid schedule must remain on safety hold")
    entries=role_queries()
    lookup={e["family"]:e["query"] for e in entries}
    if not set(GAPS).issubset(lookup):
        raise ValueError("Missing coverage family search terms")
    planned={}
    for slot in range(1,10):
        families={entries[((slot-1)*5+i)%len(entries)]["family"] for i in range(5)}
        for family in GAPS:
            if family in families and family not in planned:
                planned[family]=slot
    if coverage_for_slots(5)!=set(lookup):
        raise ValueError("Not all 22 taxonomy families rotate within five slots")
    return {
        "status":"OFFLINE_GAP_READINESS_NO_COST",
        "missing_family_count":len(GAPS),
        "missing_family_queries":[{"family":family,"query":lookup[family],
                                   "earliest_rotation_slot":planned[family]}
                                  for family in GAPS],
        "all_22_taxonomy_families_have_rotation_by_slot":5,
        "paid_refresh_enabled":False,
        "actor_runs_started":0,
        "wordpress_snapshots_sent":0,
        "budget":APPROVED_BUDGET,
        "adverts_not_invented":True,
    }


if __name__=="__main__":
    print(json.dumps(check(),sort_keys=True))
