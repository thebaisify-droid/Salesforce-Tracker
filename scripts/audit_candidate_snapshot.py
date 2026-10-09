"""Read-only candidate snapshot release eligibility report. No external calls."""
import argparse
import json
from collections import Counter
from pathlib import Path

def audit(snapshot):
    rows = snapshot["records"]
    counts = Counter(x["source"] for x in rows)
    families = Counter(x["provisional_family"] for x in rows if x.get("provisional_family"))
    statuses = Counter(x["verification"] for x in rows)
    verified = sum(x["publication_ready"] is True for x in rows)
    id_count = len({x["id"] for x in rows})
    url_count = len({x["url"] for x in rows})
    reasons = []
    if snapshot.get("publication_approved") is not False:
        reasons.append("snapshot_publication_flag_unsafe")
    if verified:
        reasons.append("unexpected_publication_ready_record")
    if len(rows) < 100:
        reasons.append("fewer_than_100_records")
    if len(families) < 22:
        reasons.append("fewer_than_22_role_families")
    if len(rows) != id_count or len(rows) != url_count:
        reasons.append("duplicate_ids_or_urls")
    if not snapshot.get("verified_representative_coverage"):
        reasons.append("representative_coverage_not_verified")
    if any(s not in ("SOURCE_ONLY_UNVERIFIED","PAGE_VIEWED_NOT_VERIFIED") for s in statuses):
        reasons.append("unrecognised_evidence_status")
    return {
        "schema":"candidate-snapshot-audit/v1",
        "records":len(rows),
        "sources":dict(sorted(counts.items())),
        "provisional_family_counts":dict(sorted(families.items())),
        "records_without_provisional_family":sum(not x.get("provisional_family") for x in rows),
        "evidence_status_counts":dict(sorted(statuses.items())),
        "publication_ready_records":verified,
        "unique_ids":id_count,"unique_urls":url_count,
        "release_status":"NO_GO",
        "reasons":reasons,
        "note":"This source-snapshot audit never establishes independent verification, precision, recall, or approval."
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",default="candidate-beta/data/pilot-snapshot.json")
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    out=Path(args.output).resolve()
    if out in {Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve(),Path(args.snapshot).resolve()}:
        parser.error("Cannot overwrite production or source records")
    report=audit(json.loads(Path(args.snapshot).read_text(encoding="utf-8")))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
