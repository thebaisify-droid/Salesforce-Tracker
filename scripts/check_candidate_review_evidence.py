"""Offline evidence completeness report; never grants publication approval."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

REQUIRED=("id","source","title","url","independent_employer_confirmed",
 "independent_title_confirmed","uk_location_confirmed","posting_date",
 "live_vacancy_confirmed","cross_source_duplicate_checked","human_role_family",
 "reviewer","reviewed_at","independent_evidence_url")
YES={"yes","true","1"}
def assess(rows):
    rows=list(rows)
    gaps=Counter()
    seen=set()
    complete=0
    for row in rows:
        identifier=(row.get("id") or "").strip()
        if not identifier or identifier in seen:
            gaps["missing_or_duplicate_record_id"]+=1
        seen.add(identifier)
        for field in REQUIRED:
            val=(row.get(field) or "").strip()
            if not val:
                gaps["missing_"+field]+=1
        for field in ("independent_employer_confirmed","independent_title_confirmed",
                      "uk_location_confirmed","live_vacancy_confirmed",
                      "cross_source_duplicate_checked"):
            if (row.get(field) or "").strip().lower() not in YES:
                gaps["not_confirmed_"+field]+=1
        if not (row.get("independent_evidence_url") or "").strip().startswith("https://"):
            gaps["missing_secure_independent_evidence_link"]+=1
        if not (row.get("reviewer") or "").strip() or not (row.get("reviewed_at") or "").strip():
            gaps["missing_human_signoff"]+=1
        if all((row.get(f) or "").strip() for f in REQUIRED) and all(
           (row.get(f) or "").strip().lower() in YES for f in (
             "independent_employer_confirmed","independent_title_confirmed",
             "uk_location_confirmed","live_vacancy_confirmed","cross_source_duplicate_checked")) and (
             row.get("independent_evidence_url") or "").startswith("https://"):
            complete+=1
    return {"schema":"candidate-evidence-completeness/v1","review_rows":len(rows),
            "documented_complete_rows":complete,"gaps":dict(sorted(gaps.items())),
            "publication_approved":False,
            "note":"Self-reported review fields are not independent truth; reviewer and sampling audits still required."}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    target=Path(args.output).resolve()
    if target in {Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve(),Path(args.input).resolve()}:
        p.error("Refuse to overwrite source or Salesforce outputs")
    with open(args.input,encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames or not set(REQUIRED).issubset(reader.fieldnames):
            p.error("Missing required review fields")
        result=assess(reader)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    main()
