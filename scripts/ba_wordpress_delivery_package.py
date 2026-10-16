"""Prepare a BA WordPress delivery package without sending it.

Validation checks all five successful run receipts, source links, and observed
records. Manual WordPress delivery remains a separate action, and this module
cannot send HTTP requests.
"""
from __future__ import annotations
import argparse, hashlib, html, json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/"business-analysis-tracker/evidence/ba-five-source-publication-candidate-20261015.json"
OUTPUT=ROOT/"business-analysis-tracker/data/wordpress-delivery-preview.json"
EXPECTED={"CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"}
def preflight(data, receipts=None):
    errors=[]
    records=data.get("records")
    if not isinstance(records,list) or not records:errors.append("EMPTY_OR_MISSING_RECORDS");records=[]
    sources={r.get("source") for r in records if isinstance(r,dict)}
    # A targeted source may succeed yet yield zero roles in this refresh.
    # Receipt-level assurance (below), not appearance of every source in
    # the qualifying rows, establishes that all five source runs succeeded.
    if not sources or not sources.issubset(EXPECTED):
        errors.append("INVALID_OR_EMPTY_RECORD_SOURCE_SET")
    ids=[r.get("id") for r in records if isinstance(r,dict)]
    if len(ids)!=len(set(ids)):errors.append("RECORD_ID_COLLISION")
    for r in records:
        if not isinstance(r,dict):errors.append("MALFORMED_ROW");continue
        u=r.get("original_advert_url") or r.get("url")
        p=urlsplit(u) if isinstance(u,str) else None
        if not p or p.scheme!="https" or not p.hostname or p.username or p.password:errors.append("UNSAFE_JOB_URL")
        if not r.get("title") or not r.get("role_family") or not r.get("source_run_id"):errors.append("MISSING_REQUIRED_FIELD")
    if receipts is None:errors.append("FRESH_BATCH_RECEIPTS_NOT_PROVIDED")
    else:
        gate=validate_run_receipts(receipts,qa_passed=not errors)
        if not gate["publish_fresh_five_source_snapshot"]:errors+=gate["reasons"]
    return {"valid_for_wordpress_delivery":not errors,"issues":sorted(set(errors)),
            "source_records":len(records),"publication_automatically_enabled":False}
def pack(data,receipts):
    state=preflight(data,receipts)
    if not state["valid_for_wordpress_delivery"]:raise ValueError("Not eligible for delivery: "+", ".join(state["issues"]))
    rows=data["records"]
    def e(s):return html.escape(str(s or "Not specified"),quote=True)
    def ddmmyyyy(s):
        try:return date.fromisoformat(s).strftime("%d/%m/%Y")
        except (TypeError,ValueError):return "Not specified"
    cells=[]
    for r in rows:
        url=e(r.get("original_advert_url") or r.get("url"))
        cells.append('<tr class="ba-v2-record"><td><strong>'+e(r.get("title"))+'</strong><small>Role family: '+e(r.get("role_family"))+'</small><details><summary>Job description summary</summary><p>Source excerpt: '+e(r.get("description_summary"))+'</p></details></td><td>'+e(r.get("advertiser"))+'<small>Sector: '+e(r.get("sector_display") or r.get("sector"))+'</small></td><td>'+e(r.get("location"))+'<small>Work mode: '+e(r.get("working_arrangement"))+'</small></td><td>'+e(r.get("employment"))+'</td><td>'+e(r.get("source"))+'</td><td>'+ddmmyyyy(r.get("posted_date"))+'</td><td><a target="_blank" rel="noopener noreferrer nofollow" href="'+url+'">View original advert ↗</a></td></tr>')
    # A separate approved receiver must atomically replace both content regions.
    script='<script type="application/json" id="ba-v2-json">'+json.dumps(rows,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+'</script>'
    table='<tbody id="ba-v2-body">'+''.join(cells)+'</tbody>'
    sha=hashlib.sha256((table+script).encode()).hexdigest()
    return {"schema":"ba-wordpress-delivery-package/v1","page_id":49,
            "sha256":sha,"rows":len(rows),"table_fragment":table,"embedded_json_fragment":script,
            "delivery_approved":False,"source_gate":"FIVE_SUCCEEDED_QA_PASSED"}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--candidate",type=Path,default=DEFAULT)
    p.add_argument("--receipts",type=Path)
    p.add_argument("--output",type=Path,default=OUTPUT)
    args=p.parse_args()
    candidate=json.loads(args.candidate.read_text(encoding="utf8"))
    receipts=json.loads(args.receipts.read_text(encoding="utf8")).get("receipts") if args.receipts else None
    inspection=preflight(candidate,receipts)
    if not inspection["valid_for_wordpress_delivery"]:
        print(json.dumps({"status":"BLOCKED_NO_WORDPRESS_WRITE",**inspection},sort_keys=True))
        return 0
    package=pack(candidate,receipts)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(package,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"PACKAGE_CREATED_NOT_PUBLISHED","rows":package["rows"]}))
    return 0
if __name__=="__main__":raise SystemExit(main())
