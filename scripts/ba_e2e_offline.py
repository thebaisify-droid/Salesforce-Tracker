"""Offline, complete BA five-source handoff dry run. No API, Actor, WP or GitHub writes."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from urllib.parse import urlsplit
from scripts.ba_stage_five_source_data import stage, MAPPING
from scripts.ba_wordpress_delivery_package import pack, preflight
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT=Path(__file__).resolve().parents[1]
STAGING=ROOT/"business-analysis-tracker/data/dryrun"
EXPECTED={"CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"}

def run_offline(batch:dict, evidence:dict):
    sources=batch.get("sources",[])
    if len(sources)!=5 or {x.get("name") for x in sources}!=EXPECTED:
        raise ValueError("Exactly five distinct source receipts required")
    receipts=[{"source":x["name"],"attempted":x.get("attempted"),
               "status":x.get("status")} for x in sources]
    gate=validate_run_receipts(receipts,qa_passed=True)
    if not gate["publish_fresh_five_source_snapshot"]:
        return {"status":"BLOCKED_PRESERVE_LIVE_SNAPSHOT","reasons":gate["reasons"],
                "actors_started":0,"wordpress_requests":0}
    staged=stage(batch,evidence)
    if staged.get("status")!="FIVE_SOURCES_RECEIVED_STAGED_ONLY" or not staged.get("records"):
        raise ValueError("No classified advertisements staged")
    # Explicitly adapt the stager's job_source to the WordPress view's source,
    # preserving the exact source run and original advert link on each row.
    rows=[]
    for original in staged["records"]:
        row=dict(original)
        row["source"]=row["job_source"]
        row["url"]=row["original_advert_url"]
        row["sector_display"]=row["sector"]
        row["publication_approved"]=False
        if not row["source_run_id"] or not row["url"].startswith("https://"):
            raise ValueError("Record provenance absent")
        if urlsplit(row["url"]).hostname is None:
            raise ValueError("Invalid advert host")
        rows.append(row)
    candidate={"schema":"ba-dryrun-wordpress-candidate/v1","records":rows,
               "publication_approved":False,"source_observed_only":True}
    inspection=preflight(candidate,receipts)
    if not inspection["valid_for_wordpress_delivery"]:
        raise ValueError("Delivery gate blocked: "+repr(inspection["issues"]))
    package=pack(candidate,receipts)
    assert package["delivery_approved"] is False
    return {"status":"DRY_RUN_PASS_NOT_PUBLISHED","sources":len(sources),
            "raw_source_rows":sum(len(x["records"]) for x in sources),
            "matched":len(rows),"rejected":staged.get("rejected"),
            "preview_sha256":package["sha256"],"actors_started":0,
            "wordpress_requests":0,"stage":staged,"candidate":candidate,"package":package}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",type=Path,required=True)
    p.add_argument("--mapping",type=Path,default=MAPPING)
    p.add_argument("--outdir",type=Path,default=STAGING)
    args=p.parse_args()
    if args.outdir.resolve().is_relative_to((ROOT/"dashboard").resolve()):
        p.error("Never write to Salesforce dashboard paths")
    batch=json.loads(args.batch.read_text(encoding="utf8"))
    evidence=json.loads(args.mapping.read_text(encoding="utf8"))
    result=run_offline(batch,evidence)
    args.outdir.mkdir(parents=True,exist_ok=True)
    summary={k:v for k,v in result.items() if k not in {"stage","candidate","package"}}
    (args.outdir/"report.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf8")
    for key in ("stage","candidate","package"):
        if key in result:
            (args.outdir/(key+".json")).write_text(json.dumps(result[key],ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps(summary,sort_keys=True))
    return 0 if result["status"]=="DRY_RUN_PASS_NOT_PUBLISHED" else 2
if __name__=="__main__":raise SystemExit(main())
