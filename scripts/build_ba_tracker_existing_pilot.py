"""Build a separate UK BA/Product/Delivery/Cyber preview from existing Apify pilot evidence.

Offline only: no Apify calls, Actor launches, Salesforce database, or WordPress writes.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from tracker.business_product_delivery_security import classify_market_role, taxonomy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "candidate-beta" / "data" / "pilot-snapshot.json"
DEFAULT_OUTPUT = ROOT / "business-analysis-tracker" / "data" / "preview-snapshot.json"
FAMILY_UMBRELLA = "Information Security / Cyber Security"
PROTECTED = {"dashboard/live-data.json", "dashboard/data.json", "data/salesforce_tracker.db"}
SOURCES = {"Totaljobs", "Indeed UK", "JobServe", "CV-Library", "Reed UK"}
EVIDENCE = {"SOURCE_ONLY_UNVERIFIED", "PAGE_VIEWED_NOT_VERIFIED"}


def build(pilot: dict) -> dict:
    if pilot.get("sample_only") is not True or pilot.get("publication_approved") is not False:
        raise ValueError("Historical source-only, non-approved pilot snapshot required")
    original = pilot.get("records")
    if not isinstance(original, list):
        raise ValueError("Missing records")
    result, seen, rejection = [], set(), Counter()
    for row in original:
        if not isinstance(row, dict):
            rejection["malformed"] += 1
            continue
        if row.get("verification") not in EVIDENCE or row.get("publication_ready") is not False:
            raise ValueError("Invalid evidence state; refuse source-only import")
        source, title, url = row.get("source"), row.get("title"), row.get("url")
        if source not in SOURCES or not isinstance(title, str) or not isinstance(url, str):
            rejection["missing_required_fields"] += 1
            continue
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            rejection["unsafe_original_advert_url"] += 1
            continue
        decision = classify_market_role(title, "")
        if not decision["included"]:
            rejection["outside_taxonomy_or_needs_context"] += 1
            continue
        if url in seen:
            rejection["duplicate_source_url"] += 1
            continue
        seen.add(url)
        result.append({
            "id": row["id"],
            "title": title.strip(),
            "advertiser": row.get("employer") or "Not specified",
            "location": row.get("location") or "Not specified",
            "source": source,
            "url": url,
            "role_family": decision["role_family"],
            "track": decision["track"],
            "review_required": bool(decision["review_required"]),
            "employment": "Not specified",
            "working_arrangement": "Not specified",
            "sector": "Not specified",
            "posted_date": None,
            "description_summary": None,
            "skills": [],
            "source_observed_only": True,
        })
    result.sort(key=lambda r: (r["title"].casefold(), r["source"], r["url"]))
    cfg = taxonomy()
    families = [{"name": f["name"], "track": f["track"]} for f in cfg["role_families"]]
    count = Counter(r["role_family"] for r in result)
    return {
        "schema": "uk-business-analysis-preview/v1",
        "status": "HISTORICAL_SOURCE_OBSERVED_PREVIEW",
        "publication_approved": False,
        "new_paid_apify_runs": 0,
        "live_refresh_enabled": False,
        "not_live_vacancies": True,
        "source_snapshot_date": pilot.get("snapshot_date"),
        "source_record_count": len(original),
        "retained_record_count": len(result),
        "excluded": dict(sorted(rejection.items())),
        "job_families": families,
        "umbrella_filter": {"name": FAMILY_UMBRELLA, "track": "SECURITY"},
        "by_family": {f["name"]: count[f["name"]] for f in families},
        "records": result,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve():
        p.error("Output cannot overwrite source input")
    try:
        rel = args.output.resolve().relative_to(ROOT).as_posix()
        if rel in PROTECTED or rel.startswith("wordpress/"):
            p.error("Cannot overwrite Salesforce production or WordPress paths")
    except ValueError:
        pass
    snapshot = build(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": snapshot["status"], "matched": snapshot["retained_record_count"],
                      "records_in": snapshot["source_record_count"], "paid_runs": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
