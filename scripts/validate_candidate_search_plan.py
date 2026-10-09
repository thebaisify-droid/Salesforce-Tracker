"""Validate proposed source inputs without contacting providers or spending money."""
from __future__ import annotations
import json
import argparse
from pathlib import Path

REQUIRED=("Indeed UK","JobServe","CV-Library","Totaljobs")
def check(spec):
    issues=[]
    if spec.get("mode")!="OFFLINE_ONLY" or spec.get("actor_runs_allowed")!=0 or spec.get("approved_spend_usd")!=0:
        issues.append("unsafe_acquisition_permission")
    sources=spec.get("source_inputs",[])
    if len(sources)!=4 or {s.get("source") for s in sources}!=set(REQUIRED):
        issues.append("missing_or_duplicate_sources")
    for s in sources:
        name=s.get("source")
        cap=s.get("max_total_charge_usd")
        if not isinstance(cap,(float,int)) or isinstance(cap,bool) or not 0<cap<=0.15:
            issues.append("invalid_source_cap:"+str(name))
        payload=s.get("example_input")
        if name=="Indeed UK":
            if not isinstance(payload,dict) or payload.get("country")!="uk" or not isinstance(payload.get("query"),str) or not 1<=payload.get("maxResults",0)<=30:
                issues.append("invalid_indeed_input")
        elif name=="JobServe":
            if not isinstance(payload,dict) or payload.get("country")!="gb" or not isinstance(payload.get("keywords"),list) or not payload["keywords"] or not 1<=payload.get("maxResults",0)<=30:
                issues.append("invalid_jobserve_input")
        elif name in ("CV-Library","Totaljobs"):
            if payload is not None or s.get("schema_status")!="SAVED_TASK_INPUT_OVERRIDE_NOT_VERIFIED":
                issues.append("unverified_saved_task_override:"+name)
    return {"passed":not issues,"issues":issues,"acquisition_authorised":False,"publication_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/candidate_search_dry_run.example.json")
    a=p.parse_args()
    result=check(json.loads(Path(a.config).read_text(encoding="utf-8")))
    print(json.dumps(result,sort_keys=True))
    return 0 if result["passed"] else 2

if __name__=="__main__":raise SystemExit(main())
