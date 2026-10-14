"""One-time, manually authorised UK Salesforce Apify pilot. NEVER publishes.

Exactly five source attempts, each charged at most its configured Apify cap.
Stop at first failure, no retries; no production database or WordPress writes.
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from scripts.plan_salesforce_five_source_pilot import SOURCES, TOTAL_CAP

BASE = "https://api.apify.com/v2/"
APPROVAL = "AUTHORISE_SALESFORCE_FIVE_SOURCE_090_ONCE"
RESERVE = 8.0
MAX_RESULTS = 20
OUTPUT = Path("salesforce-five-source-pilot-evidence.json")


def api(path, token, body=None):
    if not path.startswith(BASE):
        raise ValueError("Apify endpoint is invalid")
    req = Request(path, method="POST" if body is not None else "GET",
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={"Authorization": "Bearer " + token, "Accept": "application/json",
                           **({"Content-Type": "application/json"} if body is not None else {})})
    try:
        with urlopen(req, timeout=45) as res:
            result = json.load(res)
    except HTTPError as exc:
        # Never echo raw response, input payloads, or bearer tokens.
        raise RuntimeError("Apify request refused (HTTP %d)" % exc.code) from None
    if not isinstance(result, dict) or not isinstance(result.get("data"), dict):
        raise RuntimeError("Unexpected Apify metadata or run response")
    return result["data"]


def account_headroom(token, get=api):
    data = get(BASE + "users/me/limits", token)
    limit = data.get("limits", {}).get("maxMonthlyUsageUsd")
    usage = data.get("current", {}).get("monthlyUsageUsd")
    if type(limit) not in (float, int) or type(usage) not in (float, int):
        raise RuntimeError("Billing cap or usage unavailable")
    if abs(limit - 19.0) > 0.0001 or usage < 0 or usage > limit:
        raise RuntimeError("Unexpected account limit or billing usage")
    return round(limit - usage, 4)


def task_input(source, value):
    if not isinstance(value, dict):
        raise RuntimeError("Task input is not an object")
    out = dict(value)
    if source == "CV-Library":
        if not isinstance(out.get("query"), str) or "maxResults" not in out:
            raise RuntimeError("CV-Library Task schema not verified")
        out["query"] = "Salesforce"
        out["maxResults"] = MAX_RESULTS
    elif source == "Totaljobs":
        if not isinstance(out.get("keywords"), (str, list)) or "maxListings" not in out:
            raise RuntimeError("Totaljobs Task schema not verified")
        out["keywords"] = "Salesforce" if isinstance(out["keywords"], str) else ["Salesforce"]
        out["maxListings"] = MAX_RESULTS
    elif source == "Reed UK":
        if not isinstance(out.get("keywords"), (str, list)) or "maxResults" not in out:
            raise RuntimeError("Reed Task schema not verified")
        out["keywords"] = "Salesforce" if isinstance(out["keywords"], str) else ["Salesforce"]
        out["maxResults"] = MAX_RESULTS
    else:
        raise RuntimeError("Unexpected source")
    return out


def actor_input(source):
    if source == "Indeed UK":
        return {"query": "Salesforce", "country": "uk", "maxResults": MAX_RESULTS}
    if source == "JobServe":
        return {"keywords": ["salesforce"], "location": "", "country": "gb",
                "distance": "50", "startUrls": [], "jobType": "", "industries": [],
                "postedSince": "", "remoteOnly": False, "advertisedBy": "",
                "includeDescription": True, "onlyUniqueJobs": True,
                "maxResults": MAX_RESULTS}
    raise RuntimeError("Unexpected source")


def load_task_input(reference, token):
    path = BASE + "actor-tasks/" + quote(reference.replace("/", "~"), safe="~") + "/input"
    req = Request(path, headers={"Authorization": "Bearer " + token,
                                 "Accept": "application/json"}, method="GET")
    with urlopen(req, timeout=35) as res:
        data = json.load(res)
    if not isinstance(data, dict):
        raise RuntimeError("Saved Task input is not a JSON object")
    return data.get("data") if set(data) == {"data"} and isinstance(data["data"], dict) else data


def start_url(kind, reference, cap):
    group = "actor-tasks" if kind == "apify_task" else "acts"
    return BASE + group + "/" + quote(reference.replace("/", "~"), safe="~") + "/runs?" + urlencode({
        "maxItems": MAX_RESULTS, "maxTotalChargeUsd": "%.2f" % cap})


def poll_run(run_id, token):
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9]+", run_id):
        raise RuntimeError("Invalid Apify run identifier")
    # GET-only poll; never retries failed Actor execution.
    for _ in range(45):
        data = api(BASE + "actor-runs/" + run_id, token)
        status = data.get("status")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            return status
        if status not in ("READY", "RUNNING", "ABORTING"):
            raise RuntimeError("Unexpected run status")
        time.sleep(10)
    raise RuntimeError("Actor still running after bounded observation window; stop further launches")


def run(token, approval, *, get=api, load=load_task_input, launch=None, wait=poll_run):
    if approval != APPROVAL or not token:
        raise RuntimeError("Explicit single-use pilot approval and APIFY_TOKEN required")
    results = []
    pending = TOTAL_CAP
    launch = launch or api
    for name, kind, ref, cap, count in SOURCES:
        if count != MAX_RESULTS:
            raise RuntimeError("Pilot plan changed unexpectedly")
        headroom = account_headroom(token, get)
        if headroom + 1e-8 < RESERVE + pending:
            raise RuntimeError("Account headroom does not preserve $8 reserve and remaining pilot caps")
        if kind == "apify_task":
            payload = task_input(name, load(ref, token))
        else:
            payload = actor_input(name)
        result = launch(start_url(kind, ref, cap), token, payload)
        run_id = result.get("id")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("Provider did not return run ID; no further sources attempted")
        status = wait(run_id, token)
        results.append({"source": name, "run_id": run_id, "status": status,
                        "max_charge_usd": cap, "result_limit": MAX_RESULTS})
        print(json.dumps({"source": name, "status": status, "run_id": run_id,
                          "publication_enabled": False}), flush=True)
        if status != "SUCCEEDED":
            raise RuntimeError(name + " did not succeed; remaining sources cancelled")
        pending = round(pending - cap, 2)
    return {"schema": "salesforce-five-source-pilot-evidence/v1",
            "runs": results, "max_total_charge_usd": TOTAL_CAP,
            "wordpress_published": False, "dashboard_unchanged": True,
            "automatic_retries": 0,
            "source_data_not_yet_qa_approved": True}


def main():
    if os.getenv("PILOT_APPROVAL") != APPROVAL:
        raise SystemExit("Pilot authorization string absent or incorrect")
    token = os.getenv("APIFY_TOKEN", "")
    if not token:
        raise SystemExit("APIFY_TOKEN absent")
    result = run(token, os.environ["PILOT_APPROVAL"])
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"complete": True, "runs": len(result["runs"]),
                      "max_total_charge_usd": TOTAL_CAP, "publication": False}))


if __name__ == "__main__":
    main()
