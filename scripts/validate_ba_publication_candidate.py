"""Review a five-board Business Analysis WordPress release candidate without publishing."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"business-analysis-tracker/evidence/ba-five-source-publication-candidate-20261015.json"
def validate(d):
    errors=[]
    rows=d.get("records",[])
    ids={x.get("id") for x in rows}
    if len(rows)!=57 or len(ids)!=57:errors.append("ROW_INTEGRITY")
    if d.get("matching_source_advertisements")!=57 or d.get("unique_display_clusters_provisional")!=55:errors.append("COUNTS")
    if len(d.get("duplicate_decisions",[]))!=2:errors.append("DUPLICATE_REVIEW_MISSING")
    for pair in d.get("duplicate_decisions",[]):
        if len(pair.get("record_ids",[]))!=2 or not set(pair["record_ids"])<=ids:errors.append("INVALID_PAIR")
        if pair.get("status")!="PROBABLE_CROSS_POSTING":errors.append("PAIR_STATUS")
    if not all(x.get("original_advert_url","").startswith("https://") for x in rows):errors.append("SOURCE_URL_MISSING")
    if len({x.get("source_run_id") for x in rows})!=5:errors.append("SOURCE_PROVENANCE_MISSING")
    if any(x.get("publication_approved") is not False for x in rows):errors.append("PREMATURE_RECORD_PUBLICATION")
    if d.get("publication_approved") is not False or d.get("wordpress_published") is not False:errors.append("PREMATURE_RELEASE")
    if d.get("jobserve_charge_usd") is not None or d.get("jobserve_limit_discrepancy")!="UNRESOLVED":errors.append("FALSE_BILLING_CERTAINTY")
    return {"staging_integrity_valid":not errors,"issues":errors,"publication_authorized":False}
def main():
    r=validate(json.loads(PATH.read_text(encoding="utf8")))
    print(json.dumps(r,sort_keys=True))
    raise SystemExit(0 if r["staging_integrity_valid"] else 2)
if __name__=="__main__":main()
