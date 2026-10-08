"""Create an evidence-linked human review queue from the historical pilot export.

No network requests. Never treats a submitted claim as independently verified.
"""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
from scripts.review_existing_candidate_pilot import extract
from scripts.candidate_evidence_gate import assess,identity_url

def build_queue(document):
    rows=extract(document)
    checks=assess(rows)
    queue=[]
    for i,row in enumerate(rows):
        key=(row.get("source","")+"|"+str(identity_url(row.get("url")))).encode()
        queue.append({
            "record_id":hashlib.sha256(key).hexdigest()[:20],
            "source":row.get("source"),"title":row.get("title"),
            "source_url":row.get("url"),
            "review_status":"PENDING",
            "employer":None,"uk_location":None,"posting_date":None,
            "description_evidence_url":None,"active_vacancy_evidence_url":None,
            "evidence_checked_at_utc":None,"independent_reviewer":None,
            "role_family":None,"relevance_decision":"PENDING",
            "duplicate_of":None,"review_notes":None,
            "automated_flags":checks["records"][i]["flags"]
        })
    return {"schema":"candidate-manual-review/v1",
       "pilot_records":len(queue),"source_counts":dict(Counter(x["source"] for x in queue)),
       "reviewed_count":0,"verified_count":0,"publication_approved":False,
       "quality_assurance_complete":False,"queue":queue,
       "instructions":"Do not mark verified without time-stamped independent evidence and human reviewer."}

def summarise_review(review):
    queue=review.get("queue",[])
    if not isinstance(queue,list):raise ValueError("Queue missing")
    ids=[x.get("record_id") for x in queue]
    if len(ids)!=len(set(ids)):raise ValueError("Duplicate review identity")
    verified=[]
    for row in queue:
        required=("employer","uk_location","posting_date","description_evidence_url",
                  "active_vacancy_evidence_url","evidence_checked_at_utc",
                  "independent_reviewer","role_family")
        valid=(row.get("review_status")=="VERIFIED"
          and row.get("relevance_decision")=="INCLUDE"
          and row.get("duplicate_of") is None
          and all(row.get(k) for k in required))
        verified.append(valid)
    return {"record_count":len(queue),"verified_count":sum(verified),
       "pending_or_rejected":len(queue)-sum(verified),
       "publication_approved":False,
       "quality_assurance_complete":len(queue)>0 and all(verified),
       "note":"Evidence fields are declarations requiring independent spot checks; no URL live status is inferred."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pilot",required=True);p.add_argument("--queue",required=True)
    args=p.parse_args()
    q=build_queue(json.loads(Path(args.pilot).read_text(encoding="utf-8")))
    target=Path(args.queue)
    forbidden={Path("dashboard/data.json").resolve(),Path("dashboard/live-data.json").resolve()}
    if target.resolve() in forbidden:raise ValueError("Production output blocked")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(q,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"queued":len(q),"verified":0,"publication_approved":False}))
if __name__=="__main__":main()
