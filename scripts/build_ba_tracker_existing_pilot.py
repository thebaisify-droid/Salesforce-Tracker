"""Build isolated BA/Product/Delivery/Cyber dashboard data from completed pilots.

No network, Apify runs, Salesforce publication or WordPress writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from tracker.business_product_delivery_security import classify_market_role, taxonomy

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "candidate-beta" / "data" / "pilot-snapshot.json"
DEFAULT_CYBER = ROOT / "business-analysis-tracker" / "data" / "completed-cyber-pilots.json"
DEFAULT_OUTPUT = ROOT / "business-analysis-tracker" / "data" / "preview-snapshot.json"
FAMILY_UMBRELLA = "Information Security / Cyber Security"
PROTECTED = {"dashboard/live-data.json", "dashboard/data.json", "data/salesforce_tracker.db"}
SOURCES = {"Totaljobs", "Indeed UK", "JobServe", "CV-Library", "Reed UK"}
EVIDENCE = {"SOURCE_ONLY_UNVERIFIED", "PAGE_VIEWED_NOT_VERIFIED"}


def _url(value):
    if not isinstance(value, str):
        return False
    p = urlsplit(value)
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password


def _date_only(value):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value[:10])
        if parsed > date(2026, 10, 15):
            return None
        return parsed.isoformat()
    except ValueError:
        return None


def build(pilot: dict, cyber: dict | None = None) -> dict:
    if pilot.get("sample_only") is not True or pilot.get("publication_approved") is not False:
        raise ValueError("Historical source-only, non-approved pilot snapshot required")
    if cyber is not None and (cyber.get("status") != "HISTORICAL_SOURCE_ONLY"
                              or cyber.get("actor_runs_started_by_import") != 0
                              or cyber.get("source") != "Indeed UK"):
        raise ValueError("Only previously completed read-only Cyber evidence is allowed")
    baseline = pilot.get("records")
    extras = cyber.get("records", []) if cyber is not None else []
    if not isinstance(baseline, list) or not isinstance(extras, list):
        raise ValueError("Missing records")
    result, seen, rejections = [], set(), Counter()

    def add(row: dict, *, pilot_row: bool):
        if not isinstance(row, dict):
            rejections["malformed"] += 1
            return
        if pilot_row and (row.get("verification") not in EVIDENCE or row.get("publication_ready") is not False):
            raise ValueError("Unsafe historical pilot evidence state")
        if not pilot_row and row.get("source_observed_only") is not True:
            raise ValueError("Missing cyber source-only evidence flag")
        source = row.get("source")
        title, url = row.get("title"), row.get("url")
        if source not in SOURCES or not isinstance(title, str) or not title.strip() or not _url(url):
            rejections["invalid_source_or_url_or_title"] += 1
            return
        snippet = str(row.get("source_excerpt") or "") if not pilot_row else ""
        decision = classify_market_role(title, snippet)
        if not decision["included"]:
            rejections["outside_taxonomy_or_needs_context"] += 1
            return
        if url in seen:
            rejections["duplicate_source_url"] += 1
            return
        seen.add(url)
        advertiser = row.get("employer") if pilot_row else row.get("advertiser")
        ident = row.get("id") if pilot_row else hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        result.append({
            "id": ident,
            "title": title.strip(),
            "advertiser": advertiser if isinstance(advertiser, str) and advertiser.strip() else "Not specified",
            "location": row.get("location") or "Not specified",
            "source": source,
            "url": url,
            "role_family": decision["role_family"],
            "track": decision["track"],
            "review_required": bool(decision["review_required"]),
            "employment": "Not specified",
            "working_arrangement": "Not specified",
            "sector": "Not specified",
            "posted_date": _date_only(row.get("posted_at")) if not pilot_row else None,
            "description_summary": snippet.strip()[:300] or None,
            "skills": [],
            "source_observed_only": True,
            "source_run_id": row.get("run_id") if not pilot_row else None,
        })

    for row in baseline:
        add(row, pilot_row=True)
    for row in extras:
        add(row, pilot_row=False)
    result.sort(key=lambda r: (r["posted_date"] or "", r["title"].casefold(), r["url"]), reverse=True)
    cfg = taxonomy()
    families = [{"name": f["name"], "track": f["track"]} for f in cfg["role_families"]]
    family_counts = Counter(r["role_family"] for r in result)
    source_counts = Counter(r["source"] for r in result)
    return {
        "schema": "uk-business-analysis-preview/v2",
        "status": "HISTORICAL_SOURCE_OBSERVED_PREVIEW",
        "publication_approved": False,
        "new_paid_apify_runs": 0,
        "live_refresh_enabled": False,
        "not_confirmed_active": True,
        "source_snapshot_date": pilot.get("snapshot_date"),
        "source_record_count": len(baseline) + (cyber.get("input_record_count", 0) if cyber else 0),
        "retained_record_count": len(result),
        "excluded": dict(sorted(rejections.items())),
        "preclassified_cyber_source_count": len(extras),
        "job_families": families,
        "umbrella_filter": {"name": FAMILY_UMBRELLA, "track": "SECURITY"},
        "by_family": {f["name"]: family_counts[f["name"]] for f in families},
        "by_source": dict(sorted(source_counts.items())),
        "cross_source_deduplication_verified": False,
        "records": result,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--cyber", type=Path, default=DEFAULT_CYBER)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = p.parse_args()
    if args.input.resolve() == args.output.resolve() or args.cyber.resolve() == args.output.resolve():
        p.error("Output cannot overwrite input")
    if args.output.resolve() in {ROOT / key for key in PROTECTED}:
        p.error("Cannot overwrite Salesforce production files")
    snapshot = build(json.loads(args.input.read_text(encoding="utf-8")),
                     json.loads(args.cyber.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": snapshot["status"], "matched": snapshot["retained_record_count"],
                      "records_in": snapshot["source_record_count"], "paid_runs": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
