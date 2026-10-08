"""Classify the historical abort cause from explicit Apify status text (GET only)."""
import json,os,re
from urllib.request import Request,urlopen
RUN="vYVznbV67JxKMBqbo"
URL="https://api.apify.com/v2/actor-runs/"+RUN
RULES={
 "MAX_TOTAL_CHARGE":r"maxTotalChargeUsd|maximum.{0,40}charge|maximum.{0,40}cost|charge.{0,30}limit|maximum.{0,40}spend",
 "USER_ABORT":r"abort(?:ed)? by user|user.{0,20}abort|manually.{0,20}abort",
 "INPUT_VALIDATION":r"input.{0,25}validat|invalid.{0,20}input|missing.{0,15}required",
 "TIMEOUT":r"timed out|timeout|time limit",
 "OUT_OF_MEMORY":r"out of memory|memory limit"
}
def evaluate(data):
 d=data.get("data",{})
 if d.get("id")!=RUN: raise ValueError("wrong Actor run")
 msg=d.get("statusMessage")
 matches=[k for k,p in RULES.items() if isinstance(msg,str) and re.search(p,msg,re.I)]
 return {"run_id":RUN,"status":d.get("status"),
 "status_message_present":bool(msg),"explicit_reason_codes":matches,
 "unambiguous_status_reason":matches[0] if len(matches)==1 else None,
 "exit_code":d.get("exitCode"),"usage_total_usd":d.get("usageTotalUsd"),
 "aborted_at":d.get("finishedAt"),"raw_status_message_included":False,
 "raw_log_included":False,"runs_launched":0,
 "attribution_confirmed":False,
 "note":"Absence of a recognized explicit phrase does not establish the abort initiator."}
def main():
 token=os.getenv("APIFY_TOKEN")
 if not token: raise ValueError("APIFY_TOKEN unavailable")
 req=Request(URL,method="GET",headers={"Authorization":"Bearer "+token})
 with urlopen(req,timeout=40) as f: out=evaluate(json.load(f))
 with open("cv-library-abort-reason.json","w") as f:json.dump(out,f,indent=2)
 print(json.dumps(out))
if __name__=="__main__":main()
