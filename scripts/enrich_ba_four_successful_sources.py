"""Enhance four successful BA source datasets without new collection or publication."""
from __future__ import annotations
import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"business-analysis-tracker/evidence/ba-four-successful-boards-20261015-qa.json"
TARGET=ROOT/"business-analysis-tracker/evidence/ba-four-boards-enriched-20261015.json"

# Exact advertisement-level text evidence; never spread a client's sector across
# other advertisements from the same recruiter or across unrelated job titles.
EVIDENCE={
 "pilot-reeduk-21":("Public Sector","END_CLIENT_PROGRAMME","Central Government Service Transformation Programme"),
 "pilot-reeduk-22":("Financial Services","END_CLIENT_SECTOR","client within the Financial Services sector"),
 "pilot-reeduk-27":("Manufacturing & Engineering","ADVERTISER_SECTOR","Müller manufacturing sites"),
 "pilot-totaljobs-13":("Financial Services","ADVERTISER_SECTOR","custodian banks"),
 "pilot-totaljobs-14":("Education & Nonprofit","END_CLIENT_SECTOR","Higher Education institution"),
 "pilot-totaljobs-19":("Financial Services","ADVERTISER_SECTOR","financial data management platform"),
}
# The shorter retained snippet says Finance, which is insufficient to assert
# Financial Services over an in-house corporate finance function.
REVIEW={"pilot-reeduk-26":"Finance-sector client mentioned; sub-sector not established"}
REVIEW_DUPLICATES=(("pilot-cvlibrary-8","pilot-totaljobs-16"),)

def enrich(src):
    if src.get("schema")!="ba-four-source-pilot-qa/v1" or src.get("publication_approved") is not False:
        raise ValueError("Expected unpublished four-board pilot QA")
    records=src.get("records")
    if not isinstance(records,list) or len(records)!=33:
        raise ValueError("Expected exactly 33 source advertisements")
    ids={r.get("id") for r in records}
    if len(ids)!=33 or not set(EVIDENCE).issubset(ids) or not set(REVIEW).issubset(ids):
        raise ValueError("Record IDs changed; evidence needs renewed validation")
    rows=[]
    for record in records:
        r=dict(record)
        r["advertiser_sector"]="Not specified"
        r["end_client_sector"]="Not specified"
        r["sector_display"]="Not specified"
        r["sector_basis"]="INSUFFICIENT_EVIDENCE"
        r["sector_evidence_quote"]=None
        r["sector_confidence"]="unknown"
        r["sector_review_required"]=False
        r["possible_duplicate_ids"]=[]
        if r["id"] in EVIDENCE:
            sector,scope,quote=EVIDENCE[r["id"]]
            snippet=r.get("description_summary") or ""
            if not re.search(re.escape(quote),snippet,re.I):
                raise ValueError("Source excerpt no longer supports: "+r["id"])
            if scope=="END_CLIENT_SECTOR":
                r["end_client_sector"]=sector
            elif scope=="ADVERTISER_SECTOR":
                r["advertiser_sector"]=sector
            else:
                r["end_client_sector"]=sector
            r["sector_display"]=sector
            r["sector_basis"]="SOURCE_ADVERTISEMENT_"+scope
            r["sector_evidence_quote"]=quote
            r["sector_confidence"]="source_observed_not_independently_verified"
        if r["id"] in REVIEW:
            r["sector_review_required"]=True
            r["sector_review_reason"]=REVIEW[r["id"]]
        rows.append(r)
    by_id={r["id"]:r for r in rows}
    for a,b in REVIEW_DUPLICATES:
        first,second=by_id[a],by_id[b]
        if first["source"]==second["source"]:
            raise ValueError("Expected cross-board possible duplicate")
        if first["title"].casefold()!=second["title"].casefold() or first["posted_date"]!=second["posted_date"]:
            raise ValueError("Potential duplicate candidate changed")
        first["possible_duplicate_ids"].append(b)
        second["possible_duplicate_ids"].append(a)
    metrics=Counter(r["sector_display"] for r in rows)
    result=dict(src)
    result["schema"]="ba-four-source-pilot-enriched/v1"
    result["records"]=rows
    result["data_quality"]={
        "source_records":40,"matched_advertisements":33,"out_of_scope":7,
        "sector_with_specific_advert_evidence":len(EVIDENCE),
        "sector_unknown":metrics["Not specified"],
        "sector_requires_review":len(REVIEW),
        "end_client_sector_with_evidence":sum(r["end_client_sector"]!="Not specified" for r in rows),
        "advertiser_sector_with_evidence":sum(r["advertiser_sector"]!="Not specified" for r in rows),
        "possible_cross_board_duplicate_pairs":1,
        "confirmed_cross_board_duplicate_pairs":0,
        "unique_vacancies_confirmed":False,
        "publication_allowed":False,
        "missing_fifth_source":"JobServe",
    }
    result["source_sector_breakdown"]=dict(sorted(metrics.items()))
    result["publication_approved"]=False
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=SOURCE)
    parser.add_argument("--output",type=Path,default=TARGET)
    args=parser.parse_args()
    if args.source.resolve()==args.output.resolve() or args.output.resolve() in {
        ROOT/"dashboard/live-data.json",ROOT/"dashboard/data.json",
        ROOT/"business-analysis-tracker/data/preview-snapshot.json"}:
        parser.error("Production/source overwrites forbidden")
    result=enrich(json.loads(args.source.read_text(encoding="utf8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps(result["data_quality"],sort_keys=True))

if __name__=="__main__":
    main()
