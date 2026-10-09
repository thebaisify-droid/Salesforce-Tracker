"""Read *existing* Apify dataset items; never create or run Actors/Tasks.

Explicit dataset ID only. No API calls at import time. This is a manual, offline
evidence intake utility, not a scheduled collector or trusted source validator.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.import_candidate_exports import load_export

DATASET_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

def dataset_url(dataset_id: str, *, limit: int, offset: int = 0) -> str:
    if not DATASET_ID.fullmatch(dataset_id):
        raise ValueError("invalid Apify dataset ID")
    if limit < 1 or limit > 1000 or offset < 0:
        raise ValueError("limit must be 1..1000 and offset nonnegative")
    query = urlencode({"format": "json", "clean": "true", "limit": limit, "offset": offset})
    return f"https://api.apify.com/v2/datasets/{dataset_id}/items?{query}"

def read_existing_dataset(dataset_id: str, token: str, limit: int = 100):
    """Only GET an existing dataset. No run endpoint and no new scrape."""
    if not token:
        raise ValueError("APIFY_TOKEN is required to read the dataset")
    url = dataset_url(dataset_id, limit=limit)
    request = Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, method="GET")
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("dataset returned an unexpected format")
    return payload

def main() -> int:
    p = argparse.ArgumentParser(description="READ ONLY: fetch existing Apify dataset items for offline QA")
    p.add_argument("--dataset-id", required=True, help="Existing dataset ID, not Actor or Task ID")
    p.add_argument("--source", required=True, choices=("CV-Library","Totaljobs","Reed","Indeed UK","JobServe"))
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    dataset_url(args.dataset_id, limit=args.limit)
    target = Path(args.output).resolve()
    protected = {Path("dashboard/live-data.json").resolve(), Path("dashboard/data.json").resolve(),
                 Path("config/pipeline.json").resolve()}
    if target in protected:
        p.error("live production paths cannot be overwritten")
    raw = read_existing_dataset(args.dataset_id, os.environ.get("APIFY_TOKEN",""), args.limit)
    # Convert from a temporary local JSON only; keep existing import mapping canonical.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        source_path = Path(tmp)/"existing.json"
        source_path.write_text(json.dumps(raw), encoding="utf-8")
        normalized = load_export(source_path, args.source)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(normalized, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"existing_dataset": args.dataset_id,"source":args.source,
                      "items_read":len(raw),"records_normalized":len(normalized),
                      "actor_runs_started":0,"dataset_authenticity_reviewed":False,
                      "publication_approved":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
