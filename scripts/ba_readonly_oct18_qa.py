"""Read-only validation of completed 18 October BA datasets."""
import json, os
from urllib.request import Request, urlopen
from scripts.ba_completed_dataset_handoff import build_batch
from scripts.ba_e2e_offline import run_offline
from scripts.ba_stage_five_source_data import MAPPING

RUNS=[{"source":a,"run_id":b} for a,b in [
 ("CV-Library","VdNRJYNyZm45gmNJJ"),
 ("Totaljobs","ujiZ4fyrTZJwQndJi"),
 ("Reed UK","1c1SvyZhITNLPZRTb"),
 ("Indeed UK","709mMt55f4pdqUbvd"),
 ("JobServe","Nf4OWRu0SvPC8PJqQ")]]
LIMITS={"CV-Library":30,"Totaljobs":30,"Reed UK":30,"Indeed UK":30,"JobServe":60}

def fetch(path,token):
    if not path.startswith("https://api.apify.com/v2/"): raise ValueError("Invalid host")
    req=Request(path,headers={"Authorization":"Bearer "+token},method="GET")
    with urlopen(req,timeout=35) as f: data=json.load(f)
    if "/items?" in path:return data
    return data["data"]

def main():
    token=os.environ["APIFY_TOKEN"]
    batch=build_batch(RUNS,token,get=fetch,max_per_source=100,max_items_by_source=LIMITS)
    qa=run_offline(batch,json.loads(MAPPING.read_text()))
    report={"status":qa["status"],"source_rows":{r["name"]:len(r["records"]) for r in batch["sources"]},
            "raw_source_rows":qa["raw_source_rows"],"matched":qa["matched"],"rejected":qa["rejected"],
            "preview_sha256":qa["preview_sha256"],"actor_runs_started":0,"wordpress_requests":0}
    print("BA_READONLY_E2E "+json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
