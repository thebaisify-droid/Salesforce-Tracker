"""Stage a five-board Business Analysis refresh from previously acquired source exports.

Offline only: no Apify API requests, Actor launches, GitHub workflow dispatch, or
WordPress writes. Strict five-source evidence gate; fails closed on missing boards.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from tracker.business_product_delivery_security import classify_market_role
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "business-analysis-tracker" / "config" / "sector-evidence.json"
OUTPUT = ROOT / "business-analysis-tracker" / "data" / "next-refresh-staging.json"
NAMES = ("CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe")

def field(row, *keys):
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return html.unescape(value.strip())
    return None

def nested(row, parent, name):
    obj = row.get(parent)
    return field(obj, name) if isinstance(obj, dict) else None

def link(row, source):
    keys = {
        "CV-Library": ("canonicalUrl", "sourceUrl", "url", "applyUrl"),
        "Totaljobs": ("jobUrl", "url", "applyUrl"),
        "Reed UK": ("url", "externalUrl"),
        "Indeed UK": ("url",),
        "JobServe": ("url", "applyUrl"),
    }[source]
    value = field(row, *keys)
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), parsed.query, ""))

def posted(row):
    value = field(row, "postedDateTime", "postedAt", "datePosted", "postedDate")
    if not value:
        return None
    try:
        iso = date.fromisoformat(value[:10])
        return iso.isoformat() if iso <= date.today() else None
    except ValueError:
        return None

def employment(row):
    for key in ("contractType", "jobType", "workType"):
        value = field(row, key)
        if not value:
            continue
        v = value.lower()
        if "permanent" in v or v == "perm":
            return "Permanent"
        if "contract" in v or "freelance" in v:
            return "Contract"
        if "temporary" in v or "temp " in v or v == "temp":
            return "Temporary"
    return "Not specified"

def working(row):
    if field(row, "jobLocationType") == "TELECOMMUTE" or row.get("remote") is True:
        return "Remote"
    if row.get("isRemote") is True:
        return "Remote"
    return "Not specified"

def cleaned_excerpt(row):
    raw = field(row, "descriptionText", "descriptionSnippet", "snippet",
                "description", "textSnippet")
    if not raw:
        return None
    raw = re.sub(r"<[^>]*>", " ", raw)
    raw = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[contact omitted]", raw)
    raw = re.sub(r"(?<!\w)(?:\+44\s?\d[\d\s()-]{8,}|0\d{3,5}\s?\d[\d\s()-]{5,})(?!\w)",
                 "[contact omitted]", raw)
    return re.sub(r"\s+", " ", raw).strip()[:260] or None

def company(row):
    value = field(row, "company", "employer", "companyName", "recruiter")
    return value or nested(row, "company", "name") or nested(row, "employer", "name") or "Not specified"

def location(row):
    return (field(row, "location", "job_location")
            or nested(row, "location", "text") or "Not specified")

def sector_catalog(config):
    if config.get("scope") != "ADVERTISER_ORGANISATION_ONLY":
        raise ValueError("Sector mapping scope is not advertiser-only")
    values = {}
    for x in config.get("employers", []):
        name = x["advertiser"].strip().casefold()
        if not x["evidence_url"].startswith("https://") or name in values:
            raise ValueError("Sector evidence must be unique and secure")
        values[name] = x
    return values

def stage(input_doc, sector_mapping):
    if input_doc.get("schema") != "ba-five-source-completed-batch/v1":
        raise ValueError("Expected completed batch evidence, not a live scrape request")
    receipts = input_doc.get("sources")
    if not isinstance(receipts, list):
        raise ValueError("No source receipts")
    statuses = [{"source": x.get("name"), "status": x.get("status"),
                 "attempted": x.get("attempted")} for x in receipts if isinstance(x, dict)]
    qa = validate_run_receipts(statuses, qa_passed=True)
    if not qa["publish_fresh_five_source_snapshot"]:
        return {"schema": "ba-five-source-staging/v1", "status": "BLOCKED",
                "preserve_prior_snapshot": True, "reason": qa["reasons"],
                "records": [], "source_receipts": statuses}
    if any(not isinstance(x.get("records"), list) or not x.get("run_id")
           or not x.get("dataset_id") or not x.get("observed_at")
           for x in receipts):
        raise ValueError("Missing run ID, dataset provenance, observation, or dataset rows")

    sectors = sector_catalog(sector_mapping)
    seen_url, provisional = set(), []
    rejected = Counter()
    counts = Counter()
    for receipt in receipts:
        src = receipt["name"]
        for raw in receipt["records"]:
            counts[src] += 1
            if not isinstance(raw, dict):
                rejected["malformed"] += 1
                continue
            if src == "CV-Library" and raw.get("changeType") == "EXPIRED":
                rejected["cv_expiry_event_ignored"] += 1
                continue
            if src == "Totaljobs" and raw.get("rowType", "job") != "job":
                rejected["non_job_row"] += 1
                continue
            title = field(raw, "title", "jobTitle")
            url = link(raw, src)
            if not title or not url:
                rejected["missing_title_or_https_advert"] += 1
                continue
            desc = cleaned_excerpt(raw)
            role = classify_market_role(title, desc)
            if not role.get("included"):
                rejected["out_of_scope"] += 1
                continue
            if url in seen_url:
                rejected["exact_url_duplicate"] += 1
                continue
            seen_url.add(url)
            advertiser = company(raw)
            ev = sectors.get(advertiser.casefold())
            loc = location(raw)
            ident = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
            provisional.append({
                "id": ident, "title": title[:240], "advertiser": advertiser[:180],
                "location": loc[:160], "job_source": src,
                "original_advert_url": url, "source_run_id": receipt["run_id"],
                "dataset_id": receipt["dataset_id"],
                "observed_at": receipt["observed_at"],
                "posted_date": posted(raw), "employment": employment(raw),
                "working_arrangement": working(raw),
                "role_family": role["role_family"], "track": role["track"],
                "role_review_required": bool(role.get("review_required")),
                "description_summary": desc, "skills": [],
                "sector": ev["sector"] if ev else "Not specified",
                "sector_basis": ev["basis"] if ev else "UNKNOWN_NO_EVIDENCE",
                "sector_evidence_url": ev["evidence_url"] if ev else None,
                "end_client_sector": "Not specified", "source_observed_only": True,
            })
    # Cross-board title + advertiser + location are possible duplicates, not
    # conclusive evidence: flag rather than lose potentially distinct openings.
    signatures = defaultdict(list)
    for item in provisional:
        signatures[tuple(str(item[k]).casefold().strip()
                         for k in ("title", "advertiser", "location"))].append(item["id"])
    for item in provisional:
        signature = tuple(str(item[k]).casefold().strip()
                          for k in ("title", "advertiser", "location"))
        item["potential_duplicate"] = len(signatures[signature]) > 1

    provisional.sort(key=lambda x: (x["posted_date"] or "", x["title"].casefold()), reverse=True)
    return {"schema": "ba-five-source-staging/v1",
            "status": "FIVE_SOURCES_RECEIVED_STAGED_ONLY",
            "source_observed_only": True,
            "publication_approved": False,
            "wordpress_published": False,
            "salesforce_unchanged": True,
            "no_paid_runs_launched_by_stager": True,
            "records": provisional,
            "source_receipts": statuses,
            "source_input_rows": dict(counts),
            "rejected": dict(rejected),
            "potential_duplicate_rows": sum(x["potential_duplicate"] for x in provisional),
            "total_matching_advertisements": len(provisional)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="Local completed five-source batch JSON")
    parser.add_argument("--mapping", type=Path, default=MAPPING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    a = parser.parse_args()
    forbidden = {a.input.resolve(), a.mapping.resolve(),
                 ROOT / "dashboard/live-data.json", ROOT / "dashboard/data.json",
                 ROOT / "business-analysis-tracker/data/preview-snapshot.json"}
    if a.output.resolve() in forbidden:
        parser.error("Cannot overwrite source or live Salesforce/BA dashboard")
    result = stage(json.loads(a.input.read_text(encoding="utf-8")),
                   json.loads(a.mapping.read_text(encoding="utf-8")))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"],
                      "matching": result.get("total_matching_advertisements", 0),
                      "published": False,
                      "actor_runs_launched": 0}, sort_keys=True))
    return 0 if result["status"] == "FIVE_SOURCES_RECEIVED_STAGED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
