"""Import existing SUCCEEDED Apify run datasets into isolated, unpublished candidate files.

Read-only Apify API GET calls; NEVER starts an Actor, Task or workflow.
Usage:
 APIFY_TOKEN=... python -m scripts.import_candidate_apify_runs --manifest manifest.json --output-dir data/candidate-apify-review
Manifest format: {"runs":[{"source":"Indeed UK","run_id":"existing-run-id"}]}
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from scripts.import_candidate_exports import load_export

ACTOR_IDS = {"JobServe": "iEeTOwSjZDvAshw7Y"}

SOURCES = {"CV-Library", "Totaljobs", "Indeed UK", "JobServe", "Reed"}
SOURCE_SLUGS = {"CV-Library":"cv-library","Totaljobs":"totaljobs","Indeed UK":"indeed-uk","JobServe":"jobserve","Reed":"reed"}
RUN_ID = re.compile(r"^[A-Za-z0-9_-]{6,100}$")
API = "https://api.apify.com/v2/"
PROTECTED = {"live-data.json", "salesforce_tracker.db", "data.json"}

def get_json(route: str, token: str):
    req = urllib.request.Request(API + route, headers={"Authorization": "Bearer " + token, "Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, ValueError) as exc:
        raise RuntimeError("Apify read-only request failed; no Actor started") from None

def acquire(manifest: dict, output_dir: Path, token: str, getter=get_json):
    runs = manifest.get("runs")
    if not isinstance(runs, list) or not runs or len(runs) > 20:
        raise ValueError("Specify 1-20 previously completed runs")
    if output_dir.name in PROTECTED or any(part in {"dashboard", "candidate-beta"} for part in output_dir.parts):
        raise ValueError("Output must stay outside published dashboard paths")
    results = []
    seen = set()
    # Validate the entire manifest before any provider requests.
    for entry in runs:
        if not isinstance(entry, dict) or entry.get("source") not in SOURCES or not isinstance(entry.get("run_id"), str) or not RUN_ID.fullmatch(entry["run_id"]):
            raise ValueError("Each run needs an approved source and valid run_id")
        if entry["run_id"] in seen:
            raise ValueError("Duplicate run ID")
        seen.add(entry["run_id"])
    for entry in runs:
        source, run_id = entry["source"], entry["run_id"]
        run = getter("actor-runs/" + run_id, token)["data"]
        if run.get("status") != "SUCCEEDED" or not run.get("defaultDatasetId"):
            raise ValueError("Run is not SUCCEEDED or has no dataset: " + run_id)
        if source in ACTOR_IDS and run.get("actId") != ACTOR_IDS[source]:
            raise ValueError("Actor identity mismatch for source: " + source)
        dataset_id = run["defaultDatasetId"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,100}", dataset_id):
            raise ValueError("Unexpected dataset ID")
        # Bounded fetch; require complete output to avoid silent partial ingestion.
        payload = getter("datasets/" + dataset_id + "/items?clean=true&limit=1000", token)
        if not isinstance(payload, list):
            raise ValueError("Unexpected dataset response")
        if len(payload) >= 1000:
            raise ValueError("Dataset at safety limit; require paginated review")
        info = getter("datasets/" + dataset_id, token)["data"]
        if info.get("itemCount") != len(payload):
            raise ValueError("Dataset count mismatch; partial retrieval is not allowed")
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / (SOURCE_SLUGS[source] + "-" + run_id + "-raw.json")
        normalized_path = output_dir / (SOURCE_SLUGS[source] + "-" + run_id + "-candidate.json")
        if raw_path.exists() or normalized_path.exists():
            raise FileExistsError("Existing archive cannot be silently overwritten")
        raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        normalized = load_export(raw_path, source)
        normalized_path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        results.append({"source":source,"run_id":run_id,"dataset_id":dataset_id,
                        "run_started_at":run.get("startedAt"),"run_finished_at":run.get("finishedAt"),
                        "dataset_rows":len(payload),"normalized_rows":len(normalized),
                        "publication_approved":False,"provenance_verified_from_run_api":True})
    return {"schema":"candidate-apify-completed-runs/v1","mode":"read_only_completed_runs",
            "actor_runs_started":0,"publication_approved":False,"results":results}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        parser.error("APIFY_TOKEN required")
    output_dir = Path(args.output_dir).resolve()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    result = acquire(manifest, output_dir, token)
    (output_dir / "import-report.json").write_text(json.dumps(result,indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))

if __name__ == "__main__":
    main()
