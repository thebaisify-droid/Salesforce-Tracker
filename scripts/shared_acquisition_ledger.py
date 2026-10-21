"""Fail-closed, metadata-only shared Apify dataset ledger and read-only replay.

Does not launch Actors, mutate WordPress, or bypass Salesforce/BA QA. The
acquisition runner must independently check real Apify run/dataset metadata
and the raw source QA before calling record_verified.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import fcntl
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.request import Request, urlopen

from scripts.shared_dataset_reuse import fingerprint, reusable_receipt

SCHEMA = "shared-acquisition-ledger/v1"
ID = re.compile(r"[A-Za-z0-9_-]{6,100}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
PRIVATE = re.compile(r"token|password|secret|api.?key|authorization|cookie|credential", re.I)


def rows_sha256(rows):
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Complete non-empty list of raw source records is required")
    return sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def validated_request(request):
    if not isinstance(request, dict) or set(request) != {
            "provider", "identifier", "actor_input", "window"}:
        raise ValueError("Exact input and search window required")
    def guard(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if not isinstance(k, str) or PRIVATE.search(k):
                    raise ValueError("Do not put secrets in shared acquisition requests")
                guard(v)
        if isinstance(obj, list):
            for x in obj:
                guard(x)
    guard(request["actor_input"])
    guard(request["window"])
    if request["provider"] == "apify_task":
        # The saved Task can change underneath its stable name. Reuse requires
        # a digest of the *resolved Task input* alongside the actual query.
        digest = request["actor_input"].get("_resolved_task_input_sha256")
        if not isinstance(digest, str) or not HEX.fullmatch(digest):
            raise ValueError("Saved Task input/version has not been resolved")
    return fingerprint(**request)


def validate_receipt(record):
    if not isinstance(record, dict) or not isinstance(record.get("request"), dict):
        raise ValueError("Missing acquisition request")
    digest = validated_request(record["request"])
    if record.get("request_sha256") != digest:
        raise ValueError("Acquisition fingerprint mismatch")
    if (record.get("status") != "SUCCEEDED"
            or record.get("dataset_verified") is not True
            or record.get("qa_passed") is not True
            or not isinstance(record.get("dataset_sha256"), str)
            or not HEX.fullmatch(record["dataset_sha256"])
            or not isinstance(record.get("apify_actor_id"), str)
            or not ID.fullmatch(record["apify_actor_id"])):
        raise ValueError("Run/dataset evidence or QA approval missing")
    for field in ("run_id", "dataset_id"):
        if not isinstance(record.get(field), str) or not ID.fullmatch(record[field]):
            raise ValueError("Invalid immutable " + field)
    count, maximum = record.get("dataset_items"), record.get("approved_max_items")
    if type(count) is not int or type(maximum) is not int or not 1 <= count <= maximum <= 1000:
        raise ValueError("Dataset count outside approved item cap")
    if record["request"]["provider"] == "apify_task":
        if not isinstance(record.get("apify_task_id"), str) or not ID.fullmatch(record["apify_task_id"]):
            raise ValueError("Missing resolved Task identity")
    try:
        finished = datetime.fromisoformat(record["completed_at"].replace("Z", "+00:00"))
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ValueError("Invalid completion timestamp") from None
    if finished.tzinfo is None or finished > datetime.now(timezone.utc):
        raise ValueError("Completion timestamp must be timezone-aware and not in future")


def record_verified(request, metadata, rows):
    """Build a receipt from previously verified source metadata and QA evidence.

    Never auto-approves data; callers must have confirmed full run, task/Actor
    identity, dataset count, untruncated rows and source QA externally.
    """
    digest = validated_request(request)
    if (not isinstance(metadata, dict)
            or metadata.get("verified_request_sha256") != digest
            or metadata.get("identifier") != request["identifier"]
            or metadata.get("provider") != request["provider"]
            or metadata.get("status") != "SUCCEEDED"
            or metadata.get("dataset_verified") is not True
            or metadata.get("qa_passed") is not True
            or type(metadata.get("dataset_items")) is not int
            or metadata["dataset_items"] != len(rows)):
        raise ValueError("Source identity, query, dataset completeness or QA not verified")
    receipt = {
        "request": request, "request_sha256": digest,
        "status": "SUCCEEDED", "dataset_verified": True, "qa_passed": True,
        "run_id": metadata.get("run_id"), "dataset_id": metadata.get("dataset_id"),
        "apify_actor_id": metadata.get("apify_actor_id"),
        "dataset_items": metadata["dataset_items"],
        "approved_max_items": metadata.get("approved_max_items"),
        "dataset_sha256": rows_sha256(rows),
        "completed_at": metadata.get("completed_at"),
    }
    if request["provider"] == "apify_task":
        receipt["apify_task_id"] = metadata.get("apify_task_id")
    validate_receipt(receipt)
    return receipt


class SharedLedger:
    """Atomic append under a local filesystem lock. Needs a durable shared store
    before activation across separate GitHub Actions runners.
    """
    def __init__(self, path="state/shared_acquisition_ledger.json"):
        self.path = Path(path)

    def _read(self):
        if not self.path.exists():
            return []
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        if (not isinstance(doc, dict) or doc.get("schema") != SCHEMA
                or not isinstance(doc.get("receipts"), list)):
            raise ValueError("Invalid ledger schema")
        runs = set()
        for row in doc["receipts"]:
            validate_receipt(row)
            if row["run_id"] in runs:
                raise ValueError("Duplicate ledger run identity")
            runs.add(row["run_id"])
        return doc["receipts"]

    def read(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                return self._read()
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def append(self, receipt):
        validate_receipt(receipt)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix(".lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                records = self._read()
                for old in records:
                    if old["run_id"] == receipt["run_id"]:
                        if old == receipt:
                            return False
                        raise ValueError("Immutable run receipt rewrite blocked")
                    if old["dataset_id"] == receipt["dataset_id"]:
                        raise ValueError("Dataset identity already registered")
                payload = json.dumps({"schema": SCHEMA, "receipts": records + [receipt]},
                                     sort_keys=True, indent=2) + "\n"
                temp = None
                try:
                    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                        dir=self.path.parent, prefix=".shared-", delete=False) as handle:
                        temp = handle.name
                        handle.write(payload)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.chmod(temp, 0o600)
                    os.replace(temp, self.path)
                finally:
                    if temp and os.path.exists(temp):
                        os.unlink(temp)
                return True
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def find(self, request, *, now, max_age_hours=24):
        h = validated_request(request)
        candidates = [r for r in self.read() if reusable_receipt(
            h, r, now=now, max_age_hours=max_age_hours)]
        return max(candidates, key=lambda r: r["completed_at"]) if candidates else None


def apify_get_only(endpoint, token):
    """The ONLY network helper here: Apify GET metadata/dataset items."""
    allowed = (
        re.fullmatch(r"actor-runs/[A-Za-z0-9_-]{6,100}", endpoint) or
        re.fullmatch(r"datasets/[A-Za-z0-9_-]{6,100}", endpoint) or
        re.fullmatch(r"datasets/[A-Za-z0-9_-]{6,100}/items\?clean=false&offset=0&limit=[0-9]{1,4}", endpoint)
    )
    if not allowed or not isinstance(token, str) or not token:
        raise ValueError("Only authenticated read-only Apify GET endpoints permitted")
    request = Request("https://api.apify.com/v2/" + endpoint, method="GET", headers={
        "Authorization": "Bearer " + token, "Accept": "application/json"})
    with urlopen(request, timeout=35) as response:
        payload = json.load(response)
    if "/items?" in endpoint:
        if not isinstance(payload, list):
            raise ValueError("Expected dataset row list")
        return payload
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Missing Apify metadata envelope")
    return payload["data"]


def replay_verified(request, ledger, getter, *, now, max_age_hours=24):
    """Return full untouched raw rows to each *independent* tracker consumer.

    The returned records are NOT cleared for publication; downstream Salesforce
    and BA taxonomy/QA/deduplication gates still apply separately.
    """
    receipt = ledger.find(request, now=now, max_age_hours=max_age_hours)
    if receipt is None:
        raise ValueError("No exact, fresh, QA-passed dataset available for reuse")
    run_id, dataset_id = receipt["run_id"], receipt["dataset_id"]
    remote = getter("actor-runs/" + run_id)
    if (not isinstance(remote, dict) or remote.get("status") != "SUCCEEDED"
            or remote.get("defaultDatasetId") != dataset_id
            or remote.get("actId") != receipt["apify_actor_id"]):
        raise ValueError("Original Apify run identity/status changed")
    if request["provider"] == "apify_task" and remote.get("actTaskId") != receipt["apify_task_id"]:
        raise ValueError("Saved Task identity changed")
    try:
        original = datetime.fromisoformat(receipt["completed_at"].replace("Z", "+00:00"))
        live = datetime.fromisoformat(remote["finishedAt"].replace("Z", "+00:00"))
    except (ValueError, KeyError, AttributeError):
        raise ValueError("Remote completion time invalid") from None
    if live.tzinfo is None or abs((live - original).total_seconds()) > 1:
        raise ValueError("Apify run completion timestamp changed")
    source = getter("datasets/" + dataset_id)
    if (not isinstance(source, dict) or type(source.get("itemCount")) is not int
            or source["itemCount"] != receipt["dataset_items"]):
        raise ValueError("Dataset metadata/count changed")
    count = receipt["dataset_items"]
    rows = getter("datasets/" + dataset_id +
                  "/items?clean=false&offset=0&limit=" + str(count))
    if not isinstance(rows, list) or len(rows) != count or rows_sha256(rows) != receipt["dataset_sha256"]:
        raise ValueError("Dataset is partial, stale or mutated; fail closed")
    return {"status": "VERIFIED_READONLY_NOT_PUBLISHED", "rows": rows,
            "run_id": run_id, "dataset_id": dataset_id, "actors_started": 0}
