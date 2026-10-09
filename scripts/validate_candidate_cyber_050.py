"""Fail-closed offline proposal checks: no Actor starts or network calls."""
import json
from pathlib import Path

def validate(p):
    issues=[]
    if p.get("mode")!="OFFLINE_ONLY" or p.get("approved_spend_usd")!=0 or p.get("actor_runs_allowed")!=0 or p.get("scheduled") is not False or p.get("automatic_retries") is not False:
        issues.append("not_disabled")
    runs=p.get("source_runs",[])
    if len(runs)!=2 or [x.get("actor") for x in runs]!=["wildorigins/indeed-jobs","solidcode/jobserve-scraper"]:
        issues.append("incorrect_actors")
    if round(sum(x.get("max_total_charge_usd",999) for x in runs),2)!=0.50 or p.get("proposed_total_cap_usd")!=0.5:
        issues.append("budget_caps")
    if p.get("monthly_account_ceiling_usd")!=19 or p.get("salesforce_reserve_usd")!=8:
        issues.append("reserve_or_account_ceiling")
    if len(p.get("target_families",[]))!=7 or len(set(p["target_families"]))!=7:
        issues.append("seven_family_plan")
    if len(runs)==2:
        a,b=runs
        if a.get("proposed_input",{}).get("country")!="uk" or not 1<=a["proposed_input"].get("maxResults",0)<=15:
            issues.append("indeed_input")
        if b.get("proposed_input",{}).get("country")!="gb" or not 1<=b["proposed_input"].get("maxResults",0)<=15:
            issues.append("jobserve_input")
    return {"offline_plan_valid":not issues,"issues":issues,"acquisition_authorised":False,
            "execution_ready":False,"blocked_by":["fresh_account_usage","current_actor_pricing_and_charge_floor","jobserve_multikeyword_behavior","explicit_paid_run_approval"],
            "publication_approved":False}
if __name__=="__main__":
    p=json.loads(Path("config/candidate_cyber_050_proposal.json").read_text())
    result=validate(p)
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["offline_plan_valid"] else 2)
