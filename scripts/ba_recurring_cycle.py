"""Independent BA scheduled source collection -> QA -> atomic WordPress receiver.

Disabled until recurring spend is explicitly approved and the config is enabled.
Never touches Salesforce jobs/tasks or WordPress page content directly.
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.ba_controlled_refresh import run as acquire_once, validate as validate_acquisition, CONFIG as ACQ_CONFIG, OUT as RECEIPTS_FILE
from scripts.ba_acquisition_planner import select_slot
from scripts.ba_completed_dataset_handoff import build_batch
from scripts.ba_e2e_offline import run_offline
from scripts.ba_stage_five_source_data import MAPPING
from scripts.ba_atomic_snapshot_sender import send_once
from scripts.ba_wordpress_delivery_package import preflight
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT = Path(__file__).resolve().parents[1]
LONDON = ZoneInfo("Europe/London")
EXPECTED = {"CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe"}
MONTHLY_CEILING = 17.00
MAX_SLOTS_MONTHLY = 9
PER_RUN_CEILING = 1.80

def scheduled_slot(now: datetime, *, requested=True) -> dict:
    """Two UTC crons cover daylight saving; only one local 07:35 slot is due."""
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Timezone-aware current time required")
    local = now.astimezone(LONDON)
    if local.weekday() not in (1, 4) or local.hour != 7 or not 30 <= local.minute <= 59:
        return {"due": False, "reason": "NOT_TUE_FRIDAY_0730_UK", "month_slots": 0}
    days = [date(local.year, local.month, i)
            for i in range(1, local.day + 1)]
    slots = sum(d.weekday() in (1, 4) for d in days)
    if slots > MAX_SLOTS_MONTHLY:
        return {"due": False, "reason": "MONTHLY_SLOT_CAP", "month_slots": slots}
    return {"due": True, "reason": "UK_TUE_FRIDAY_SLOT", "month_slots": slots}

def build_live_document(batch: dict, result: dict, now: datetime) -> dict:
    sources = batch.get("sources", [])
    if len(sources) != 5 or {x.get("name") for x in sources} != EXPECTED:
        raise ValueError("Five distinct board receipts required")
    statuses = [{"source":x.get("name"), "attempted":x.get("attempted"),
                 "status":x.get("status")} for x in sources]
    gate = validate_run_receipts(statuses, qa_passed=True)
    if not gate["publish_fresh_five_source_snapshot"]:
        raise ValueError("Incomplete five-source refresh")
    if result.get("status") != "DRY_RUN_PASS_NOT_PUBLISHED":
        raise ValueError("BA source QA failed")
    records = result.get("candidate",{}).get("records",[])
    if not records:
        raise ValueError("No qualified adverts; keep last snapshot")
    verified=preflight(result["candidate"], statuses)
    if not verified["valid_for_wordpress_delivery"]:
        raise ValueError("WordPress publication gate failed")
    by_source={r["name"]:r for r in sources}
    seen_ids=set()
    normalized=[]
    for record in records:
        r=dict(record)
        source=r.get("source")
        receipt=by_source.get(source)
        if (not receipt or r.get("source_run_id")!=receipt["run_id"]
                or r.get("dataset_id")!=receipt["dataset_id"]):
            raise ValueError("Cross-run provenance mismatch")
        if r.get("id") in seen_ids:
            raise ValueError("Duplicate canonical record ID")
        seen_ids.add(r["id"])
        r["job_source"]=source
        r["original_advert_url"]=r["url"]
        r["source_observed_only"]=True
        normalized.append(r)
    end_times = []
    for source in sources:
        stamp=source.get("observed_at")
        if not isinstance(stamp,str):
            raise ValueError("Missing source observation time")
        ts=datetime.fromisoformat(stamp.replace("Z","+00:00"))
        if ts.tzinfo is None or ts > now + timedelta(minutes=15) or ts < now-timedelta(hours=36):
            raise ValueError("Stale/future observation; cannot publish")
        end_times.append(ts)
    completed=max(end_times)
    return {
        "schema":"ba-live-snapshot/v1",
        "refresh":{"status":"success",
                   "finished_at":completed.isoformat().replace("+00:00","Z"),
                   "type":"CONTROLLED_FIVE_SOURCE_REFRESH",
                   "source_observed_not_employer_confirmed":True},
        "quality":{"passed":True,"matched_advertisements":len(normalized),
                   "excluded":sum(result.get("rejected",{}).values()),
                   "potential_duplicate_rows":sum(bool(r.get("potential_duplicate")) for r in normalized),
                   "independently_confirmed_open":False},
        "sources":[{"source":s["name"],"status":"SUCCEEDED","attempted":True,
                    "run_id":s["run_id"],"dataset_id":s["dataset_id"]}
                   for s in sources],
        "records":normalized,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scheduled",action="store_true")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    cfg=json.loads(ACQ_CONFIG.read_text(encoding="utf8"))
    valid=validate_acquisition(cfg)
    now=datetime.now(timezone.utc)
    if not args.execute:
        print(json.dumps({"status":"READ_ONLY_CONFIG_PREFLIGHT",
            "enabled":cfg["enabled"],"proposed_per_run_usd":cfg["max_total_charge_usd"],
            "scheduled_slot":scheduled_slot(now),"actors_started":0,"snapshots_sent":0}))
        return
    if (not cfg.get("enabled") or not cfg.get("paid_acquisition_enabled")
        or not cfg.get("scheduling_enabled")
        or not cfg.get("recurring_budget_approved")
        or not cfg.get("pricing_guard_verified")
        or cfg.get("max_total_charge_usd")!=PER_RUN_CEILING
        or cfg.get("monthly_ba_allowance_usd")!=MONTHLY_CEILING
        or cfg.get("max_scheduled_runs_per_month")!=MAX_SLOTS_MONTHLY):
        raise SystemExit("Recurring BA budget or pricing controls not fully authorised")
    if cfg.get("rolling_coverage_enabled") is not True:
        raise SystemExit("22-family rolling snapshot retention is not ready; no paid acquisition")
    if os.getenv("BA_PAID_REFRESH_APPROVAL")!="EXPLICIT_BA_REFRESH_APPROVED":
        raise SystemExit("Scheduled acquisition approval missing")
    if not args.scheduled or os.getenv("GITHUB_EVENT_NAME")!="schedule" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        raise SystemExit("Paid BA acquisition is only allowed from the first scheduled GitHub attempt")
    if args.scheduled:
        slot=scheduled_slot(now)
        if not slot["due"]:
            print(json.dumps({"status":"NOT_DUE_NO_COST",**slot}))
            return
    if args.publish and (not cfg.get("wordpress_delivery_enabled")
        or os.getenv("BA_WP_DELIVERY_APPROVAL")!="EXPLICIT_APPROVAL"):
        raise SystemExit("Independent WordPress delivery approval missing")
    # Fresh per-Actor pricing inspection before any paid Actor API POST.
    # PRICE_PER_DATASET_ITEM must fit maxItems; PPE uses maxTotalChargeUsd.
    from scripts.ba_pricing_readonly import check as inspect_prices, validate_cost_models
    report=inspect_prices(cfg,os.getenv("APIFY_TOKEN",""))
    active_plan=select_slot(cfg,slot["month_slots"],report)
    price_status=validate_cost_models(report,active_plan)
    if not price_status["pricing_guard_passed"]:
        raise SystemExit("Actor pricing safeguards not proven: "+repr(price_status["issues"]))
    if report["available_after_salesforce_reserve_usd"] + 1e-9 < PER_RUN_CEILING:
        raise SystemExit("Insufficient account balance after the protected Salesforce reserve")
    # Acquisition itself is bounded by separate per-source limits, account
    # headroom checks and a shared concurrency group with the Salesforce workflow.
    receipts=acquire_once(active_plan,os.getenv("APIFY_TOKEN",""))
    # No Actor retries and no historical run substitutions.
    from urllib.request import Request,urlopen
    def getter(path,token):
        req=Request(path,headers={"Authorization":"Bearer "+token,
                    "Accept":"application/json"},method="GET")
        with urlopen(req,timeout=35) as response:
            data=json.load(response)
        if "/items?" in path:
            if not isinstance(data,list):
                raise ValueError("Dataset response not a list")
            return data
        if not isinstance(data,dict) or not isinstance(data.get("data"),dict):
            raise ValueError("Invalid Apify metadata envelope")
        return data["data"]
    batch=build_batch(receipts,os.getenv("APIFY_TOKEN",""),get=getter,max_per_source=50)
    by_name={source["name"]:source for source in active_plan["sources"]}
    if any(len(source["records"])>by_name[source["name"]]["max_items"] for source in batch["sources"]):
        raise ValueError("Actor returned more than its authorised requested items; do not publish")
    result=run_offline(batch,json.loads(MAPPING.read_text(encoding="utf8")))
    live=build_live_document(batch,result,datetime.now(timezone.utc))
    print(json.dumps({"status":"FIVE_SOURCES_QA_PASSED","source_advertisements":len(live["records"]),
        "delivery_enabled":args.publish,"source_observed_not_confirmed":True}))
    if args.publish:
        ack=send_once(live,os.getenv("BA_WP_USERNAME",""),
                      os.getenv("BA_WP_APPLICATION_PASSWORD",""),approved=True)
        if ack.get("records")!=len(live["records"]):
            raise ValueError("Receiver record count mismatch")
        print(json.dumps({"status":"PUBLISHED_RECEIVER_CONFIRMED",
            "records":ack["records"],"sha256":ack["sha256"]}))

if __name__=="__main__":
    main()
