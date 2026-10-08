"""Validate an INACTIVE acquisition proposal. Never start Apify work."""
from __future__ import annotations
import json
import argparse
from pathlib import Path

def validate(p):
    required={"CV-Library","Totaljobs","Indeed UK","JobServe"}
    errors=[]
    if set(p.get("core_sources",[]))!=required: errors.append("core_sources_mismatch")
    if p.get("enabled") or p.get("paid_acquisition_enabled") or p.get("production_publication_enabled"):
        errors.append("unsafe_activation")
    if p.get("scheduled_runs"): errors.append("pilot_must_not_schedule_runs")
    if p.get("actor_runs_to_launch") != 0: errors.append("pilot_must_not_launch_actors")
    if p.get("additional_spend_approved_usd") != 0: errors.append("spend_not_approved")
    cap=p.get("shared_account_monthly_limit_usd")
    if not isinstance(cap,(int,float)) or isinstance(cap,bool) or cap>19 or cap<=0: errors.append("invalid_shared_limit")
    costs=p.get("proposed_per_source_max_usd",{})
    if set(costs)!=required or any(not isinstance(x,(int,float)) or isinstance(x,bool) or x<=0 for x in costs.values()):
        errors.append("missing_positive_source_caps")
    else:
        if abs(sum(costs.values())-p.get("proposed_total_max_usd",0))>0.000001:
            errors.append("pilot_cost_sum_mismatch")
    allocation=p.get("proposed_pilot_allocation_usd")
    if not isinstance(allocation,(int,float)) or isinstance(allocation,bool) or allocation<=0 or allocation>19:
        errors.append("invalid_pilot_allocation")
    elif isinstance(p.get("proposed_total_max_usd"),(int,float)) and p["proposed_total_max_usd"]>allocation:
        errors.append("pilot_exceeds_reserved_allocation")
    evidence=p.get("pricing_evidence",{})
    if not evidence.get("actor_rates_are_indicative") or not evidence.get("indeed_uk",{}).get("url") or not evidence.get("jobserve",{}).get("url"):
        errors.append("incomplete_pricing_evidence")
    return {"passed":not errors,"errors":errors,"pilot_authorised":False,"paid_acquisition_enabled":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/candidate_acquisition_pilot.example.json")
    a=p.parse_args()
    result=validate(json.loads(Path(a.config).read_text(encoding="utf-8")))
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 2

if __name__=="__main__":raise SystemExit(main())
