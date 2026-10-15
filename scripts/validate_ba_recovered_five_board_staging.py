"""Fail-closed assurance for separately acquired five-board BA advertisements."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"business-analysis-tracker/evidence/ba-five-source-recovered-staging-20261015.json"
SOURCES={"CV-Library":10,"Totaljobs":10,"Reed UK":7,"Indeed UK":6,"JobServe":24}
def verify(data):
    problems=[]
    rows=data.get("records",[])
    if not isinstance(rows,list) or len(rows)!=57:problems.append("EXPECTED_57_SOURCE_ADVERTISEMENTS")
    actual=dict(Counter(r.get("source") for r in rows if isinstance(r,dict)))
    if actual!=SOURCES:problems.append("SOURCE_COUNTS_MISMATCH")
    urls=[r.get("url") for r in rows if isinstance(r,dict)]
    if len(set(urls))!=len(urls) or not all(isinstance(u,str) and u.startswith("https://") for u in urls):problems.append("DUPLICATE_OR_UNSAFE_SOURCE_LINK")
    if any(r.get("publication_approved") is not False for r in rows if isinstance(r,dict)):problems.append("UNSAFE_RECORD_PUBLICATION")
    if data.get("publication_approved") is not False or data.get("wordpress_updated") is not False:problems.append("UNSAFE_PUBLICATION")
    if data.get("source_retrieval_events",{}).get("JobServe",{}).get("actual_dataset_items")!=24:problems.append("JOBSERVE_COUNT_NOT_RECONCILED")
    if data.get("source_retrieval_events",{}).get("JobServe",{}).get("limit_discrepancy_pending_review") is not True:problems.append("UNRESOLVED_LIMIT_MUST_REMAIN_VISIBLE")
    if data.get("source_retrieval_events",{}).get("JobServe",{}).get("actual_charges_unverified") is not True:problems.append("BILLING_NOT_CONFIRMED")
    if data.get("paid_runs_launched_by_processing")!=0:problems.append("PROCESSOR_MUST_BE_FREE")
    ids={r.get("id") for r in rows if isinstance(r,dict)}
    if len(ids)!=57:problems.append("ROW_ID_COLLISION")
    possible=data.get("potential_duplicate_pairs") or []
    if not isinstance(possible,list) or len(possible)<2:problems.append("MISSING_POSSIBLE_DUPLICATE_EVIDENCE")
    else:
        for pair in possible:
            a,b=pair.get("ids",[None,None])
            if a not in ids or b not in ids or pair.get("status")!="POSSIBLE_ONLY":problems.append("INCORRECT_DUPLICATE_STATUS")
    return {"valid_for_further_staging":not problems,"issues":problems,"matching_source_advertisements":len(rows),"confirmed_distinct_vacancies":None,"may_publish":False}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,default=INPUT)
    args=ap.parse_args()
    result=verify(json.loads(args.input.read_text(encoding="utf8")))
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result["valid_for_further_staging"] else 2)
if __name__=="__main__":main()
