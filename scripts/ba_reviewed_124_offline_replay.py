"""Reconstruct exact user-reviewed 124 from historical five-board observations.

NO automatic role family expansion for future jobs. NO paid Actors/WordPress
calls. This script handles only the exact archived 2026-10-16 batch and
explicitly reconciles source, URL, title and retained reviewed family.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from collections import Counter
from scripts.ba_stage_five_source_data import (
    stage, link, field, company, location, posted, employment, working,
    cleaned_excerpt, sector_catalog, MAPPING, FINAL_SCOPE_DECISIONS
)
from scripts.ba_wordpress_delivery_package import preflight, pack

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/"business-analysis-tracker/evidence/ba-five-completed-20261016-audit-redacted.json"
FAMILIES=ROOT/"business-analysis-tracker/evidence/ba-20261016-reviewed-124-role-families.json"

def replay():
    source=json.loads(ARCHIVE.read_text(encoding="utf8"))
    ledger=json.loads(FINAL_SCOPE_DECISIONS.read_text(encoding="utf8"))
    fam=json.loads(FAMILIES.read_text(encoding="utf8"))
    evidence=json.loads(MAPPING.read_text(encoding="utf8"))
    if (source["date"]!="2026-10-16" or len(source["sources"])!=5 or
        ledger["keep_count"]!=124 or ledger["exclude_count"]!=37 or
        fam["record_count"]!=124 or fam["schema"]!="ba-reviewed-20261016-live-role-families/v1"):
        raise ValueError("Unrecognised historical reviewed batch")
    approved={(x["source"],x["original_advert_url"]):x for x in ledger["decisions"] if x["decision"]=="KEEP"}
    families={(x["source"],x["url"]):x for x in fam["records"]}
    if len(approved)!=124 or len(families)!=124 or set(approved)!=set(families):
        raise ValueError("Reviewed 124 role-family evidence not exact")
    batch={"schema":"ba-five-source-completed-batch/v1","sources":source["sources"]}
    baseline=stage(batch,evidence)
    if baseline["status"]!="FIVE_SOURCES_RECEIVED_STAGED_ONLY":
        raise ValueError("Five-source stage quality gate failed")
    by_key={(x["job_source"],x["original_advert_url"]):x for x in baseline["records"]}
    source_rows={}
    for receipt in source["sources"]:
        for raw in receipt["records"]:
            url=link(raw,receipt["name"])
            key=(receipt["name"],url)
            if key in source_rows:raise ValueError("Source advert duplicate")
            source_rows[key]=(receipt,raw)
    if len(source_rows)!=161 or not set(approved).issubset(source_rows):
        raise ValueError("Historical source identity mismatch")
    sectors=sector_catalog(evidence)
    result=[]
    for key,entry in approved.items():
        receipt,raw=source_rows[key]
        role=families[key]
        title=field(raw,"title","jobTitle")
        if not title or title!=entry["title"] or title!=role["title"]:
            raise ValueError("Source title changed after reviewer approval")
        if key in by_key:
            row=dict(by_key[key])
        else:
            url=key[1]
            advertiser=company(raw)
            sector=sectors.get(advertiser.casefold())
            row={
                "id":hashlib.sha256(url.encode("utf8")).hexdigest()[:24],
                "title":title[:240],
                "advertiser":advertiser[:180],
                "location":location(raw)[:160],
                "job_source":receipt["name"],
                "original_advert_url":url,
                "source_run_id":receipt["run_id"],
                "dataset_id":receipt["dataset_id"],
                "observed_at":receipt["observed_at"],
                "posted_date":posted(raw),
                "employment":employment(raw),
                "working_arrangement":working(raw),
                "description_summary":cleaned_excerpt(raw),
                "skills":[],
                "sector":sector["sector"] if sector else "Not specified",
                "sector_basis":sector["basis"] if sector else "UNKNOWN_NO_EVIDENCE",
                "sector_evidence_url":sector["evidence_url"] if sector else None,
                "end_client_sector":"Not specified",
                "source_observed_only":True
            }
        row["role_family"]=role["role_family"]
        row["track"]=role["track"]
        row["scope_review_provenance"]="EXACT_20261016_APPROVED_ADVERT"
        row["source"]=row["job_source"]
        row["url"]=row["original_advert_url"]
        row["sector_display"]=row["sector"]
        row["publication_approved"]=False
        result.append(row)
    if len(result)!=124 or len({(x["source"],x["url"]) for x in result})!=124:
        raise ValueError("Reviewed record count mismatch")
    receipts=[{"source":s["name"],"status":s["status"],"attempted":s["attempted"]} for s in source["sources"]]
    candidate={"schema":"ba-dryrun-wordpress-candidate/v1",
               "records":result,"publication_approved":False,
               "source_observed_only":True}
    gate=preflight(candidate,receipts)
    if not gate["valid_for_wordpress_delivery"]:
        raise ValueError("Receiver payload contract rejected: "+str(gate["issues"]))
    package=pack(candidate,receipts)
    if package["delivery_approved"] is not False:
        raise ValueError("Unexpected publication authorisation")
    return {
       "status":"REVIEWED_124_OFFLINE_READY_NOT_FRESH_NOT_PUBLISHED",
       "source_records":len(source_rows),
       "approved_records":len(result),
       "excluded_records":37,
       "baseline_automatic_records":len(by_key),
       "reviewed_exact_override_records":len(result)-len(by_key),
       "actor_runs_started":0,"wordpress_requests":0,
       "preview_sha256":package["sha256"],
       "candidate":candidate,
       "package":package
    }

if __name__=="__main__":
    r=replay()
    print(json.dumps({k:v for k,v in r.items() if k not in ("candidate","package")},sort_keys=True))
