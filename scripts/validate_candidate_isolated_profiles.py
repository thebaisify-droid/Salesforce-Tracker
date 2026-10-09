"""Validate that separate CV-Library/Totaljobs proposals cannot run or mutate saved tasks."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

EXPECTED={"CV-Library":"develop_ify/cv-library-scraper-task","Totaljobs":"develop_ify/totaljobs-com-scraper-task"}
def validate(p):
    errors=[]
    if p.get("enabled") is not False or p.get("paid_acquisition_enabled") is not False or p.get("approved_spend_usd") != 0:
        errors.append("pilot_must_remain_inactive")
    if p.get("production_tasks_immutable") is not True:
        errors.append("production_task_mutation_not_allowed")
    profiles=p.get("source_profiles")
    if not isinstance(profiles,list) or len(profiles)!=2 or {x.get("source") for x in profiles if isinstance(x,dict)}!=set(EXPECTED):
        errors.append("unexpected_source_profiles")
    else:
        for item in profiles:
            source=item["source"]
            if item.get("production_task")!=EXPECTED[source]:
                errors.append("production_task_reference_mismatch:"+source)
            if item.get("actor_input_schema_verified") is not False or item.get("override_support_verified") is not False:
                errors.append("unsubstantiated_schema_claim:"+source)
            queries=item.get("proposed_searches")
            if not isinstance(queries,list) or not 1<=len(queries)<=2:
                errors.append("unbounded_query_proposal:"+source)
            elif source=="CV-Library" and any(not isinstance(q,dict) or q.get("maxResults",0)>15 or q.get("maxResults",0)<1 for q in queries):
                errors.append("invalid_cv_library_result_limit")
    return {"safe_proposal":not errors,"ready_for_paid_run":False,"production_task_changes":False,"errors":errors}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/candidate_isolated_search_profiles.example.json")
    a=p.parse_args()
    out=validate(json.loads(Path(a.config).read_text(encoding="utf-8")))
    print(json.dumps(out,sort_keys=True))
    return 0 if out["safe_proposal"] else 2
if __name__=="__main__":raise SystemExit(main())
