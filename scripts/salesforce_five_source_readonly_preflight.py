"""Read-only five-source acquisition metadata preflight.

Queries three saved Task definitions and their current Actor metadata via Apify GET.
NEVER starts Actors, modifies Tasks, downloads vacancy records, or publishes.
No Task input values (which can contain credentials) are written or printed.
"""
from __future__ import annotations

import json
import os
from urllib.parse import quote
from urllib.request import Request, urlopen

TASKS = {
    "CV-Library": "develop_ify/cv-library-scraper-task",
    "Totaljobs": "develop_ify/totaljobs-com-scraper-task",
    "Reed UK": "develop_ify/uk-jobs-reed-task",
}
OTHER_ACTORS = {"Indeed UK": "wildorigins~indeed-jobs",
                "JobServe": "solidcode~jobserve-scraper"}
BASE = "https://api.apify.com/v2/"
SECRET_TERMS = ("token", "password", "secret", "cookie", "authorization", "api_key", "apikey")


def fetch(url, token):
    if not url.startswith(BASE):
        raise ValueError("Disallowed API endpoint")
    req = Request(url, method="GET", headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(req, timeout=35) as response:
        data = json.load(response)
    return data["data"]


def inspect(token, get=fetch):
    if not token:
        raise ValueError("APIFY_TOKEN missing")
    tasks = []
    for label, name in TASKS.items():
        url = BASE + "actor-tasks/" + quote(name.replace("/", "~"), safe="~")
        task = get(url, token)
        inp = get(url + "/input", token)
        if not isinstance(task, dict) or not isinstance(inp, dict):
            raise ValueError("Saved Task or input is not an object")
        aid = task.get("actId")
        if not isinstance(aid, str) or not aid:
            raise ValueError("Saved Task Actor ID unavailable")
        actor = get(BASE + "acts/" + quote(aid, safe="~"), token)
        if not isinstance(actor, dict) or actor.get("id") != aid:
            raise ValueError("Actor identity mismatch")
        fields = sorted(k for k in inp if isinstance(k, str)
                        and not any(t in k.lower() for t in SECRET_TERMS))
        tasks.append({"source": label, "task": name, "actor_id": aid,
                      "actor_name": actor.get("name"),
                      "task_input_field_names": fields,
                      "raw_task_input_included": False,
                      "pricing_verified": False,
                      "has_explicit_input_limit_key": any("max" in k.lower() for k in fields)})
    for label, aid in OTHER_ACTORS.items():
        actor = get(BASE + "acts/" + quote(aid, safe="~"), token)
        if not isinstance(actor, dict) or not actor.get("id"):
            raise ValueError("External Actor not found: " + label)
    return {"schema": "salesforce-five-source-readonly-preflight/v1",
            "saved_tasks": tasks, "other_actors_checked": sorted(OTHER_ACTORS),
            "actor_runs_started": 0, "paid_acquisition_approved": False,
            "tasks_mutated": 0, "publication_enabled": False}


def main():
    result = inspect(os.environ.get("APIFY_TOKEN", ""))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
