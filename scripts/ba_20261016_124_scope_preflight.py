"""One-time read-only publication preflight for 124 title-in-scope source adverts.

Uses the original 161 already-paid, privacy-trimmed observations and the exact
39 advert URLs explicitly kept by the user. No network, Actor POST, WordPress
delivery or changes to source taxonomy. Do not run as a paid collector.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.ba_stage_five_source_data import (
    stage, field, company, location, employment, working, posted,
    cleaned_excerpt, link, sector_catalog, MAPPING,
)
from scripts.ba_wordpress_delivery_package import preflight
from scripts.ba_recurring_cycle import build_live_document
from scripts.validate_ba_five_source_contract import validate_run_receipts

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "business-analysis-tracker/evidence/ba-five-completed-20261016-audit-redacted.json"
REVIEW = ROOT / "business-analysis-tracker/evidence/ba-20261016-user-approved-39-scope.json"
OBSERVED_COUNTS={"CV-Library":30,"Totaljobs":25,"Reed UK":30,"Indeed UK":30,"JobServe":46}

def candidate():
    doc=json.loads(DATA.read_text(encoding="utf8"))
    review=json.loads(REVIEW.read_text(encoding="utf8"))
    if (doc.get("schema")!="ba-offline-actor-observations/v1" or
        doc.get("publication_approved") is not False or
        review.get("not_a_publication_approval") is not True or
        review.get("exact_matched_advertisements")!=39):
        raise ValueError("Evidence or scope-review provenance changed")
    receipts=doc["sources"]
    if ({r["name"] for r in receipts} != set(OBSERVED_COUNTS)
        or len(receipts)!=5 or
        any(len(r["records"])!=OBSERVED_COUNTS[r["name"]] or
            r["status"]!="SUCCEEDED" or not r.get("run_id") or not r.get("dataset_id")
            or not r.get("observed_at") for r in receipts)):
        raise ValueError("Not the completed five-source dataset")
    # Actor documented page-sized overfetch is a separate limit, not
    # equivalent to a 30-row exact output promise.
    if OBSERVED_COUNTS["JobServe"]>60:
        raise ValueError("JobServe above proposed bounded observed ceiling")
    mapping=json.loads(MAPPING.read_text(encoding="utf8"))
    sectors=sector_catalog(mapping)
    official=stage({"schema":"ba-five-source-completed-batch/v1","sources":receipts},mapping)
    if official["status"]!="FIVE_SOURCES_RECEIVED_STAGED_ONLY":
        raise ValueError("Official 22-family staging did not pass")
    baseline=official["records"]
    if len(baseline)!=87:
        raise ValueError("The reviewed 87-record candidate baseline has changed")
    by_url={r["original_advert_url"]:dict(r) for r in baseline}
    if len(by_url)!=87:
        raise ValueError("Duplicate exact URL in reviewed baseline")
    user_rows=review["records"]
    if len(user_rows)!=39 or any(r.get("user_role_scope_decision")!="IN_SCOPE_KEEP"
                                for r in user_rows):
        raise ValueError("Manual review is incomplete")
    # Totaljobs exports occasionally duplicate its absolute site URL prefix.
    # Compare both the review register and raw records via the existing
    # source-specific URL normalizer; preserve the original advert identity.
    def normalize_review_url(entry):
        value=entry["original_advert_url"]
        normalized=link({"canonicalUrl":value,"jobUrl":value,"url":value,
                         "sourceUrl":value,"applyUrl":value},entry["source"])
        if not normalized:
            raise ValueError("Unsafe original user-approved advert URL")
        return normalized.rstrip("/")
    registered={(r["source"],normalize_review_url(r)):r for r in user_rows}
    if len(registered)!=39:
        raise ValueError("Scope register has duplicate source URLs")

    all_seen=set()
    new_rows=[]
    intersection=[]
    by_source=Counter()
    for source in receipts:
        name=source["name"]
        for raw in source["records"]:
            original=link(raw,name)
            title=field(raw,"title","jobTitle")
            if not original or not title:
                # Unsafe rows never become eligible through a scope override.
                continue
            key=(name,original.rstrip("/"))
            if key in all_seen:
                raise ValueError("Exact advert URL duplicate across collected sources")
            all_seen.add(key)
            user=registered.get(key)
            if not user:
                continue
            if title != user["original_job_title"] or user["source"]!=name:
                raise ValueError("Scope approval does not match original title and source")
            if original in by_url:
                intersection.append(original)
                by_url[original]["user_scope_approved"]=True
                by_url[original]["scope_review_provenance"]="EXACT_USER_ADVERT_URL"
                by_url[original]["proposed_reviewer_family"]=user["proposed_role_family"]
                continue
            # Build 37 extra rows using the SAME source/URL/date/sector functions
            # as official staging. This is a manual inclusion override, not
            # an assertion that the source's advert remains open.
            advertiser=company(raw)
            sector_ev=sectors.get(advertiser.casefold())
            row={
                "id":hashlib.sha256(original.encode("utf8")).hexdigest()[:24],
                "title":title[:240],"advertiser":advertiser[:180],
                "location":location(raw)[:160],
                "job_source":name,"source":name,
                "url":original,"original_advert_url":original,
                "source_run_id":source["run_id"],"dataset_id":source["dataset_id"],
                "observed_at":source["observed_at"],
                "posted_date":posted(raw),"employment":employment(raw),
                "working_arrangement":working(raw),
                "role_family":user["proposed_role_family"],"track":"REVIEWER_EXTENDED_SCOPE",
                "role_review_required":True,
                "description_summary":cleaned_excerpt(raw),
                "skills":[],"sector":sector_ev["sector"] if sector_ev else "Not specified",
                "sector_display":sector_ev["sector"] if sector_ev else "Not specified",
                "sector_basis":sector_ev["basis"] if sector_ev else "UNKNOWN_NO_EVIDENCE",
                "sector_evidence_url":sector_ev["evidence_url"] if sector_ev else None,
                "end_client_sector":"Not specified",
                "source_observed_only":True,
                "source_title_scope_decision":"IN_SCOPE_KEEP",
                "scope_review_provenance":"EXACT_USER_ADVERT_URL",
                "user_scope_approved":True,"publication_approved":False,
            }
            by_url[original]=row
            new_rows.append(row)
            by_source[name]+=1
    missing=set(registered)-all_seen
    if missing:
        raise ValueError("Manual review contains unknown source records: "+str(missing)[:180])
    if len(intersection)!=2 or len(new_rows)!=37 or len(by_url)!=124:
        raise ValueError("Manual approval overlap/union differs from 2/37/124")
    # Adapt all official rows to the WordPress dry-run contract.
    records=[]
    for r in by_url.values():
        row=dict(r)
        row["source"]=row["job_source"]
        row["url"]=row["original_advert_url"]
        row["sector_display"]=row["sector"]
        row["publication_approved"]=False
        row.setdefault("user_scope_approved",False)
        records.append(row)
    records.sort(key=lambda r:(r.get("posted_date") or "",r["title"].casefold()),reverse=True)
    valid=preflight({"records":records},[
        {"source":s["name"],"attempted":s["attempted"],"status":s["status"]}
        for s in receipts])
    if valid["valid_for_wordpress_delivery"] is not True:
        raise ValueError("Candidate preflight failed: "+str(valid["issues"]))
    preview=build_live_document(
        {"sources":receipts},
        {"status":"DRY_RUN_PASS_NOT_PUBLISHED",
         "candidate":{"records":records,"publication_approved":False},
         "rejected":official["rejected"]},
        datetime(2026,10,16,14,0,tzinfo=timezone.utc))
    if len(preview["records"])!=124:
        raise ValueError("Offline live-schema preview missing records")
    families=Counter(r["role_family"] for r in records)
    sectors_evidenced=sum(r["sector"]!="Not specified" for r in records)
    working_known=sum(r["working_arrangement"]!="Not specified" for r in records)
    posting_known=sum(bool(r["posted_date"]) for r in records)
    return {
        "schema":"ba-20261016-reviewed-scope-preflight/v1",
        "status":"STAGED_NOT_PUBLISHED",
        "total_raw_sources":161,"automatic_22_family_matches":87,
        "user_kept_adverts":39,"already_in_baseline":len(intersection),
        "newly_in_scope":len(new_rows),"combined_in_scope":len(records),
        "remaining_not_kept":161-len(records),
        "source_observed_only":True,"employer_openings_independently_verified":False,
        "publication_approved":False,
        "actor_runs_started":0,"wordpress_requests":0,
        "five_source_receipt_gate_passed":True,
        "live_payload_schema_preflight_passed":True,
        "source_counts":dict(Counter(r["source"] for r in records)),
        "role_families":dict(families.most_common()),
        "role_family_count":len(families),
        "sector_evidenced":sectors_evidenced,
        "working_known":working_known,"source_posted_dates_known":posting_known,
        "new_manual_role_families":sorted(set(x["role_family"] for x in new_rows)),
        "specific_new_advert_urls":len(new_rows),
        "needs_manual_family_review":len(new_rows),
    }

def main():
    import sys
    result=candidate()
    print("BA_REVIEWED_SCOPE_PREFLIGHT "+json.dumps(result,sort_keys=True))
    if result["combined_in_scope"]!=124:
        sys.exit(1)

if __name__=="__main__":
    main()
