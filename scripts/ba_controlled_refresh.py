"""Controlled five-source acquisition with 22-family rotating search planning.

API calls happen only after BA_PAID_REFRESH_APPROVAL and explicit --execute. Run
once per source, fail closed, no retries, no WordPress delivery and no Salesforce writes.
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from urllib.parse import urlencode
from scripts.ba_jobserve_api_once import api

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"business-analysis-tracker/config/automated_refresh_pipeline.json"
OUT=ROOT/"business-analysis-tracker/data/acquisition-receipts.json"
BASE="https://api.apify.com/v2/"
TERMINAL={"SUCCEEDED","FAILED","ABORTED","TIMED-OUT"}
def validate(cfg):
    if cfg.get("schema")!="ba-automatic-refresh/v1":raise ValueError("Incorrect schema")
    if cfg.get("monthly_limit_usd")!=25 or cfg.get("salesforce_reserve_usd")!=8:raise ValueError("Budget configuration unsafe")
    if cfg.get("search_profile") != "ROTATING_22_FAMILY_TAXONOMY":
        raise ValueError("All 22 job families must be covered by the scheduled search rotation")
    if cfg.get("automatic_retries") != 0:
        raise ValueError("Automatic retries are prohibited")
    if cfg.get("publish_automatically") is not cfg.get("wordpress_delivery_enabled"):
        raise ValueError("Publishing requires an identical WordPress delivery approval gate")
    if cfg.get("monthly_ba_allowance_usd") != 17 or cfg.get("max_scheduled_runs_per_month") != 9:
        raise ValueError("BA standing monthly allowance or cadence changed")
    if cfg.get("max_total_charge_usd") != 1.80:
        raise ValueError("Approved per-refresh cap exceeded")
    flags = ("enabled", "paid_acquisition_enabled", "scheduling_enabled",
             "recurring_budget_approved", "pricing_guard_verified")
    if any(cfg.get(k) is not True for k in flags) and any(cfg.get(k) is True for k in flags):
        raise ValueError("Partially enabled BA recurring acquisition is not permitted")
    if cfg.get("publish_automatically") is True and not all(cfg.get(k) is True for k in flags):
        raise ValueError("Cannot auto-deliver an unapproved BA acquisition")
    if cfg.get("publish_automatically") is not True and any(cfg.get(k) is True for k in flags):
        raise ValueError("Scheduled paid BA collection must use the quality-gated receiver")
    names=[x.get("name") for x in cfg.get("sources",[])]
    if names!=["CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"]:raise ValueError("Five sources are mandatory")
    approved_actors = {
        "CV-Library": ("blackfalcondata/cv-library-scraper", "maxResults"),
        "Totaljobs": ("abotapi/totaljobs-com-scraper", "maxListings"),
        "Reed UK": ("wildorigins/uk-jobs-reed", "maxResults"),
        "Indeed UK": ("wildorigins/indeed-jobs", "maxResults"),
        "JobServe": ("solidcode/jobserve-scraper", "maxResults"),
    }
    for source in cfg["sources"]:
        name = source["name"]
        actor, result_field = approved_actors[name]
        if source.get("actor") != actor:
            raise ValueError("Unapproved source Actor identity: " + name)
        size=source.get("max_items")
        value=(source.get("input") or {}).get(result_field)
        if type(size) is not int or not 1 <= size <= 50 or type(value) is not int or value != size:
            raise ValueError("Source input or result limit changed: " + name)
        cap=source.get("max_charge_usd")
        if type(cap) not in (int, float) or not 0 < cap <= 0.70:
            raise ValueError("Invalid Actor charge cap: " + name)
        if source.get("input",{}).get("incrementalMode",False) is not False:
            raise ValueError("Shared Actor incremental state disallowed")
    if round(sum(x["max_charge_usd"] for x in cfg["sources"]),2) != 1.80:
        raise ValueError("Sum of per-source charge caps differs from authorisation")
    return {"valid":True,"sources":names,"max_total_charge_usd":cfg["max_total_charge_usd"],
            "enabled":cfg.get("enabled") is True,"actor_runs_launched":0}
def verified_dataset_count(metadata:dict, max_items:int, source:str)->int:
    """Fail closed on source outputs exceeding the paid request before continuing."""
    count=metadata.get("itemCount") if isinstance(metadata,dict) else None
    if type(max_items) is not int or max_items<1 or type(count) is not int or count<0:
        raise ValueError(source+": missing or invalid completed dataset item count")
    if count>max_items:
        raise ValueError(source+": dataset count "+str(count)+" exceeds requested cap "+str(max_items))
    return count

def run(cfg, token, *, getter=api, sleep=time.sleep):
    if not cfg.get("enabled") or os.getenv("BA_PAID_REFRESH_APPROVAL")!="EXPLICIT_BA_REFRESH_APPROVED":
        raise RuntimeError("BA acquisition disabled or not separately authorised")
    if cfg.get("rolling_coverage_enabled") is not True:
        raise RuntimeError("Rolling 22-family retention not ready; do not buy partial replacement snapshots")
    from scripts.ba_acquisition_planner import role_queries
    approved={item["family"] for item in role_queries()}
    families=[source.get("query_family") for source in cfg["sources"]]
    if cfg.get("rotation_slot") not in range(1,10) or len(set(families))!=5 or not set(families)<=approved:
        raise RuntimeError("Unplanned or repeated family acquisition rejected")
    if not token:raise RuntimeError("APIFY_TOKEN missing")
    remaining=cfg["max_total_charge_usd"]
    receipts=[]
    for source in cfg["sources"]:
        # Recheck fresh account usage immediately before each POST.
        account=getter(BASE+"users/me/limits",token)
        limit=(account.get("limits") or {}).get("maxMonthlyUsageUsd")
        used=(account.get("current") or {}).get("monthlyUsageUsd")
        if type(limit) not in (int,float) or abs(limit-25)>1e-5 or type(used) not in (int,float) or not 0<=used<=limit:
            raise RuntimeError("Apify $25 account hard limit not independently verified")
        if limit-used+1e-9 < cfg["salesforce_reserve_usd"]+remaining:
            raise RuntimeError("Insufficient headroom for outstanding caps")
        max_items=source["max_items"]
        uri=BASE+"acts/"+source["actor"].replace("/","~")+"/runs?"+urlencode({
            "maxItems":max_items,"maxTotalChargeUsd":f'{source["max_charge_usd"]:.2f}',
            "timeout":150,"restartOnError":"false"})
        item=getter(uri,token,source["input"])
        rid=item.get("id")
        if not isinstance(rid,str) or not rid.isalnum():raise RuntimeError("Missing Actor ID; no more runs")
        receipt={"source":source["name"],"actor":source["actor"],"run_id":rid,"attempted":True,
                 "query_family":source.get("query_family"),"requested_items":max_items,
                 "status":"STARTED","max_charge_usd":source["max_charge_usd"],"dataset_id":None}
        receipts.append(receipt)
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps({"schema":"ba-source-run-receipts/v1","receipts":receipts,
                  "publication_approved":False},indent=2)+"\n",encoding="utf8")
        for _ in range(35):
            state=getter(BASE+"actor-runs/"+rid,token)
            if state.get("status") in TERMINAL:
                receipt["status"]=state["status"]
                receipt["dataset_id"]=state.get("defaultDatasetId")
                break
            sleep(6)
        # Record terminal status even for failure; never retry a failed Actor.
        OUT.write_text(json.dumps({"schema":"ba-source-run-receipts/v1",
            "receipts":receipts,"publication_approved":False},indent=2)+"\n",encoding="utf8")
        if receipt["status"]!="SUCCEEDED" or not receipt["dataset_id"]:
            raise RuntimeError("BA source failed or timed out: "+source["name"]+"; no retry")
        # Important: JobServe previously emitted 24 rows despite maxResults=20.
        # Check actual post-run dataset metadata BEFORE launching the next paid Actor.
        try:
            meta=getter(BASE+"datasets/"+receipt["dataset_id"],token)
            receipt["dataset_items"]=verified_dataset_count(meta,max_items,source["name"])
        except (ValueError,TypeError,RuntimeError) as exc:
            receipt["status"]="OUTPUT_COUNT_REJECTED"
            receipt["count_validation_error"]=str(exc)[:220]
            OUT.write_text(json.dumps({"schema":"ba-source-run-receipts/v1",
                "receipts":receipts,"publication_approved":False},indent=2)+"\n",encoding="utf8")
            raise RuntimeError("BA dataset count fails closed before next Actor; no retry: "+str(exc)) from exc
        OUT.write_text(json.dumps({"schema":"ba-source-run-receipts/v1",
            "receipts":receipts,"publication_approved":False},indent=2)+"\n",encoding="utf8")
        remaining=round(remaining-source["max_charge_usd"],2)
    OUT.write_text(json.dumps({"schema":"ba-source-run-receipts/v1","receipts":receipts,
         "publication_approved":False},indent=2)+"\n",encoding="utf8")
    return receipts
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--execute",action="store_true")
    args=parser.parse_args()
    cfg=json.loads(CONFIG.read_text(encoding="utf8"))
    print(json.dumps(validate(cfg),sort_keys=True),flush=True)
    if args.execute:run(cfg,os.getenv("APIFY_TOKEN",""))
if __name__=="__main__":main()
