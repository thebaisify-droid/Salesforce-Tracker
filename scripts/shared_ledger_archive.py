"""Portable, integrity-checked persistence of the shared metadata-only ledger.

Archives can be uploaded as one GitHub Actions artifact and restored by a
future single, serialised acquisition workflow. Does not handle raw ads,
APIFY_TOKEN, credentials or database snapshots.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import zipfile

from scripts.shared_acquisition_ledger import SCHEMA, SharedLedger

ARCHIVE_SCHEMA = "shared-acquisition-archive/v1"
LEDGER_MEMBER = "state/shared_acquisition_ledger.json"
MANIFEST_MEMBER = "state/shared_acquisition_manifest.json"
MAX_ARCHIVE_BYTES = 5 * 1024 * 1024
MAX_LEDGER_BYTES = 3 * 1024 * 1024


def _archive_ledger_bytes(ledger: SharedLedger) -> bytes:
    # Use the ledger read+parse validation before snapshot; the temporary
    # snapshot is self-consistent even while new receipts are appended.
    rows = ledger.read()
    encoded = json.dumps({"schema": SCHEMA, "receipts": rows},
                         indent=2, sort_keys=True, ensure_ascii=False).encode()
    if len(encoded) > MAX_LEDGER_BYTES:
        raise ValueError("Ledger exceeds conservative metadata size limit")
    return encoded


def make_archive(ledger: SharedLedger, output: str | Path) -> dict:
    output = Path(output)
    ledger_data = _archive_ledger_bytes(ledger)
    manifest = {
        "schema": ARCHIVE_SCHEMA,
        "ledger_file": LEDGER_MEMBER,
        "ledger_sha256": sha256(ledger_data).hexdigest(),
        "ledger_bytes": len(ledger_data),
        "receipts": len(ledger.read()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contains_raw_adverts": False,
    }
    # A racing appended receipt must not make count inaccurate. Count is
    # calculated from the immutable bytes being archived, not a later read.
    manifest["receipts"] = len(json.loads(ledger_data)["receipts"])
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(LEDGER_MEMBER, ledger_data)
        archive.writestr(MANIFEST_MEMBER,
                         json.dumps(manifest, indent=2, sort_keys=True).encode())
    data = buffer.getvalue()
    if len(data) > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive exceeds safe size limit")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".shared-archive-",
                                         delete=False) as handle:
            tmp = handle.name
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, output)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return manifest


def restore_archive(archive_path: str | Path, ledger: SharedLedger, *,
                    require_empty: bool = True) -> dict:
    """Fail-closed restore, never silently overwrite an established live ledger."""
    archive_path = Path(archive_path)
    if archive_path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("Archive too large")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != 2 or set(names) != {LEDGER_MEMBER, MANIFEST_MEMBER}:
            raise ValueError("Unexpected ZIP members or path traversal")
        for info in archive.infolist():
            if info.file_size > MAX_LEDGER_BYTES:
                raise ValueError("Archive member too large")
            if info.is_dir():
                raise ValueError("Unexpected directory")
        ledger_bytes = archive.read(LEDGER_MEMBER)
        manifest = json.loads(archive.read(MANIFEST_MEMBER))
    if not isinstance(manifest, dict) or manifest.get("schema") != ARCHIVE_SCHEMA:
        raise ValueError("Invalid archive manifest")
    if (manifest.get("ledger_file") != LEDGER_MEMBER
            or manifest.get("ledger_sha256") != sha256(ledger_bytes).hexdigest()
            or manifest.get("ledger_bytes") != len(ledger_bytes)
            or manifest.get("contains_raw_adverts") is not False):
        raise ValueError("Corrupt or unsupported shared acquisition archive")
    doc = json.loads(ledger_bytes)
    if (not isinstance(doc, dict) or doc.get("schema") != SCHEMA
            or not isinstance(doc.get("receipts"), list)
            or len(doc["receipts"]) != manifest.get("receipts")):
        raise ValueError("Ledger content inconsistent with archive manifest")
    # Validate ALL receipt identities before changing durable state.
    from scripts.shared_acquisition_ledger import validate_receipt
    run_ids = set()
    for receipt in doc["receipts"]:
        validate_receipt(receipt)
        if receipt["run_id"] in run_ids:
            raise ValueError("Duplicate run ID")
        run_ids.add(receipt["run_id"])
    ledger.path.parent.mkdir(parents=True, exist_ok=True)
    with ledger.path.with_suffix(".lock").open("a+b") as lock:
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            if require_empty and ledger.path.exists():
                raise ValueError("Refusing to overwrite existing shared ledger")
            temp = None
            try:
                with tempfile.NamedTemporaryFile(dir=ledger.path.parent,
                    prefix=".restore-shared-", delete=False) as handle:
                    temp = handle.name
                    handle.write(ledger_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temp, 0o600)
                os.replace(temp, ledger.path)
            finally:
                if temp and os.path.exists(temp):
                    os.unlink(temp)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    return {"status": "RESTORED_VERIFIED_LEDGER_METADATA_ONLY",
            "receipts": len(doc["receipts"]),
            "ledger_sha256": manifest["ledger_sha256"]}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Offline archive/restore shared metadata only")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--restore", type=Path)
    parser.add_argument("--ledger", type=Path, default=Path("state/shared_acquisition_ledger.json"))
    arguments = parser.parse_args()
    if bool(arguments.archive) == bool(arguments.restore):
        parser.error("Choose exactly one of --archive or --restore")
    ledger = SharedLedger(arguments.ledger)
    if arguments.archive:
        result = make_archive(ledger, arguments.archive)
    else:
        result = restore_archive(arguments.restore, ledger)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
