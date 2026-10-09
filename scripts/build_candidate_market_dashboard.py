"""Build an isolated offline candidate-market dashboard JSON from supplied records.

No scraping, external requests, database writes or live publication.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tracker.business_product_delivery_security import classify_raw, taxonomy

ALLOWED = ("title", "title_raw", "job_title", "jobTitle", "position", "name")
URL_KEYS = ("url", "apply_url", "job_url", "jobUrl", "link")
SOURCE_KEYS = ("source", "source_name", "job_board")
DATE_KEYS = ("posted_at", "postedAt", "datePosted", "date_posted")
COMPANY_KEYS = ("company", "company_name", "employer", "advertiser")
LOCATION_KEYS = ("location", "city", "job_location")

def _field(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None

def _clean_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    pairs = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")]
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), urlencode(pairs), ""))

def build_snapshot(records: list[dict[str, Any]], generated_at: str | None = None) -> dict[str, Any]:
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    seen: dict[str, dict[str, Any]] = {}
    counts = Counter()
    for row in records:
        if not isinstance(row, dict):
            counts["malformed"] += 1
            continue
        decision = classify_raw(row)
        if not decision["included"]:
            counts["excluded"] += 1
            continue
        title = _field(row, ALLOWED)
        url = _clean_url(_field(row, URL_KEYS))
        if not title or not url:
            counts["invalid"] += 1
            continue
        company = _field(row, COMPANY_KEYS)
        location = _field(row, LOCATION_KEYS)
        key = url.lower()
        if key in seen:
            counts["duplicate"] += 1
            continue
        seen[key] = {
            "title": title,
            "url": url,
            "advertiser": company,
            "location": location,
            "posted_at": _field(row, DATE_KEYS),
            "source": _field(row, SOURCE_KEYS),
            "track": decision["track"],
            "role_family": decision["role_family"],
            "matched_title": decision["matched_title"],
            "review_required": decision["review_required"],
        }
    rows = sorted(seen.values(), key=lambda row: (row["posted_at"] or "", row["title"]), reverse=True)
    by_track = Counter(row["track"] for row in rows)
    by_family = Counter(row["role_family"] for row in rows)
    reviewed = sum(bool(row["review_required"]) for row in rows)
    return {
        "schema": "uk-business-product-delivery-security/v1",
        "mode": "offline_candidate_only",
        "publication_approved": False,
        "acquisition_enabled": False,
        "taxonomy_version": taxonomy()["version"],
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "total_vacancies": len(rows),
        "review_required": reviewed,
        "rejections": dict(counts),
        "by_track": [{"label": name, "value": by_track.get(name, 0)} for name in ("BUSINESS_PRODUCT_DELIVERY", "SECURITY")],
        "by_role_family": [{"label": group["name"], "track": group["track"], "value": by_family.get(group["name"], 0)} for group in taxonomy()["role_families"]],
        "vacancies": rows,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OFFLINE candidate hiring dashboard JSON")
    parser.add_argument("--input", required=True, help="Local JSON list of vacancy records")
    parser.add_argument("--output", required=True, help="Offline candidate output, not the Salesforce live path")
    args = parser.parse_args()
    target = Path(args.output)
    if target.as_posix() in ("dashboard/live-data.json", "dashboard/data.json"):
        parser.error("existing Salesforce dashboard output is protected")
    if target.resolve() == Path(args.input).resolve():
        parser.error("output cannot overwrite the source input")
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    snapshot = build_snapshot(raw)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OFFLINE ONLY: {snapshot['total_vacancies']} unique target vacancies -> {target}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
