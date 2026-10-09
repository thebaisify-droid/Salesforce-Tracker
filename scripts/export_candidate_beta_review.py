"""Create a human-review CSV from the historical private beta without invented evidence."""
import argparse
import csv
import json
from pathlib import Path

FIELDS = ("id","source","title","url","observed_employer","observed_location",
          "provisional_family","existing_evidence_state","independent_employer_confirmed",
          "independent_title_confirmed","uk_location_confirmed","posting_date",
          "live_vacancy_confirmed","cross_source_duplicate_checked","human_role_family",
          "reviewer","reviewed_at","independent_evidence_url","review_notes")

def export_review(snapshot):
    if snapshot.get("publication_approved") is not False or snapshot.get("sample_only") is not True:
        raise ValueError("Only unapproved historical beta snapshots are accepted")
    records = snapshot.get("records")
    if not isinstance(records,list) or not records:
        raise ValueError("Missing historical records")
    if len({r["id"] for r in records}) != len(records):
        raise ValueError("Duplicate IDs require manual investigation")
    output=[]
    for r in records:
        if r.get("publication_ready") is not False:
            raise ValueError("Unexpected publication-ready record")
        if r.get("verification") not in {"SOURCE_ONLY_UNVERIFIED","PAGE_VIEWED_NOT_VERIFIED"}:
            raise ValueError("Unrecognised evidence status")
        row={key:"" for key in FIELDS}
        row.update(id=r["id"],source=r["source"],title=r["title"],url=r["url"],
                   observed_employer=r.get("employer") or "",
                   observed_location=r.get("location") or "",
                   provisional_family=r.get("provisional_family") or "",
                   existing_evidence_state=r["verification"])
        output.append(row)
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="candidate-beta/data/pilot-snapshot.json")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    target=Path(args.output).resolve()
    forbidden={Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve()}
    if target in forbidden:
        p.error("Production dashboard outputs are protected")
    rows=export_review(json.loads(Path(args.snapshot).read_text(encoding="utf-8")))
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Prepared {len(rows)} unverified human-review rows; no labels or approvals assigned")

if __name__=="__main__":
    main()
