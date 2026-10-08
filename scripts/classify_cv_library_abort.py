"""Read-only diagnosis using safe boolean signals, without exporting raw logs."""
import json
import os
import re
from urllib.request import Request, urlopen
RUN="vYVznbV67JxKMBqbo"
PATTERNS={
"charge_cap":r"maxTotalChargeUsd|maximum.{0,35}charge|charge.{0,25}limit|cost.{0,25}limit|spending.{0,25}limit",
"invalid_input":r"invalid.{0,20}input|input.{0,20}validat|schema.{0,20}error|required.{0,20}field",
"manual_abort":r"abort.{0,30}(user|manually|request)|user.{0,30}abort",
"timeout":r"timeout|timed out|exceeded.{0,20}time",
"proxy_network":r"proxy.{0,20}error|network.{0,20}error|captcha|blocked",
}
def classify(meta, log):
    data=meta.get("data",{})
    if data.get("id")!=RUN: raise ValueError("Run identity mismatch")
    status=str(data.get("statusMessage") or "")
    signals={k:{"status":bool(re.search(p,status,re.I)),
                 "log":bool(re.search(p,log,re.I))} for k,p in PATTERNS.items()}
    positives=[k for k,v in signals.items() if v["status"] or v["log"]]
    diagnosis=positives[0] if len(positives)==1 else "ambiguous_or_no_explicit_signal"
    return {"run_id":RUN,"status":data.get("status"),"signals":signals,
            "diagnosis_signal":diagnosis,"definitive_cause_confirmed":len(positives)==1,
            "raw_log_included":False,"raw_status_message_included":False,
            "actor_runs_started":0,"note":"A single matching signal supports diagnosis but still requires interpreting Apify run billing semantics."}
def fetch(url,token,plain=False):
    req=Request(url,method="GET",headers={"Authorization":"Bearer "+token})
    with urlopen(req,timeout=50) as r:
        return r.read(300000).decode("utf-8","replace") if plain else json.load(r)
def main():
    token=os.environ.get("APIFY_TOKEN")
    if not token: raise ValueError("APIFY_TOKEN missing")
    meta=fetch("https://api.apify.com/v2/actor-runs/"+RUN,token)
    log=fetch("https://api.apify.com/v2/logs/"+RUN,token,True)
    report=classify(meta,log)
    with open("cv-library-abort-signals.json","w") as fh: json.dump(report,fh,indent=2)
    print(json.dumps(report))
if __name__=="__main__":main()
