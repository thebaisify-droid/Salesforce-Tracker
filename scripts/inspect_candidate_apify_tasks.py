"""Inspect existing Apify saved Task inputs via GET only; never run or update tasks.

Usage: APIFY_TOKEN=... python -m scripts.inspect_candidate_apify_tasks --output /tmp/task-evidence.json
Output contains an allowlisted summary, not raw Task input or credentials.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

TASKS = {"CV-Library": "develop_ify/cv-library-scraper-task",
         "Totaljobs": "develop_ify/totaljobs-com-scraper-task"}
SEARCH_HINTS = ("query", "queries", "keyword", "keywords", "search", "searchterm",
                "what", "location", "where", "country", "maxresults", "maxitems",
                "resultsperpage", "starturls")
SECRET_HINTS = ("token", "secret", "password", "cookie", "authorization", "apikey", "api_key")

def _task_url(task_id):
    return "https://api.apify.com/v2/actor-tasks/" + quote(task_id.replace("/", "~"), safe="~")

def _get(url, token):
    request = Request(url, method="GET",
                      headers={"Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=45) as response:
        return json.load(response)

def summarise(task_id, task_payload, input_payload):
    metadata = task_payload.get("data", task_payload)
    inp = input_payload.get("data", input_payload)
    if not isinstance(metadata, dict) or not isinstance(inp, dict):
        raise ValueError("unexpected task metadata/input format")
    fields = sorted(str(k) for k in inp if not any(s in k.lower() for s in SECRET_HINTS))
    search_fields = [k for k in fields if any(s in k.lower().replace("_", "") for s in SEARCH_HINTS)]
    return {"task_id": task_id, "actor_id": metadata.get("actId"),
            "input_field_names": fields,
            "candidate_search_fields": search_fields,
            "input_schema_verified": False,
            "non_salesforce_search_verified": False,
            "metadata_retrieved": True,
            "raw_input_included": False,
            "note": "Key names alone do not prove that fields are supported or overrideable."}

def inspect(token):
    if not token:
        raise ValueError("APIFY_TOKEN not set")
    results = []
    for source, task in TASKS.items():
        url = _task_url(task)
        meta = _get(url, token)
        task_input = _get(url + "/input", token)
        results.append({"source": source, **summarise(task, meta, task_input)})
    return {"schema": "apify-saved-task-read-only-evidence/v1", "tasks": results,
            "actor_runs_started": 0, "task_updates": 0,
            "paid_acquisition_approved": False}

def main():
    p = argparse.ArgumentParser(description="Read-only redacted Apify Task metadata inspection")
    p.add_argument("--output", required=True)
    args = p.parse_args()
    destination = Path(args.output).resolve()
    if destination in {Path("dashboard/live-data.json").resolve(),
                       Path("dashboard/data.json").resolve(),
                       Path("config/pipeline.json").resolve()}:
        p.error("Cannot overwrite production configuration/data")
    report = inspect(os.environ.get("APIFY_TOKEN", ""))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"tasks_inspected": len(report["tasks"]),
                      "actor_runs_started": 0, "paid_acquisition_approved": False}))

if __name__ == "__main__":
    main()
