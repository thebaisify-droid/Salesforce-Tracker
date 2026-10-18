"""Publish *existing*, quality-checked 18 Oct BA datasets exactly once.

No Actor start endpoints, no paid acquisition and no recurring enablement.
All five previously completed Actor runs are re-read using GET only.
The quality result must match the 18 Oct independently audited fingerprint.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo

from scripts.ba_readonly_oct18_qa import RUNS, LIMITS, fetch
from scripts.ba_completed_dataset_handoff import build_batch
from scripts.ba_e2e_offline import run_offline
from scripts.ba_stage_five_source_data import MAPPING
from scripts.ba_recurring_cycle import build_live_document
from scripts.ba_atomic_snapshot_sender import send_once

APPROVAL = "EXISTING_COMPLETED_DATASETS_ONLY_OCT18"
TRIGGER = "[BA-EXISTING-SNAPSHOT-ONCE-20261018]"
AUDITED_SHA256 = "02a2650e81506f5716caf908443f5c4b3dd54aa1d662e807c0996e52ba1da7f6"
AUDITED_REJECTIONS = {
    "out_of_scope": 28,
    "scope_review_required_not_auto_published": 2,
    "user_explicitly_excluded_advert": 9,
}
AUDITED_BY_SOURCE = {
    "CV-Library": 30, "Totaljobs": 25, "Reed UK": 30,
    "Indeed UK": 30, "JobServe": 44,
}


def check_approval(env: dict, now: datetime) -> None:
    if (env.get("BA_EXISTING_DATASET_PUBLISH_APPROVAL") != APPROVAL
            or env.get("BA_WP_DELIVERY_APPROVAL") != "EXPLICIT_APPROVAL"
            or env.get("GITHUB_EVENT_NAME") != "push"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"
            or not env.get("GITHUB_COMMIT_MESSAGE", "").startswith(TRIGGER)):
        raise ValueError("Not the singly authorised 18 Oct completed-dataset publication")
    if now.tzinfo is None or now.astimezone(ZoneInfo("Europe/London")).date() != date(2026, 10, 18):
        raise ValueError("One-time completed dataset authorisation has expired")
    if (not env.get("APIFY_TOKEN") or not env.get("BA_WP_USERNAME")
            or not env.get("BA_WP_APPLICATION_PASSWORD")):
        raise ValueError("Missing read-only dataset or dedicated WordPress credentials")


def verify_qa(batch: dict, result: dict) -> None:
    counts = {r.get("name"): len(r.get("records", [])) for r in batch.get("sources", [])}
    if (counts != AUDITED_BY_SOURCE
            or result.get("status") != "DRY_RUN_PASS_NOT_PUBLISHED"
            or result.get("raw_source_rows") != 159
            or result.get("matched") != 120
            or result.get("rejected") != AUDITED_REJECTIONS
            or result.get("preview_sha256") != AUDITED_SHA256):
        raise ValueError("Previously audited five-source dataset has changed: no WordPress write")


def run_once(env: dict, now: datetime, *, getter=fetch, sender=send_once) -> dict:
    check_approval(env, now)
    batch = build_batch(
        RUNS, env["APIFY_TOKEN"], get=getter, max_per_source=100,
        max_items_by_source=LIMITS,
    )
    qa = run_offline(batch, json.loads(MAPPING.read_text(encoding="utf8")))
    verify_qa(batch, qa)
    live = build_live_document(batch, qa, datetime.now(timezone.utc))
    if live.get("schema") != "ba-live-snapshot/v1" or len(live.get("records", [])) != 120:
        raise ValueError("WordPress snapshot contract mismatch: no write")
    ack = sender(live, env["BA_WP_USERNAME"], env["BA_WP_APPLICATION_PASSWORD"], approved=True)
    if ack.get("accepted") is not True or ack.get("records") != 120 or not ack.get("sha256"):
        raise ValueError("Receiver did not acknowledge the exact source-count snapshot")
    return {
        "status": "PUBLISHED_RECEIVER_CONFIRMED",
        "existing_source_records": 159,
        "qa_matched": 120,
        "actor_runs_started": 0,
        "paid_acquisition_requests": 0,
        "wordpress_delivery_requests": 1,
        "receiver_ack_records": ack["records"],
        "receiver_sha256": ack["sha256"],
        "source_observed_not_employer_confirmed": True,
    }


def main() -> None:
    result = run_once(dict(os.environ), datetime.now(timezone.utc))
    print("BA_EXISTING_DATASET_PUBLISH " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
