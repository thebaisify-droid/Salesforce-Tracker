"""Fail-closed feasibility review before any 22-family paid validation."""
import json
from decimal import Decimal
from pathlib import Path

def inspect(plan,account_usage=None,actor_evidence=None):
    reasons=[]
    families=plan.get("families",[])
    if len(families)!=22 or len({f.get("family") for f in families})!=22:
        reasons.append("taxonomy_coverage_not_22")
    ceiling=Decimal(str(plan.get("proposed_validation_max_usd",0)))
    cap=Decimal(str(plan.get("per_run_cap_usd",0)))
    if cap<=0 or ceiling<=0 or ceiling>Decimal("1.50"):
        reasons.append("invalid_spend_limits")
        max_runs=0
    else:
        max_runs=int(ceiling//cap)
    # Every distinct family query is one Actor run unless multi-keyword operation
    # is explicitly supported, tested and priced for the selected Actor.
    if max_runs<len(families) and not (actor_evidence or {}).get("validated_multi_family_batches"):
        reasons.append("budget_cannot_cover_individual_family_queries")
    if account_usage is None:
        reasons.append("fresh_account_usage_required")
    else:
        limit=Decimal(str(account_usage.get("monthly_limit_usd",0)))
        used=Decimal(str(account_usage.get("usage_usd",999)))
        if limit>19 or used<0 or (limit-used)<Decimal("8")+ceiling:
            reasons.append("insufficient_account_reserve")
    if not (actor_evidence or {}).get("source_schemas_verified"):
        reasons.append("source_input_schemas_unverified")
    if not (actor_evidence or {}).get("account_charging_verified"):
        reasons.append("source_charging_unverified")
    if plan.get("paid_runs_enabled") or plan.get("pilot_spend_approved_usd",0):
        reasons.append("paid_execution_must_remain_blocked")
    return {"ready_to_implement_paid_workflow":not reasons,
            "paid_execution_authorised":False,"actor_runs_started":0,
            "max_runs_at_declared_cap":max_runs,"distinct_family_queries":len(families),
            "minimum_independently_reviewed":plan.get("minimum_human_reviewed_records"),
            "reasons":reasons,"production_publication_authorised":False}

def main():
    plan=json.loads(Path("config/candidate_representative_validation_plan.json").read_text())
    print(json.dumps(inspect(plan),indent=2))
if __name__=="__main__":main()
