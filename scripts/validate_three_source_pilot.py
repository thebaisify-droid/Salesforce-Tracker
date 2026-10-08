"""Validate a blocked three-source budget proposal without contacting Apify."""
import json
from decimal import Decimal
from pathlib import Path
EXPECTED={"Totaljobs","Indeed UK","JobServe"}
def validate(d):
    errors=[]
    src=d.get("sources",[])
    names={s.get("source") for s in src if isinstance(s,dict)}
    if len(src)!=3 or names!=EXPECTED:errors.append("sources_not_exactly_three")
    if d.get("paid_execution_enabled") is not False or d.get("allowed_actor_runs")!=0 or d.get("publication_enabled") is not False:errors.append("not_disabled")
    if d.get("account_monthly_ceiling_usd")!=19 or d.get("minimum_protected_salesforce_headroom_usd",0)<8:errors.append("account_limit_or_reserve")
    if any(not isinstance(s,dict) or type(s.get("cap_usd")) not in (float,int) or s["cap_usd"]<=0 or type(s.get("max_results")) is not int or s["max_results"]>10 for s in src):errors.append("invalid_source_cap")
    else:
        total=sum((Decimal(str(s["cap_usd"])) for s in src),Decimal("0"))
        if total!=Decimal("0.50") or total!=Decimal(str(d.get("maximum_total_usd"))):errors.append("total_budget_mismatch")
    return {"valid":not errors,"issues":errors,"authorised":False,"actor_runs_allowed":0}
if __name__=="__main__":
    d=json.loads(Path("config/three_source_pilot_proposal.json").read_text())
    print(json.dumps(validate(d)))
