"""Read-only five-source BA acquisition preflight: no network calls, paid runs or publication."""
from __future__ import annotations
import json
import argparse
from pathlib import Path
from scripts.validate_ba_five_source_contract import validate_config

ROOT=Path(__file__).resolve().parents[1]
CONF=ROOT/"business-analysis-tracker/config/five_source_refresh.json"
INPUTS=ROOT/"business-analysis-tracker/config/five_source_search_inputs.json"
EXPECTED={"CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"}
KEYWORDS={"CV-Library":"query","Totaljobs":"keywords","Reed UK":"keywords","Indeed UK":"query","JobServe":"keywords"}
LIMITS={"CV-Library":"maxResults","Totaljobs":"maxListings","Reed UK":"maxResults","Indeed UK":"maxResults","JobServe":"maxResults"}

def preflight(contract:dict, spec:dict)->dict:
    issues=list(validate_config(contract)["issues"])
    if spec.get("enabled") is not False or spec.get("paid_runs_authorised") != 0:
        issues.append("PREAPPROVAL_ACTIVATION_PROHIBITED")
    payloads=spec.get("inputs",[])
    if not isinstance(payloads,list) or len(payloads)!=5 or {x.get("source") for x in payloads}!=EXPECTED:
        issues.append("FIVE_SOURCE_INPUTS_REQUIRED")
    for x in payloads:
        name=x.get("source")
        if name not in EXPECTED:
            continue
        expected=next((y for y in contract["sources"] if y["name"]==name),None)
        if expected is None or expected["actor"]!=x.get("actor"):
            issues.append("ACTOR_MISMATCH_"+name)
            continue
        data=x.get("input",{})
        query=data.get(KEYWORDS[name])
        if name=="JobServe":
            valid_query=isinstance(query,list) and query==["business analyst"]
        else:
            valid_query=query=="business analyst"
        if not valid_query or data.get(LIMITS[name]) != 10:
            issues.append("BAD_PILOT_QUERY_OR_CAP_"+name)
        if any(isinstance(v,str) and "salesforce" in v.lower() for v in data.values()):
            issues.append("PRODUCTION_QUERY_LEAK_"+name)
        if name=="Totaljobs" and data.get("mode")!="search":
            issues.append("TOTALJOBS_SEARCH_MODE_REQUIRED")
    evidence=spec.get("preflight",{})
    unverified=[k for k in ("source_specific_actor_pricing_verified","actual_monthly_apify_usage_read","account_limit_confirmed_live","salesforce_reserve_confirmed_live","paid_run_approved") if evidence.get(k) is not True]
    activation_ready=not issues and not unverified and isinstance(evidence.get("aggregate_new_charge_cap_usd"),(int,float)) and evidence["aggregate_new_charge_cap_usd"]>0
    return {"config_valid":not issues,"issues":issues,"all_five_inputs_prepared":len(payloads)==5,"paid_activation_ready":bool(activation_ready),"missing_activation_evidence":unverified,"actor_runs_started":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contract",type=Path,default=CONF)
    p.add_argument("--inputs",type=Path,default=INPUTS)
    a=p.parse_args()
    out=preflight(json.loads(a.contract.read_text()),json.loads(a.inputs.read_text()))
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["config_valid"] else 2)

if __name__=="__main__":
    main()
