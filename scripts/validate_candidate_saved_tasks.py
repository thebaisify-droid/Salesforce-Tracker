"""Offline verification of documented saved Apify task input evidence."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

EXPECTED={"CV-Library":"develop_ify/cv-library-scraper-task","Totaljobs":"develop_ify/totaljobs-com-scraper-task"}

def check(document):
    errors=[]
    checks=document.get("task_checks")
    if document.get("paid_calls_permitted") is not False:
        errors.append("unsafe_paid_call_permission")
    if not isinstance(checks,list) or len(checks)!=2 or {x.get("source") for x in checks if isinstance(x,dict)}!=set(EXPECTED):
        errors.append("incorrect_task_inventory")
    else:
        for x in checks:
            if x.get("task_id")!=EXPECTED[x["source"]]:
                errors.append("unexpected_task_id:"+x["source"])
            if x.get("input_schema_verified") and not x.get("task_definition_exported"):
                errors.append("schema_claim_lacks_task_evidence:"+x["source"])
            if x.get("non_salesforce_search_verified") and not x.get("input_schema_verified"):
                errors.append("unsupported_search_claim:"+x["source"])
    verified=isinstance(checks,list) and len(checks)==2 and all(
        isinstance(x,dict) and x.get("task_definition_exported") and x.get("input_schema_verified") and x.get("non_salesforce_search_verified") for x in checks
    )
    return {"safe_specification":not errors,"task_overrides_verified":bool(not errors and verified),
            "paid_acquisition_authorised":False,"errors":errors}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/candidate_saved_task_evidence.example.json")
    args=p.parse_args()
    report=check(json.loads(Path(args.config).read_text(encoding="utf-8")))
    print(json.dumps(report,sort_keys=True))
    return 0 if report["safe_specification"] else 2

if __name__=="__main__":
    raise SystemExit(main())
