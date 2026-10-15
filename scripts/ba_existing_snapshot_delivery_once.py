"""Exactly one controlled BA snapshot delivery from existing five-source pilot evidence.

This is NOT a new acquisition. All 57 public advert observations already appear
on page 49. Preserve actual source finish time; never label them newly scraped.
The dedicated receiver saves JSON only; visible page handoff is independently gated.
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from scripts.ba_atomic_snapshot_sender import send_once
from scripts.ba_wordpress_delivery_package import preflight
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/"business-analysis-tracker/evidence/ba-five-source-publication-candidate-20261015.json"
RUN_IDS={
 "CV-Library":("qo9YEfFlbYaV31MkK","OD5lSdCGHaw4q1D4j"),
 "Totaljobs":("2TlvO2bI41Bl50TeR","Yt7qb5XvPgdWn3TSW"),
 "Reed UK":("xLIKQOkwaZE5jFJn7","lecElui54GPzA0Qux"),
 "Indeed UK":("i6unDcLG8Qh1XSftt","ssJHtekdlbvmP2UCZ"),
 "JobServe":("c2PSagDDBiesSovtt","nkk1RZK5gznvfZogL"),
}
# Actual terminal time of the final successful JobServe run, not an invented new refresh.
LAST_SOURCE_FINISHED_AT="2026-10-15T15:51:48.728Z"
APPROVAL="APPROVE_EXISTING_57_BA_RECEIVER_TEST_ONCE"
PUBLIC_JSON="https://jobs.zarafytek.com/wp-content/uploads/business-analysis-tracker/live-data.json"

def build_snapshot(candidate, now=None):
    rows=candidate.get("records")
    if candidate.get("schema")!="ba-five-source-publication-candidate/v1" or not isinstance(rows,list) or len(rows)!=57:
        raise ValueError("Only existing 57-row audited BA pilot candidate is accepted")
    if len({r.get("id") for r in rows})!=57:
        raise ValueError("Non-unique record IDs")
    if candidate.get("matching_source_advertisements")!=57 or candidate.get("excluded")!=7:
        raise ValueError("Review counts changed")
    if candidate.get("probable_cross_post_pairs")!=2 or candidate.get("unique_display_clusters_provisional")!=55:
        raise ValueError("Duplicate review changed")
    receipts=[{"source":name,"status":"SUCCEEDED","attempted":True} for name in RUN_IDS]
    if not validate_run_receipts(receipts,qa_passed=True)["publish_fresh_five_source_snapshot"]:
        raise ValueError("Incomplete five source receipts")
    check=preflight(candidate,receipts)
    if not check["valid_for_wordpress_delivery"]:
        raise ValueError("BA WordPress quality gate: "+repr(check["issues"]))
    observed=datetime.fromisoformat(LAST_SOURCE_FINISHED_AT.replace("Z","+00:00"))
    at=now or datetime.now(timezone.utc)
    if at.tzinfo is None or not 0 <= (at-observed).total_seconds() <= 36*3600:
        raise ValueError("Source batch too old or clock invalid for controlled receiver test")
    cleaned=[]
    for row in rows:
        r=dict(row)
        src=r.get("source")
        if src not in RUN_IDS or (r.get("source_run_id"),r.get("dataset_id"))!=RUN_IDS[src]:
            raise ValueError("Source/Actor run provenance mismatch")
        r["job_source"]=src
        r["original_advert_url"]=r.get("original_advert_url") or r.get("url")
        r["source_observed_only"]=True
        r["publication_approved"]=False
        cleaned.append(r)
    assert Counter(r["job_source"] for r in cleaned)==Counter({"CV-Library":10,"Totaljobs":10,"Reed UK":7,"Indeed UK":6,"JobServe":24})
    return {"schema":"ba-live-snapshot/v1",
      "quality":{"passed":True,"matched_advertisements":57,"excluded":7,
                 "possible_cross_posts":2,"independently_confirmed_open":False},
      "refresh":{"status":"success","finished_at":LAST_SOURCE_FINISHED_AT,
                 "type":"HISTORICAL_COMPLETED_FIVE_SOURCE_PILOT",
                 "source_observed_not_employer_confirmed":True},
      "sources":[{"source":source,"status":"SUCCEEDED","attempted":True,"run_id":ids[0],
                  "dataset_id":ids[1]} for source,ids in RUN_IDS.items()],
      "records":cleaned}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--send",action="store_true")
    args=p.parse_args()
    doc=build_snapshot(json.loads(CANDIDATE.read_text(encoding="utf8")))
    if not args.send:
        print(json.dumps({"status":"DRY_RUN_PREPARED","records":len(doc["records"]),
                          "source_finished_at":LAST_SOURCE_FINISHED_AT,"wordpress_writes":0}))
        return
    if (os.environ.get("BA_SNAPSHOT_ONE_TIME_APPROVAL")!=APPROVAL
        or os.environ.get("GITHUB_EVENT_NAME")!="push"
        or os.environ.get("GITHUB_REF")!="refs/heads/main"
        or os.environ.get("GITHUB_RUN_ATTEMPT")!="1"):
        raise SystemExit("One-time receiver test launch is not authorised")
    if os.environ.get("BA_WP_USERNAME")!="ba-delivery":
        raise SystemExit("Dedicated restricted BA user required")
    result=send_once(doc,os.environ["BA_WP_USERNAME"],
        os.environ.get("BA_WP_APPLICATION_PASSWORD",""),approved=True)
    if result.get("records")!=57:
        raise RuntimeError("Unexpected receiver acknowledgement record count")
    print(json.dumps({"receiver_accepted":True,"count":57,"sha256":result["sha256"],
                      "wordpress_page_updated":False,"apify_actors_started":0}))
if __name__=="__main__":
    main()
