"""Single authorised, delivery-only handoff of 16 Oct reviewed BA vacancies.

No Apify token, no Actor POST, no retries. Requires an exact one-time push
event on the isolated review branch; fail closed on stale observations.
"""
from __future__ import annotations
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.ba_20261016_124_scope_preflight import candidate
from scripts.ba_atomic_snapshot_sender import envelope, send_once
from scripts.ba_delivery_credentials_readonly import check as credentials_preflight

FINISHED_AT="2026-10-16T10:35:40.217Z"
EXACT_COMMIT_MESSAGE="[BA-PUBLISH-REVIEWED-124-ONCE-20261016]"
EXPECTED_BRANCH="refs/heads/audit/ba-paid-datasets-20261016-offline"

def gate(now:datetime, environ:dict)->dict:
    if now.tzinfo is None:
        raise ValueError("Timezone-aware now required")
    finished=datetime.fromisoformat(FINISHED_AT.replace("Z","+00:00"))
    elapsed=now.astimezone(timezone.utc)-finished
    if elapsed < timedelta(0) or elapsed >= timedelta(hours=35,minutes=30):
        raise RuntimeError("Source observations are outside the safe publication freshness margin")
    if (environ.get("GITHUB_EVENT_NAME")!="push"
        or environ.get("GITHUB_REF")!=EXPECTED_BRANCH
        or environ.get("GITHUB_RUN_ATTEMPT")!="1"
        or environ.get("BA_TRIGGER_MESSAGE")!=EXACT_COMMIT_MESSAGE
        or environ.get("BA_WP_DELIVERY_APPROVAL")!="EXPLICIT_APPROVAL"):
        raise RuntimeError("Trusted one-time delivery event/approval missing")
    if environ.get("APIFY_TOKEN"):
        raise RuntimeError("No Apify credentials are permitted for this delivery-only job")
    return {"mode":"ONE_TIME_DELIVERY","age_hours":round(elapsed.total_seconds()/3600,3)}

def main():
    state=gate(datetime.now(timezone.utc),os.environ)
    report, doc=candidate(return_snapshot=True)
    if (report["combined_in_scope"]!=124 or report["newly_in_scope"]!=37
        or report["already_in_baseline"]!=2 or report["total_raw_sources"]!=161
        or report["actor_runs_started"]!=0 or report["wordpress_requests"]!=0
        or report["live_payload_schema_preflight_passed"] is not True
        or len(doc["records"])!=124 or len(doc["sources"])!=5
        or datetime.fromisoformat(doc["refresh"]["finished_at"].replace("Z","+00:00")) != datetime.fromisoformat(FINISHED_AT.replace("Z","+00:00"))
        or doc["quality"]["passed"] is not True):
        raise RuntimeError("Payload provenance, coverage or QA gates failed")
    digest=envelope(doc)["sha256"]
    print("DELIVERY_ONLY_PREFLIGHT "+json.dumps({
        "status":"QA_PASSED_NOT_SENT","actor_runs_started":0,
        "source_records":161,"submitted_records":124,"sha256":digest,
        "source_timestamp":FINISHED_AT,"freshness_age_hours":state["age_hours"]
    },sort_keys=True),flush=True)
    # No WordPress mutation before restricted user + endpoint checks pass.
    credentials_preflight()
    print("DELIVERY_ONLY_SUBMITTING "+json.dumps({
        "status":"SINGLE_WORDPRESS_POST_STARTING",
        "submitted_records":124,"sha256":digest
    },sort_keys=True),flush=True)
    # Exactly one network POST. On HTTP error/timeout, STOP: inspect live
    # receiver before any attempt to retry, since it may already be stored.
    result=send_once(doc,os.environ.get("BA_WP_USERNAME",""),
                     os.environ.get("BA_WP_APPLICATION_PASSWORD",""),approved=True)
    if result.get("records")!=124 or result.get("sha256")!=digest:
        raise RuntimeError("WordPress receiver acknowledgment mismatch; do not retry")
    print("DELIVERY_ONLY_RESULT "+json.dumps({
        "status":"PUBLISHED_RECEIVER_CONFIRMED","records_submitted":124,
        "actor_runs_started":0,"sha256":digest
    },sort_keys=True),flush=True)

if __name__=="__main__":
    main()
