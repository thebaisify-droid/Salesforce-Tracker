"""Read-only Apify completed datasets -> five-source BA offline QA/delivery preview.

No Actor POST, no paid collection and no WordPress mutation. Fail closed if a
dataset count exceeds limit, if a run is not successful or the source identity
does not match. This is an independently testable integration boundary.
"""
from __future__ import annotations
import argparse,json,os,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import quote
from scripts.ba_e2e_offline import run_offline
from scripts.ba_jobserve_api_once import api
from scripts.ba_stage_five_source_data import MAPPING
EXPECTED={
 "CV-Library":"T0edvAvD8lVcvc58G",
 "Totaljobs":"RO7aokuNWfmP0kV0G",
 "Reed UK":"4iavHborUyvW5vQgz",
 "Indeed UK":"BkcKc9frZp43LeRM7",
 "JobServe":"iEeTOwSjZDvAshw7Y",
}
ROOT=Path(__file__).resolve().parents[1]
RESULT_DIR=ROOT/"business-analysis-tracker/data/read-only-handoff"
def build_batch(receipts,token,*,get=api,max_per_source=100,max_items_by_source=None):
    if not token:raise ValueError("APIFY_TOKEN needed for read-only retrieval")
    if not isinstance(receipts,list) or len(receipts)!=5 or {x.get("source") for x in receipts}!=set(EXPECTED):
        raise ValueError("Exactly five distinct source receipts required")
    sources=[]
    for row in receipts:
        source=row["source"]
        run_id=row.get("run_id")
        if not isinstance(run_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,100}",run_id):
            raise ValueError("Invalid run ID")
        run=get("https://api.apify.com/v2/actor-runs/"+run_id,token)
        dataset=run.get("defaultDatasetId")
        if run.get("status")!="SUCCEEDED" or run.get("actId")!=EXPECTED[source]:
            raise ValueError("Run not successful or Actor ID mismatch: "+source)
        if not isinstance(dataset,str) or not re.fullmatch(r"[A-Za-z0-9_-]{6,100}",dataset):
            raise ValueError("Missing dataset ID")
        count=get("https://api.apify.com/v2/datasets/"+dataset,token).get("itemCount")
        declared=(max_items_by_source or {}).get(source,max_per_source)
        if type(declared) is not int or declared<1 or declared>max_per_source:
            raise ValueError("Invalid agreed source count limit: "+source)
        if type(count) is not int or count<1 or count>declared:
            raise ValueError("Unexpected dataset count or item limit: "+source)
        # Existing API utility expects a data envelope, whereas dataset items
        # endpoint returns a list. Injected getter can support both shapes.
        result=get("https://api.apify.com/v2/datasets/"+dataset+"/items?clean=false&limit="+str(max_per_source),token)
        if not isinstance(result,list) or len(result)!=count:
            raise ValueError("Partial or malformed dataset: "+source)
        sources.append({"name":source,"status":"SUCCEEDED","attempted":True,
                        "run_id":run_id,"dataset_id":dataset,
                        "observed_at":run.get("finishedAt") or run.get("startedAt"),
                        "records":result})
    return {"schema":"ba-five-source-completed-batch/v1","sources":sources}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipts",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,default=RESULT_DIR)
    args=parser.parse_args()
    manifest=json.loads(args.receipts.read_text(encoding="utf8"))
    if manifest.get("schema")!="ba-source-run-receipts/v1" or manifest.get("publication_approved") is not False:
        parser.error("Invalid unpublished receipt manifest")
    # The existing api() helper works only on dictionary envelopes. Use a
    # strict adapter for list item GETs without ever performing HTTP POST.
    from urllib.request import Request,urlopen
    def get(path,token):
        req=Request(path,headers={"Authorization":"Bearer "+token,"Accept":"application/json"},method="GET")
        with urlopen(req,timeout=35) as response:
            document=json.load(response)
        if path.endswith("/items?clean=false&limit=100"):
            return document
        if not isinstance(document,dict) or not isinstance(document.get("data"),dict):
            raise ValueError("Malformed Apify read-only metadata")
        return document["data"]
    batch=build_batch(manifest.get("receipts"),os.environ.get("APIFY_TOKEN",""),get=get)
    evidence=json.loads(MAPPING.read_text(encoding="utf8"))
    qa=run_offline(batch,evidence)
    if qa["status"]!="DRY_RUN_PASS_NOT_PUBLISHED":
        raise ValueError("Quality gate blocked; live snapshot preserved")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for name,doc in [("qa-report",{k:v for k,v in qa.items() if k not in ("stage","candidate","package")}),
                     ("delivery-preview",qa["package"])]:
        (args.output_dir/(name+".json")).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"status":"READ_ONLY_FIVE_SOURCE_HANDOFF_PASSED",
                      "matched":qa["matched"],"actors_started":0,"wordpress_requests":0}))
if __name__=="__main__":main()
