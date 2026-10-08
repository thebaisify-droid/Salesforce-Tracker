"""Fail-closed offline review of revised pilot budget; never authorises acquisition."""
from decimal import Decimal
import json
from pathlib import Path

EXPECTED={"CV-Library","Totaljobs","Indeed UK","JobServe"}
def validate(p):
    issues=[]
    if p.get("paid_acquisition_enabled") is not False or p.get("additional_spend_approved_usd")!=0: issues.append("pilot_not_disabled")
    caps=p.get("proposed_caps_usd",{})
    if set(caps)!=EXPECTED or any(type(v) not in (int,float) or v<=0 for v in caps.values()):
        issues.append("invalid_source_caps")
    else:
        total=sum((Decimal(str(v)) for v in caps.values()),Decimal("0"))
        if total!=Decimal(str(p.get("proposed_total_usd"))):issues.append("cap_sum_mismatch")
        if total>Decimal("0.80"):issues.append("exceeds_proposed_pilot_ceiling")
        if Decimal(str(caps["CV-Library"]))<=Decimal("0.10"):issues.append("does_not_address_known_cv_charge_abort")
    if p.get("shared_monthly_account_limit_usd")!=19:issues.append("shared_limit_changed")
    if p.get("protected_salesforce_headroom_usd",0)<8:issues.append("salesforce_protection_reduced")
    if p.get("maximum_results_per_source",999)>10:issues.append("result_limit_too_high")
    return {"proposal_valid":not issues,"issues":issues,"pilot_authorised":False,"paid_requests_allowed":False}
if __name__=="__main__":
    print(json.dumps(validate(json.loads(Path("config/candidate_pilot_rebudget_v2.example.json").read_text())),sort_keys=True))
