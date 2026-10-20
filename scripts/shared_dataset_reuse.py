"""Conservative, zero-spend cross-tracker acquisition reuse checks.

Same Actor is NOT sufficient: the complete normalized input and search window
must match. This module never launches Actors, reads tokens or publishes data.
Future shared orchestration may reuse only receipts passing `reusable_receipt`.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SF_PIPELINE = ROOT / "config/pipeline.json"
BA_PIPELINE = ROOT / "business-analysis-tracker/config/automated_refresh_pipeline.json"


def fingerprint(*, provider: str, identifier: str, actor_input: dict, window: dict) -> str:
    """Include every acquisition-affecting parameter, including result limits."""
    if provider not in ("apify_actor", "apify_task"):
        raise ValueError("Only audited Apify Actor or Task runs can be compared")
    if not identifier or not isinstance(actor_input, dict) or not isinstance(window, dict):
        raise ValueError("Missing Actor identity, input or search window")
    if not window.get("since") or not window.get("until"):
        raise ValueError("Both search-window boundaries required for safe reuse")
    canonical = json.dumps(
        {"provider": provider, "identifier": identifier, "input": actor_input,
         "window": window}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def reusable_receipt(request_hash: str, receipt: dict, *, now: datetime,
                     max_age_hours: int = 24) -> bool:
    """Fail closed on missing metadata, unsupported status or unverifiable data.

    `dataset_verified` and `qa_passed` must be populated by the acquiring
    pipeline after a real metadata and QA check, never assumed from an Apify
    SUCCEEDED run or a guessed dataset count.
    """
    if not isinstance(request_hash, str) or len(request_hash) != 64:
        return False
    if not isinstance(receipt, dict) or not isinstance(now, datetime) or now.tzinfo is None:
        return False
    if (receipt.get("request_sha256") != request_hash
            or receipt.get("status") != "SUCCEEDED"
            or receipt.get("dataset_verified") is not True
            or receipt.get("qa_passed") is not True
            or not isinstance(receipt.get("run_id"), str)
            or not receipt["run_id"]
            or not isinstance(receipt.get("dataset_id"), str)
            or not receipt["dataset_id"]
            or not isinstance(receipt.get("dataset_sha256"), str)
            or len(receipt["dataset_sha256"]) != 64):
        return False
    count = receipt.get("dataset_items")
    if type(count) is not int or count < 1:
        return False
    try:
        collected_at = datetime.fromisoformat(receipt["completed_at"].replace("Z", "+00:00"))
    except (ValueError, KeyError, AttributeError):
        return False
    if collected_at.tzinfo is None or not 0 < max_age_hours <= 48:
        return False
    age = now.astimezone(timezone.utc) - collected_at.astimezone(timezone.utc)
    return timedelta(0) <= age <= timedelta(hours=max_age_hours)


def configured_overlap(sf_pipeline=SF_PIPELINE, ba_pipeline=BA_PIPELINE) -> dict:
    """Read-only audit of configured acquisition compatibility.

    A Salesforce saved Task and a BA Actor are deliberately NOT assumed equal.
    Missing run-specific windows mean these are only potential candidates;
    no paid run may be skipped from this audit alone.
    """
    sf = json.loads(Path(sf_pipeline).read_text(encoding="utf-8"))
    ba = json.loads(Path(ba_pipeline).read_text(encoding="utf-8"))
    sf_sources = []
    for entry in sf["sources"]:
        if not entry.get("enabled", True):
            continue
        config_path = ROOT / entry["config"]
        src = json.loads(config_path.read_text(encoding="utf-8"))
        provider = src.get("provider")
        if provider not in ("apify_actor", "apify_task"):
            continue
        sf_sources.append({
            "name": src.get("source_name", entry["name"]),
            "provider": provider,
            "identifier": src.get("actor_id") if provider == "apify_actor" else src.get("task_id"),
            "input": src.get("input", {}),
        })
    matches = []
    same_actor_different_request = []
    for s in sf_sources:
        for b in ba["sources"]:
            if s["provider"] != "apify_actor" or s["identifier"] != b["actor"]:
                continue
            if s["input"] == b.get("input", {}):
                matches.append({"salesforce_source": s["name"], "ba_source": b["name"]})
            else:
                same_actor_different_request.append({
                    "salesforce_source": s["name"], "ba_source": b["name"],
                    "reason": "different search input and/or result limits",
                })
    return {
        "status": "READ_ONLY_NO_ACTORS_LAUNCHED",
        "current_exact_input_matches": matches,
        "same_actor_non_reusable": same_actor_different_request,
        "salesforce_source_count": len(sf_sources),
        "ba_source_count": len(ba["sources"]),
        "current_verified_cost_saving_usd": 0,
        "note": "This is a config-only audit, not evidence of actual completed dataset reuse.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Read-only Salesforce/BA dataset reuse audit")
    p.add_argument("--audit", action="store_true")
    p.parse_args()
    print(json.dumps(configured_overlap(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
