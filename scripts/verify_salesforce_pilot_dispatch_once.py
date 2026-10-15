"""Fail closed if this single-use paid workflow has been dispatched before.

Read-only GitHub metadata query. Prevents a second workflow_dispatch and retries.
"""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen

def verify_once(*, get=None):
    if os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise RuntimeError("Reruns are not permitted for the paid one-time pilot")
    repo=os.getenv("GITHUB_REPOSITORY","")
    run=os.getenv("GITHUB_RUN_ID","")
    token=os.getenv("GITHUB_TOKEN","")
    if repo!="thebaisify-droid/Salesforce-Tracker" or not run.isdigit() or not token:
        raise RuntimeError("Unexpected GitHub execution or missing credentials")
    path="https://api.github.com/repos/"+repo+"/actions/workflows/salesforce-five-source-once.yml/runs?event=workflow_dispatch&per_page=100"
    if get is None:
        request=Request(path,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json"})
        with urlopen(request,timeout=20) as response:
            payload=json.load(response)
    else:
        payload=get(path)
    runs=payload.get("workflow_runs")
    if not isinstance(runs,list):
        raise RuntimeError("GitHub workflow history unavailable")
    if any(str(x.get("id"))!=run for x in runs if isinstance(x,dict)):
        raise RuntimeError("One-time pilot was already dispatched; no paid retry")
    if not any(str(x.get("id"))==run for x in runs if isinstance(x,dict)):
        raise RuntimeError("Current workflow run not visible; fail closed")
    print(json.dumps({"one_time_execution":True,"run_id":run,"prior_dispatch_count":0}))

if __name__=="__main__":
    verify_once()
