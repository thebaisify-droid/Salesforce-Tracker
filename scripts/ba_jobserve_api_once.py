"""One explicitly authorised JobServe recovery using Apify REST API, not MCP.

GitHub-only, one launch maximum. Does not modify Salesforce, source tasks,
WordPress or existing BA snapshots. No retries on failure.
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

BASE = "https://api.apify.com/v2/"
ACTOR = "solidcode~jobserve-scraper"
APPROVAL = "AUTHORISE_BA_JOBSERVE_API_RECOVERY_050_20_ONCE"
CAP_USD = 0.50
ROWS = 20
RESERVE = 8.0
ACCOUNT_LIMIT = 19.0
OUTPUT = Path("business-analysis-tracker/evidence/jobserve-api-recovery-result.json")

def api(path, token, body=None):
    if not path.startswith(BASE):
        raise RuntimeError("Untrusted API URL")
    req = Request(path,
        data=json.dumps(body).encode() if body is not None else None,
        method="POST" if body is not None else "GET",
        headers={"Authorization":"Bearer "+token,"Accept":"application/json",
                 **({"Content-Type":"application/json"} if body is not None else {})})
    try:
        with urlopen(req, timeout=30) as response:
            result=json.load(response)
    except HTTPError as error:
        raise RuntimeError("Provider HTTP "+str(error.code)) from None
    except (URLError, ValueError, TimeoutError):
        raise RuntimeError("Provider API unavailable") from None
    if not isinstance(result,dict) or not isinstance(result.get("data"),dict):
        raise RuntimeError("Provider API response invalid")
    return result["data"]

def billing(data):
    upper=(data.get("limits") or {}).get("maxMonthlyUsageUsd")
    used=(data.get("current") or {}).get("monthlyUsageUsd")
    if type(upper) not in (int,float) or type(used) not in (int,float):
        raise RuntimeError("Account usage missing")
    if abs(upper-ACCOUNT_LIMIT)>0.00001 or used<0 or used>upper:
        raise RuntimeError("Account ceiling changed or usage invalid")
    remaining=upper-used
    if remaining + 1e-9 < RESERVE + CAP_USD:
        raise RuntimeError("Insufficient protected headroom for $0.50 one-off")
    return {"account_limit_usd":upper,"account_usage_before_usd":round(used,4),
            "headroom_before_usd":round(remaining,4),
            "protected_salesforce_reserve_usd":RESERVE,
            "maximum_request_usd":CAP_USD}

def input_record():
    return {"keywords":["business analyst"],"country":"gb",
            "maxResults":ROWS,"includeDescription":True,"onlyUniqueJobs":True}

def safe_write(record):
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf8")

def main():
    if os.getenv("BA_JOBSERVE_APPROVAL")!=APPROVAL or os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        raise SystemExit("Not authorised for this one-time execution")
    if os.getenv("GITHUB_EVENT_NAME")!="push":
        raise SystemExit("Only release's one-time push trigger authorised")
    if os.getenv("GITHUB_REF")!="refs/heads/main":
        raise SystemExit("Must run on main")
    token=os.getenv("APIFY_TOKEN")
    if not token:
        raise SystemExit("Missing token; no Actor launched")
    # Check billing before the only permitted POST.
    before=billing(api(BASE+"users/me/limits",token))
    print(json.dumps({"event":"billing_preflight_ok",**before}),flush=True)
    url=BASE+"acts/"+ACTOR+"/runs?"+urlencode({
        "maxItems":ROWS,"maxTotalChargeUsd":"0.50","timeout":120})
    # There is exactly ONE POST to the Actor launch endpoint in this program.
    launched=api(url,token,input_record())
    run_id=launched.get("id")
    if not isinstance(run_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,100}",run_id):
        raise RuntimeError("Launch returned invalid ID; no second launch")
    receipt={"schema":"ba-jobserve-api-recovery/v1","actor":"solidcode/jobserve-scraper",
             "execution_origin":"API_NOT_MCP","run_id":run_id,
             "requested_max_charge_usd":CAP_USD,"requested_max_items":ROWS,
             "input_max_results":ROWS,"automatic_retries":0,"actor_launches":1,
             "wordpress_published":False,"salesforce_modified":False,
             "source_data_publication_approved":False,"billing_preflight":before,
             "status":"LAUNCHED"}
    safe_write(receipt)
    for _ in range(24):
        status=api(BASE+"actor-runs/"+run_id,token)
        state=status.get("status")
        if state in ("SUCCEEDED","FAILED","ABORTED","TIMED-OUT"):
            receipt["status"]=state
            receipt["dataset_id"]=status.get("defaultDatasetId")
            receipt["status_message"]=str(status.get("statusMessage") or "")[:250]
            receipt["finished_at"]=status.get("finishedAt")
            safe_write(receipt)
            print(json.dumps({"event":"terminal","run_id":run_id,"status":state,
                              "dataset_id":receipt["dataset_id"],
                              "publication":False}),flush=True)
            return 0 if state=="SUCCEEDED" else 2
        if state not in ("READY","RUNNING","ABORTING","TIMING-OUT"):
            raise RuntimeError("Unexpected status; do not launch again")
        time.sleep(6)
    receipt["status"]="OBSERVATION_TIMEOUT_NO_RETRY"
    safe_write(receipt)
    raise SystemExit("Actor not terminal within bounded observation; no retry")

if __name__=="__main__":
    raise SystemExit(main())
