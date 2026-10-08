"""Convert historical one-off pilot evidence to the offline evidence-gate input format."""
import argparse,json
from pathlib import Path
from scripts.candidate_evidence_gate import assess

ALLOWED={"Totaljobs","Indeed UK","JobServe"}
def extract(pilot):
    results=pilot.get("results")
    if not isinstance(results,list):raise ValueError("Pilot results missing")
    rows=[]
    for item in results:
        source=item.get("source")
        if source not in ALLOWED:raise ValueError("Unexpected source")
        records=item.get("vacancies")
        if not isinstance(records,list):raise ValueError("Missing retained vacancies")
        for rec in records:
            if not isinstance(rec,dict):raise ValueError("Malformed vacancy")
            rows.append({"source":source,"title":rec.get("title"),"url":rec.get("url")})
    return rows
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--output",required=True)
    args=p.parse_args()
    rows=extract(json.loads(Path(args.input).read_text(encoding="utf-8")))
    report=assess(rows)
    report["pilot_source_counts"]={x["source"]:x["accepted_count"] for x in json.loads(Path(args.input).read_text())["results"]}
    report["provisional_title_review_not_verified"]=True
    report["quality_gate_status"]="BLOCKED_MISSING_EVIDENCE"
    report["publication_approved"]=False
    destination=Path(args.output)
    if destination.resolve() in (Path("dashboard/data.json").resolve(),Path("dashboard/live-data.json").resolve()):raise ValueError("Live dashboard forbidden")
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"records":len(rows),"ready":report["publication_ready_count"],"publication_approved":False}))
if __name__=="__main__":main()
