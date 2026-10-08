from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SNAPSHOT_PREFIXES = ("data/", "state/", "dashboard/")
REQUIRED_TABLES = {"vacancies", "vacancy_sources", "refresh_runs"}
MANIFEST_RELATIVE = Path("state/state_manifest.json")


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def inspect_database(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"tracker database is missing: {path}")
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"SQLite integrity_check failed: {integrity}")
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = sorted(REQUIRED_TABLES - tables)
        if missing:
            raise RuntimeError("tracker database is missing required tables: " + ", ".join(missing))
        counts = {
            "vacancies": int(conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]),
            "active_vacancies": int(conn.execute("SELECT COUNT(*) FROM vacancies WHERE is_active=1").fetchone()[0]),
            "vacancy_sources": int(conn.execute("SELECT COUNT(*) FROM vacancy_sources").fetchone()[0]),
            "refresh_runs": int(conn.execute("SELECT COUNT(*) FROM refresh_runs").fetchone()[0]),
        }
        if "lifecycle_checks" in tables:
            counts["lifecycle_checks"] = int(conn.execute("SELECT COUNT(*) FROM lifecycle_checks").fetchone()[0])
            for row in conn.execute("SELECT lifecycle_status, COUNT(*) FROM vacancies GROUP BY lifecycle_status"):
                counts["lifecycle_" + str(row[0]).lower()] = int(row[1])
        latest = conn.execute(
            "SELECT run_id, status, finished_at FROM refresh_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except sqlite3.Error as exc:
        raise RuntimeError(f"could not verify tracker database: {exc}") from exc
    return {
        "integrity_check": integrity,
        "counts": counts,
        "latest_run": dict(latest) if latest else None,
    }


def snapshot_files(root: Path, database: Path) -> list[Path]:
    candidates = [database]
    for directory in (root / "state", root / "dashboard"):
        if directory.exists():
            candidates.extend(p for p in directory.rglob("*") if p.is_file())
    manifest = root / MANIFEST_RELATIVE
    return sorted({p.resolve() for p in candidates if p.exists() and p.resolve() != manifest.resolve()})


def build_manifest(root: Path, database_path: str | Path = "data/salesforce_tracker.db") -> dict[str, Any]:
    root = root.resolve()
    database = Path(database_path)
    if not database.is_absolute():
        database = root / database
    database = database.resolve()
    database_info = inspect_database(database)
    files = []
    for path in snapshot_files(root, database):
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"snapshot file lies outside repository workspace: {path}") from exc
        files.append({
            "path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return {
        "schema": "salesforce-tracker-state/v1",
        "generated_at": utc_iso(),
        "database": {
            "path": database.relative_to(root).as_posix(),
            "sha256": sha256_file(database),
            **database_info,
        },
        "files": files,
    }


def write_manifest(root: Path, output: Path, database_path: str | Path) -> dict[str, Any]:
    manifest = build_manifest(root, database_path)
    atomic_write_json(output, manifest)
    return manifest


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    root = root.resolve()
    if not manifest_path.exists():
        raise RuntimeError(f"state manifest is missing: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"state manifest is invalid: {exc}") from exc
    if manifest.get("schema") != "salesforce-tracker-state/v1":
        raise RuntimeError("unsupported state manifest schema")

    for item in manifest.get("files", []):
        path = (root / item["path"]).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise RuntimeError(f"manifest path escapes workspace: {item['path']}") from exc
        if not path.exists():
            raise RuntimeError(f"snapshot file is missing: {item['path']}")
        actual = sha256_file(path)
        if actual != item.get("sha256"):
            raise RuntimeError(f"snapshot checksum mismatch: {item['path']}")

    database_relative = manifest.get("database", {}).get("path")
    if not database_relative:
        raise RuntimeError("manifest does not identify the tracker database")
    database = (root / database_relative).resolve()
    database_info = inspect_database(database)
    if sha256_file(database) != manifest["database"].get("sha256"):
        raise RuntimeError("tracker database checksum does not match manifest")
    return {
        "verified": True,
        "manifest": str(manifest_path),
        "database": database_info,
        "generated_at": manifest.get("generated_at"),
    }


def safe_extract(snapshot_zip: Path, root: Path) -> list[str]:
    root = root.resolve()
    extracted: list[str] = []
    with zipfile.ZipFile(snapshot_zip) as archive:
        for member in archive.infolist():
            name = member.filename.replace("\\", "/")
            if name.endswith("/"):
                continue
            if name.startswith("/") or ".." in Path(name).parts:
                raise RuntimeError(f"unsafe path in state artifact: {name}")
            if not name.startswith(SNAPSHOT_PREFIXES):
                raise RuntimeError(f"unexpected file in state artifact: {name}")
            destination = (root / name).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(f"state artifact path escapes workspace: {name}") from exc
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, destination.open("wb") as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            extracted.append(name)
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, verify or restore Salesforce tracker state snapshots")
    parser.add_argument("--root", default=".")
    parser.add_argument("--database", default="data/salesforce_tracker.db")
    parser.add_argument("--write-manifest", default=None)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--extract", default=None, help="Path to a downloaded tracker-state artifact ZIP")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = Path(args.write_manifest) if args.write_manifest else root / MANIFEST_RELATIVE
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path

    if args.extract:
        extracted = safe_extract(Path(args.extract), root)
        result = verify_manifest(root, root / MANIFEST_RELATIVE)
        result["restored_files"] = extracted
        print(json.dumps(result, indent=2))
        return 0

    if args.write_manifest:
        result = write_manifest(root, manifest_path, args.database)
        print(json.dumps(result, indent=2))
        return 0

    if args.verify:
        result = verify_manifest(root, root / MANIFEST_RELATIVE)
        print(json.dumps(result, indent=2))
        return 0

    parser.error("choose --write-manifest, --verify or --extract")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
