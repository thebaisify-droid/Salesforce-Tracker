"""Read-only investigation of second CV-Library pilot; sanitized metadata only."""
import json,os,re
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
START=datetime.fromisoformat("2026-10-08T16:34:00+00:00")
END=datetime.fromisoformat("2026-10-08T16:40:00+00:00")
BASE="https://api.apify.com/v2/"
TASK="actor-tasks/develop_ify~cv-library-scraper-task/runs"
def classify(message):
    s=str(message or "")
    patterns={"MAX_TOTAL_CHARGE":r"maxTotalChargeUsd|maximum.{0,40}charge|charge.{0,30}limit|maximum.{0,40}cost",
    "INPUT_ERROR":r"invalid.{0,20}input|input.{0,20}validat|missing.{0,20}required",
    "USER_ABORT":r"abort.{0,20}by user|manually.{0,20}abort",
    "TIMEOUT":r"timeout|timed out"}
    return [key for key,pat in patterns.items() if re.search(pat,s,re.I)]
def audit(items,details):
    matched=[]
    for x in items:
        try: ts=datetime.fromisoformat(x["startedAt"].replace("Z","+00:00"))
        except (KeyError,ValueError,TypeError,AttributeError):continue
        if not START<=ts<=END:continue
        d=details.get(x.get("id"),{})
        r=d.get("data",{})
        cap=r.get("options",{}).get("maxTotalChargeUsd")
        matched.append({"run_id":x.get("id"),"started_at":x.get("startedAt"),
        "finished_at":r.get("finishedAt"),"status":r.get("status"),
        "run_cap_usd":cap if type(cap) in (int,float) else None,
        "usage_total_usd":r.get("usageTotalUsd"),"reason_signals":classify(r.get("statusMessage")),
        "status_message_present":bool(r.get("statusMessage"))})
    return {"window_utc":[START.isoformat(),END.isoformat()],"matching_runs":matched,
    "count":len(matched),"raw_logs_exported":False,"raw_status_messages_exported":False,
    "actor_runs_started":0,"final_billed_amount_confirmed":False}
def main():
    token=os.environ["APIFY_TOKEN"]
    def get(path):
        request=Request(BASE+path,headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
        with urlopen(request,timeout=45) as response:return json.load(response)
    listing=get(TASK+"?"+urlencode({"limit":100,"desc":1,"startedAfter":START.isoformat(),"startedBefore":END.isoformat()}))
    items=listing.get("data",{}).get("items",[])
    if not isinstance(items,list):raise ValueError("Unexpected run listing")
    found={}
    for x in items:
        if x.get("id"):found[x["id"]]=get("actor-runs/"+x["id"])
    result=audit(items,found)
    with open("second-cv-failure-audit.json","w") as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=="__main__":main()
