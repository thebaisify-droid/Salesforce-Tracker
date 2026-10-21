"""Verify an existing Apify run via GET only and append its raw dataset digest.

This adapter never starts an Actor and cannot publish a WordPress snapshot.
The existing production collectors are not modified. Actual Actor run INPUT
must equal the full fingerprinted request, otherwise no reuse is permitted.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import re
from hashlib import sha256

from scripts.shared_acquisition_ledger import (
    ID, SharedLedger, apify_get_only, record_verified, validated_request)


def intake_existing(request, *, ledger: SharedLedger, run_id, actor_id,
                    maximum_items, getter, source_quality):
    digest = validated_request(request)
    if (not isinstance(run_id, str) or not ID.fullmatch(run_id)
            or not isinstance(actor_id, str) or not ID.fullmatch(actor_id)
            or type(maximum_items) is not int or not 1 <= maximum_items <= 1000
            or not callable(source_quality)):
        raise ValueError("Incomplete source identity, result cap or QA")
    run = getter("actor-runs/" + run_id)
    if (not isinstance(run, dict) or run.get("status") != "SUCCEEDED"
            or run.get("actId") != actor_id):
        raise ValueError("Completed run Actor identity mismatch")
    dataset, store = run.get("defaultDatasetId"), run.get("defaultKeyValueStoreId")
    if (not isinstance(dataset, str) or not ID.fullmatch(dataset)
            or not isinstance(store, str) or not ID.fullmatch(store)):
        raise ValueError("No verified dataset or original INPUT store")
    stored_input = getter("key-value-stores/" + store + "/records/INPUT")
    if not isinstance(stored_input, dict):
        raise ValueError("Cannot authenticate original run input")
    intended = dict(request["actor_input"])
    task_id = None
    if request["provider"] == "apify_task":
        task_id = run.get("actTaskId")
        if not isinstance(task_id, str) or not ID.fullmatch(task_id):
            raise ValueError("Saved Task run identity missing")
        task = getter("actor-tasks/" + request["identifier"].replace("/", "~"))
        if (not isinstance(task, dict) or task.get("id") != task_id
                or task.get("actId") != actor_id):
            raise ValueError("Saved Task identity was changed")
        expected_sha = intended.pop("_resolved_task_input_sha256")
        canonical = json.dumps(stored_input, sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False).encode()
        if sha256(canonical).hexdigest() != expected_sha:
            raise ValueError("Saved Task effective input digest mismatch")
    if stored_input != intended:
        raise ValueError("Remote effective input differs from requested Actor input")
    try:
        completed = datetime.fromisoformat(run["finishedAt"].replace("Z", "+00:00"))
        since = datetime.fromisoformat(request["window"]["since"].replace("Z", "+00:00"))
        until = datetime.fromisoformat(request["window"]["until"].replace("Z", "+00:00"))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise ValueError("Acquisition window or timestamp invalid") from None
    if (any(d.tzinfo is None for d in (since, until, completed))
            or not since < until <= completed + timedelta(minutes=2)
            or completed > datetime.now(timezone.utc) + timedelta(minutes=2)):
        raise ValueError("Acquisition date boundaries not proven")
    meta = getter("datasets/" + dataset)
    count = meta.get("itemCount") if isinstance(meta, dict) else None
    if type(count) is not int or not 1 <= count <= maximum_items:
        raise ValueError("Dataset count violates approved maximum")
    rows = getter("datasets/" + dataset + "/items?clean=false&offset=0&limit=" + str(count))
    if not isinstance(rows, list) or len(rows) != count or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Raw dataset missing, partial or malformed")
    if source_quality(rows) is not True:
        raise ValueError("Raw source did not pass independent quality gate")
    metadata = {
        "identifier": request["identifier"], "provider": request["provider"],
        "verified_request_sha256": digest, "status": "SUCCEEDED",
        "dataset_verified": True, "qa_passed": True,
        "run_id": run_id, "dataset_id": dataset, "apify_actor_id": actor_id,
        "dataset_items": count, "approved_max_items": maximum_items,
        "completed_at": run["finishedAt"],
    }
    if task_id is not None:
        metadata["apify_task_id"] = task_id
    receipt = record_verified(request, metadata, rows)
    appended = ledger.append(receipt)
    return {"status": "READ_ONLY_COMPLETED_RUN_VERIFIED_NOT_PUBLISHED",
            "new_receipt": appended, "run_id": run_id, "dataset_id": dataset,
            "dataset_items": count, "actors_started": 0, "wordpress_requests": 0}


def raw_quality(rows):
    """Conservative source-level gate; both downstream classifier gates still run."""
    from urllib.parse import urlsplit
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        if not isinstance(row, dict):
            return False
        title = next((row.get(k) for k in ("title", "jobTitle", "title_raw", "job_title")
                      if isinstance(row.get(k), str) and row.get(k).strip()), None)
        advert = next((row.get(k) for k in ("url", "jobUrl", "canonicalUrl", "sourceUrl")
                       if isinstance(row.get(k), str) and row.get(k).strip()), None)
        if title is None or advert is None:
            return False
        parsed = urlsplit(advert)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
    return True
