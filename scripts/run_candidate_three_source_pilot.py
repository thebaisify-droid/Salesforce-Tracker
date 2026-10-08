"""One-off manual UK analyst/security pilot. No production DB or saved Task writes.

Requires explicit --execute AND PILOT_APPROVAL=RUN_CAPPED_PILOT.
Uses hard Apify maxTotalChargeUsd on each run, monthly limit and headroom guards.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from scripts.extract_candidate_evidence import extract

CAPS={"Totaljobs":0.20,"Indeed UK":0.15,"JobServe":0.15}
TASKS={"CV-Library":"develop_ify/cv-library-scraper-task","Totaljobs":"develop_ify/totaljobs-com-scraper-task"}
ACTORS={"Indeed UK":"wildorigins/indeed-jobs","JobServe":"solidcode/jobserve-scraper"}
LIMIT=10
SAFE_RESERVE_FOR_EXISTING_TRACKER=8.00
# The prior CV-Library run aborted at its $0.10 charge cap. Fail closed until
# observed charging and a revised pilot allocation have been separately reviewed.
PAID_PILOT_ENABLED=False
BLOCKED_SOURCE="CV-Library"

def request_json(url,token,*,body=None):
    method="POST" if body is not None else "GET"
    req=Request(url,method=method,headers={"Authorization":"Bearer "+token,
        "Accept":"application/json",**({"Content-Type":"application/json"} if body is not None else {})},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urlopen(req,timeout=660 if body is not None else 45) as response:
            return json.load(response)
    except HTTPError as exc:
        # Log structured provider error type only; never log tokens, inputs or raw messages.
        error_type = "unknown"
        try:
            details = json.loads(exc.read(4096))
            candidate = details.get("error", {}).get("type", "")
            if isinstance(candidate, str) and candidate.isascii() and candidate.replace("_", "").replace("-", "").isalnum():
                error_type = candidate[:80]
        except (ValueError, AttributeError, TypeError):
            pass
        raise RuntimeError(f"Apify HTTP {exc.code}; error_type={error_type}") from None

def remaining_headroom(limits):
    payload=limits.get("data",{})
    maximum=payload.get("limits",{}).get("maxMonthlyUsageUsd")
    used=payload.get("current",{}).get("monthlyUsageUsd")
    if (type(maximum) not in (int,float) or type(used) not in (int,float)
        or maximum>19 or maximum<=0 or used<0 or used>maximum):
        raise ValueError("Account limit/usage missing or exceeds $19; fail closed")
    return round(maximum-used,4)

def task_override(source,existing):
    if not isinstance(existing,dict): raise ValueError("Saved Task input unavailable")
    payload=dict(existing)
    if source=="CV-Library":
        if not isinstance(payload.get("query"),str):
            raise ValueError("CV-Library query field is not a string")
        payload["query"]="business analyst"
        if "maxResults" in payload:
            payload["maxResults"]=min(LIMIT,int(payload["maxResults"]))
    else:
        keywords=payload.get("keywords")
        if isinstance(keywords,str): payload["keywords"]="business analyst"
        elif isinstance(keywords,list): payload["keywords"]=["business analyst"]
        else: raise ValueError("Totaljobs keywords format unrecognised")
        if not payload.get("mode"): raise ValueError("Totaljobs required mode missing")
        if "maxListings" in payload: payload["maxListings"]=min(LIMIT,int(payload["maxListings"]))
    return payload

def make_request(source,token):
    params=urlencode({"format":"json","clean":"true","maxItems":LIMIT,
                      "maxTotalChargeUsd":CAPS[source]})
    if source in TASKS:
        tid=TASKS[source].replace("/","~")
        raw=request_json(f"https://api.apify.com/v2/actor-tasks/{quote(tid,safe='~')}/input",token)
        payload=task_override(source,raw.get("data",raw))
        url=f"https://api.apify.com/v2/actor-tasks/{quote(tid,safe='~')}/run-sync-get-dataset-items?{params}"
    elif source=="Indeed UK":
        payload={"query":"business analyst","country":"uk","maxResults":LIMIT}
        url=f"https://api.apify.com/v2/acts/wildorigins~indeed-jobs/run-sync-get-dataset-items?{params}"
    else:
        payload={"keywords":["business analyst"],"location":"","country":"gb","distance":"50",
                 "startUrls":[],"jobType":"","industries":[],"postedSince":"",
                 "remoteOnly":False,"advertisedBy":"","includeDescription":True,
                 "onlyUniqueJobs":True,"maxResults":LIMIT}
        url=f"https://api.apify.com/v2/acts/solidcode~jobserve-scraper/run-sync-get-dataset-items?{params}"
    return url,payload

def run(*,token,execute,approval,output):
    if not execute or approval!="AUTHORISE_THREE_SOURCE_050_PILOT":
        raise ValueError("Explicit single-run pilot approval required")
    if not PAID_PILOT_ENABLED:
        raise RuntimeError("Revised pilot not enabled")
    if not token: raise ValueError("Missing APIFY_TOKEN")
    results=[]
    remaining_proposed=round(sum(CAPS.values()),2)
    for source in CAPS:
        limits=request_json("https://api.apify.com/v2/users/me/limits",token)
        headroom=remaining_headroom(limits)
        if headroom < SAFE_RESERVE_FOR_EXISTING_TRACKER+remaining_proposed:
            raise RuntimeError("Insufficient headroom after preserving $8 for existing tracker")
        url,payload=make_request(source,token)
        # Output only public vacancy metadata, no raw descriptions or email/phone data.
        print(f"Submitting capped request for {source} (max ${CAPS[source]:.2f}); no retry on failure", flush=True)
        try:
            response=request_json(url,token,body=payload)
        except Exception as exc:
            raise RuntimeError(f"Pilot stopped at {source}: {exc}; other sources not attempted") from None
        if not isinstance(response,list): raise RuntimeError(source+" returned non-list response")
        accepted=[]
        for rec in response[:LIMIT]:
            extracted=extract(rec,source)
            if extracted is not None:
                accepted.append(extracted)
        results.append({"source":source,"max_usd":CAPS[source],"raw_count":len(response),
                        "accepted_count":len(accepted),"vacancies":accepted})
        remaining_proposed=round(remaining_proposed-CAPS[source],2)
    document={"schema":"candidate-pilot-evidence/v1","live_salesforce_unchanged":True,
              "budget_limit_usd":19,"max_reserved_charge_usd":round(sum(CAPS.values()),2),
              "results":results,"publication_approved":False}
    dest=Path(output)
    if dest.resolve() in (Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve()):
        raise ValueError("Live Salesforce output forbidden")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(document,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"sources":[{"source":r["source"],"accepted":r["accepted_count"]} for r in results],
                      "publication_approved":False,"max_reserved_charge_usd":.50}))
    return document

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",default="candidate-pilot-evidence.json")
    args=p.parse_args()
    run(token=os.environ.get("APIFY_TOKEN",""),execute=args.execute,
        approval=os.environ.get("PILOT_APPROVAL",""),output=args.output)
if __name__=="__main__":main()
