"""Evidence-backed advertiser-sector enrichment for historical BA tracker.

Offline; no scraping or employer/client industry guesses.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "business-analysis-tracker" / "config" / "sector-evidence.json"
INPUT = ROOT / "business-analysis-tracker" / "data" / "preview-snapshot.json"
OUTPUT = ROOT / "business-analysis-tracker" / "data" / "sector-enriched-snapshot.json"
UNKNOWN = "Not specified"


def enrich(snapshot: dict, config: dict) -> dict:
    if config.get("scope") != "ADVERTISER_ORGANISATION_ONLY":
        raise ValueError("Only evidence-backed advertiser sectors are permitted")
    if snapshot.get("schema") != "uk-business-analysis-preview/v2" or snapshot.get("publication_approved") is not False:
        raise ValueError("Only source-observed historical BA preview is supported")
    catalog = {}
    for obj in config.get("employers", []):
        name = obj["advertiser"].strip().casefold()
        url = obj["evidence_url"]
        if not url.startswith("https://") or not obj["sector"] or name in catalog:
            raise ValueError("Sector map requires unique exact organisations and HTTPS evidence")
        catalog[name] = obj

    rows = []
    for row in snapshot["records"]:
        v = dict(row)
        v["sector"] = UNKNOWN
        v["sector_basis"] = "UNKNOWN_NO_EVIDENCE"
        v["sector_evidence_url"] = None
        v["end_client_sector"] = UNKNOWN
        v["sector_display_scope"] = "ADVERTISER_SECTOR_NOT_END_CLIENT"
        advertiser = str(v.get("advertiser") or "").strip().casefold()
        source = catalog.get(advertiser)
        if source:
            v["sector"] = source["sector"]
            v["sector_basis"] = source["basis"]
            v["sector_evidence_url"] = source["evidence_url"]
        rows.append(v)

    counts = Counter(x["sector"] for x in rows)
    result = dict(snapshot)
    result["schema"] = "uk-business-analysis-preview/v2-sector-enriched"
    result["records"] = rows
    result["sector_definition"] = "advertiser_organisation_industry_not_end_client"
    result["sector_data_quality"] = {
        "total_records": len(rows),
        "advertiser_missing": sum(r.get("advertiser") == UNKNOWN for r in rows),
        "sector_resolved_with_external_organisation_evidence": len(rows)-counts.get(UNKNOWN, 0),
        "sector_not_specified": counts.get(UNKNOWN, 0),
        "end_client_sector_resolved": 0,
        "by_advertiser_sector": dict(sorted(counts.items())),
    }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=INPUT)
    p.add_argument("--mapping", type=Path, default=MAP)
    p.add_argument("--output", type=Path, default=OUTPUT)
    args = p.parse_args()
    if args.output.resolve() in {args.input.resolve(), MAP.resolve(), ROOT / "dashboard/live-data.json", ROOT / "dashboard/data.json"}:
        p.error("Cannot overwrite source or Salesforce output")
    result = enrich(json.loads(args.input.read_text(encoding="utf-8")),
                    json.loads(args.mapping.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["sector_data_quality"], sort_keys=True))


if __name__ == "__main__":
    main()
