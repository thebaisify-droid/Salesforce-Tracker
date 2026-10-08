"""Read-only audit of Apify run metadata during failed pilot window."""
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL="https://api.apify.com/v2/actor-tasks/develop_ify~cv-library-scraper-task/runs"
START=datetime.fromisoformat("2026-10-08T15:31:00+00:00")
END=datetime.fromisoformat("2026-10-08T15:36:00+00:00")

def summarise(data):
    items=data.get("data",{}).get("items")
    if not isinstance(items,list): raise ValueError("Unexpected Apify response")
    matches=[]
    for item in items:
        try:
            dt=datetime.fromisoformat(item["startedAt"].replace("Z","+00:00"))
        except (ValueError,KeyError,TypeError,AttributeError):
            continue
        if START <= dt <= END:
            usage=item.get("usageTotalUsd")
            matches.append({
                "run_id":item.get("id"),
                "status":item.get("status"),
                "started_at":item.get("startedAt"),
                "finished_at":item.get("finishedAt"),
                "usage_total_usd":usage if type(usage) in (int,float) else None
            })
    return {"schema":"candidate-failed-run-audit/v1","window_utc":[START.isoformat(),END.isoformat()],
            "matching_runs":matches,"run_count":len(matches),
            "actual_billing_attributed":False,
            "note":"Apify run usage is informational and may differ from finalized billing; compare billing records.",
            "actor_runs_started":0}

def main():
    token=os.environ.get("APIFY_TOKEN")
    if not token: raise ValueError("APIFY_TOKEN missing")
    query=urlencode({"limit":100,"desc":1,"startedAfter":START.isoformat(),
                    "startedBefore":END.isoformat()})
    req=Request(URL+"?"+query,method="GET",headers={"Authorization":"Bearer "+token,
                                                    "Accept":"application/json"})
    with urlopen(req,timeout=45) as resp:
        result=summarise(json.load(resp))
    with open("failed-pilot-run-audit.json","w",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
    print(json.dumps({"matching_runs":result["run_count"],"actor_runs_started":0}))
if __name__=="__main__":main()
