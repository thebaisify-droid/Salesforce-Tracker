"""Offline-only candidate ingest and export.

Usage: python -m scripts.stage_candidate_market --input fixtures.json --database data/business_product_delivery_security_candidate.db --batch-id manual-001 --output dashboard/business-product-delivery-security-candidate.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tracker.candidate_store import CandidateStore

def main() -> int:
    parser = argparse.ArgumentParser(description="Stage local candidate records; never invoke Apify")
    parser.add_argument("--input", required=True)
    parser.add_argument("--database", default="data/business_product_delivery_security_candidate.db")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--output", default="dashboard/business-product-delivery-security-candidate.json")
    args = parser.parse_args()

    source = Path(args.input).resolve()
    db = Path(args.database).resolve()
    output = Path(args.output).resolve()
    protected = {Path("dashboard/data.json").resolve(), Path("dashboard/live-data.json").resolve(),
                 Path("data/salesforce_tracker.db").resolve()}
    if len({source, db, output}) != 3 or any(p in protected for p in (db, output)):
        parser.error("candidate paths must be distinct and cannot overwrite Salesforce files")
    raw = json.loads(source.read_text(encoding="utf-8"))
    with CandidateStore(db) as store:
        result = store.ingest(raw, args.batch_id)
        snapshot = store.snapshot()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"mode": snapshot["mode"], "batch_id": args.batch_id,
                      "ingest": result, "stored": snapshot["total_vacancies"],
                      "publication_approved": False}, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
