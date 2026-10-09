"""Offline source-quality comparison for already exported UK job records."""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from scripts.build_candidate_market_dashboard import _clean_url, _field, ALLOWED, URL_KEYS, DATE_KEYS, COMPANY_KEYS
from tracker.business_product_delivery_security import classify_raw

CORE=("CV-Library","Totaljobs","Indeed UK","JobServe")
OPTIONAL=("Reed",)

def analyse(sources: dict[str,list[dict]]) -> dict:
    if not isinstance(sources,dict):
        raise ValueError("sources must be an object")
    result=[]
    seen_global=set()
    missing_core = [name for name in CORE if name not in sources]
    supplied = {name for name in sources if name in (*CORE, *OPTIONAL)}
    for source in (*CORE,*OPTIONAL):
        records=sources.get(source)
        if records is None and source not in sources:
            result.append({"source":source,"core":source in CORE,"status":"NOT_SUPPLIED",
                           "raw_records":None,"valid_unique_urls":None,
                           "relevant_unique_urls":None,"incremental_unique_urls_in_order":None,
                           "relevant_with_company_and_date":None,"rejected_records":None})
            continue
        if not isinstance(records,list):
            raise ValueError(f"{source} must be a list")
        valid_urls=set()
        relevant_urls=set()
        complete=0
        rejected=0
        for raw in records:
            if not isinstance(raw,dict):
                rejected+=1
                continue
            url=_clean_url(_field(raw,URL_KEYS))
            title=_field(raw,ALLOWED)
            if not url or not title:
                rejected+=1
                continue
            valid_urls.add(url.lower())
            if classify_raw(raw)["included"]:
                relevant_urls.add(url.lower())
                if _field(raw,DATE_KEYS) and _field(raw,COMPANY_KEYS):
                    complete+=1
        incremental=relevant_urls-seen_global
        # Deterministic ordered attribution; not a causal estimate of provider value.
        seen_global|=relevant_urls
        result.append({"source":source,"core":source in CORE,"status":"SUPPLIED", "raw_records":len(records),
                       "valid_unique_urls":len(valid_urls),
                       "relevant_unique_urls":len(relevant_urls),
                       "incremental_unique_urls_in_order":len(incremental),
                       "relevant_with_company_and_date":complete,
                       "rejected_records":rejected})
    return {"schema":"candidate-source-quality/v1","mode":"offline_only",
            "acquisition_enabled":False,"publication_approved":False,
            "source_order":list(CORE)+list(OPTIONAL),"sources":result,
            "core_exports_supplied":not missing_core,
            "missing_core_exports":missing_core,
            "real_source_comparison_complete":False,
            "caveats":["Only URL-identical duplicates are consolidated; cross-board duplicates remain.",
                       "Incremental attribution depends on the fixed listed source order.",
                       "No extrapolation to market-wide coverage or traffic.",
                       "Missing source exports have status NOT_SUPPLIED and null metrics; even supplied empty exports are not independently verified to mean zero market vacancies."]}

def main():
    p=argparse.ArgumentParser(description="Evaluate existing source exports without acquisition")
    p.add_argument("--input",required=True,help="JSON mapping source name to array of records")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    target=Path(a.output).resolve()
    if target in {Path("dashboard/live-data.json").resolve(),Path("dashboard/data.json").resolve()}:
        p.error("existing Salesforce dashboard path protected")
    report=analyse(json.loads(Path(a.input).read_text(encoding="utf-8")))
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"mode":report["mode"],"sources_checked":len(report["sources"]),
                      "publication_approved":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
