"""Controlled BA five-source acquisition. DISABLED until separately approved.

API calls happen only after BA_PAID_REFRESH_APPROVAL and explicit --execute. Run
once per source, fail closed, no retries, no WordPress delivery and no Salesforce writes.
"""
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from urllib.parse import urlencode
from scripts.ba_jobserve_api_once import api, billing

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"business-analysis-tracker/config/automated_refresh_pipeline.json"
OUT=ROOT/"business-analysis-tracker/data/acquisition-receipts.json"
BASE="https://api.apify.com/v2/"
TERMINAL={"SUCCEEDED","FAILED","ABORTED","TIMED-OUT"}
def validate(cfg):
    if cfg.get("schema")!="ba-automatic-refresh/v1":raise ValueError("Incorrect schema")
    if cfg.get("monthly_limit_usd")!=19 or cfg.get("salesforce_reserve_usd")!=8:raise ValueError("Budget configuration unsafe")
    if cfg.get("automatic_retries") != 0:
        raise ValueError("Automatic retries are prohibited")
    if cfg.get("publish_automatically") is not cfg.get("wordpress_delivery_enabled"):
        raise ValueError("Publishing requires an identical WordPress delivery approval gate")
    if cfg.get("monthly_ba_allowance_usd") != 11 or cfg.get("max_scheduled_runs_per_month") != 9:
        raise ValueError("BA standing monthly allowance or cadence changed")
    if cfg.get("max_total_charge_usd") != 1.20:
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
        if type(size) is not int or size != 10 or type(value) is not int or value != 10:
            raise ValueError("Source input or result limit changed: " + name)
        cap=source.get("max_charge_usd")
        if type(cap) not in (int, float) or not 0 < cap <= 0.50:
            raise ValueError("Invalid Actor charge cap: " + name)
        if source.get("input",{}).get("incrementalMode",False) is not False:
            raise ValueError("Shared Actor incremental state disallowed")
    if round(sum(x["max_charge_usd"] for x in cfg["sources"]),2) != 1.20:
        raise ValueError("Sum of per-source charge caps differs from authorisation")
    return {"valid":True,"sources":names,"max_total_charge_usd":cfg["max_total_charge_usd"],
            "enabled":cfg.get("enabled") is True,"actor_runs_launched":0}
def run(cfg, token, *, getter=api, sleep=time.sleep):
    if not cfg.get("enabled") or os.getenv("BA_PAID_REFRESH_APPROVAL")!="EXPLICIT_BA_REFRESH_APPROVED":
        raise RuntimeError("BA acquisition disabled or not separately authorised")
    if not token:raise RuntimeError("APIFY_TOKEN missing")
    remaining=cfg["max_total_charge_usd"]
    receipts=[]
    for source in cfg["sources"]:
        # Recheck fresh account usage immediately before each POST.
        status=billing(getter(BASE+"users/me/limits",token))
        if status["headroom_before_usd"]+1e-9 < cfg["salesforce_reserve_usd"]+remaining:
            raise RuntimeError("Insufficient headroom for outstanding caps")
        max_items=source["max_items"]
        uri=BASE+"acts/"+source["actor"].replace("/","~")+"/runs?"+urlencode({
            "maxItems":max_items,"maxTotalChargeUsd":f'{source["max_charge_usd"]:.2f}',"timeout":150})
        item=getter(uri,token,source["input"])
        rid=item.get("id")
        if not isinstance(rid,str) or not rid.isalnum():raise RuntimeError("Missing Actor ID; no more runs")
        receipt={"source":source["name"],"actor":source["actor"],"run_id":rid,"attempted":True,
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
