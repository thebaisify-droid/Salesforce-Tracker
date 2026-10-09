"""Offline taxonomy coverage audit; provisional labels are never verified vacancies."""
import argparse
import json
from collections import Counter
from pathlib import Path

def assess(snapshot, taxonomy):
    family_items=taxonomy["role_families"]
    names=[f["name"] for f in family_items]
    if len(names)!=22 or len(set(names))!=22:
        raise ValueError("Expected 22 unique taxonomy families")
    counts=Counter(r.get("provisional_family") for r in snapshot["records"] if r.get("provisional_family"))
    unknown=sorted(set(counts)-set(names))
    groups=[]
    for family in family_items:
        name=family["name"]
        groups.append({"family":name,"track":family["track"],"provisional_records":counts.get(name,0),
                       "independently_verified_records":0,"coverage_status":"PROVISIONAL_ONLY" if counts.get(name) else "NOT_SAMPLED"})
    return {"schema":"candidate-family-coverage/v1","taxonomy_families":22,
            "provisionally_represented":sum(bool(counts.get(n)) for n in names),
            "unrepresented":sum(not counts.get(n) for n in names),
            "unmapped_provisional_families":unknown,
            "records_without_provisional_family":sum(not r.get("provisional_family") for r in snapshot["records"]),
            "families":groups,"publication_approved":False,
            "note":"Provisional family coverage is not independent accuracy validation or representative sampling."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--snapshot",default="candidate-beta/data/pilot-snapshot.json")
    p.add_argument("--taxonomy",default="config/business_product_delivery_security_taxonomy_v1.0.json")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    out=Path(args.output).resolve()
    if out in {Path(args.snapshot).resolve(),Path(args.taxonomy).resolve(),
               Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve()}:
        p.error("Protected source or production path")
    result=assess(json.loads(Path(args.snapshot).read_text()),json.loads(Path(args.taxonomy).read_text()))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="families"},sort_keys=True))
if __name__=="__main__":
    main()
