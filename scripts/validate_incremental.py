from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pipeline.daily_refresh import inspect_record_artifact

REQUIRED_METRICS = (
    "inserted_rows", "updated_rows", "unchanged_rows", "rejected_rows",
    "master_data_version", "role_taxonomy_version",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_result(passed: bool, value: Any = None, detail: str | None = None) -> dict[str, Any]:
    out = {"passed": bool(passed), "value": value}
    if detail:
        out["detail"] = detail
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Validate one Salesforce tracker incremental run")
    p.add_argument("--run-id")
    p.add_argument("--report", required=True)
    p.add_argument("--run-dir")
    p.add_argument("--expected-sources", type=int)
    p.add_argument("--expected-master-data-version")
    p.add_argument("--expected-role-taxonomy-version")
    p.add_argument("--max-rejection-rate", type=float)
    args = p.parse_args()

    run_dir = Path(args.run_dir or os.environ.get("PIPELINE_RUN_DIR", ""))
    report_path = Path(args.report)
    raw_dir = run_dir / "raw"
    metrics_path = run_dir / "metrics.json"

    expected_sources = args.expected_sources
    if expected_sources is None:
        value = os.environ.get("PIPELINE_MIN_SOURCES")
        expected_sources = int(value) if value else 3

    expected_master = args.expected_master_data_version or os.environ.get("PIPELINE_EXPECTED_MASTER_DATA_VERSION")
    expected_taxonomy = args.expected_role_taxonomy_version or os.environ.get("PIPELINE_EXPECTED_ROLE_TAXONOMY_VERSION")
    max_rejection_rate = args.max_rejection_rate
    if max_rejection_rate is None and os.environ.get("PIPELINE_MAX_REJECTION_RATE"):
        max_rejection_rate = float(os.environ["PIPELINE_MAX_REJECTION_RATE"])

    checks: dict[str, Any] = {}
    evidence: dict[str, Any] = {"run_id": args.run_id or os.environ.get("PIPELINE_RUN_ID"), "sources": []}

    raw_files = sorted(p for p in raw_dir.glob("*") if p.is_file()) if raw_dir.exists() else []
    valid_sources = 0
    total_raw_records = 0
    for path in raw_files:
        count, valid, error = inspect_record_artifact(path)
        if valid:
            valid_sources += 1
            total_raw_records += count or 0
        evidence["sources"].append({
            "file": path.name,
            "valid": valid,
            "record_count": count,
            "error": error,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

    checks["source_coverage"] = check_result(
        valid_sources >= expected_sources,
        valid_sources,
        f"expected at least {expected_sources} valid source artifacts",
    )
    checks["raw_artifact_integrity"] = check_result(
        len(raw_files) == valid_sources and valid_sources >= expected_sources,
        {"files": len(raw_files), "valid": valid_sources, "raw_records": total_raw_records},
    )

    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        metrics = None

    checks["metrics_present"] = check_result(isinstance(metrics, dict), bool(isinstance(metrics, dict)))
    missing_metrics = []
    invalid_counts = []
    if isinstance(metrics, dict):
        missing_metrics = [k for k in REQUIRED_METRICS if k not in metrics]
        for key in ("inserted_rows", "updated_rows", "unchanged_rows", "rejected_rows"):
            value = metrics.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                invalid_counts.append(key)
    else:
        missing_metrics = list(REQUIRED_METRICS)

    checks["metrics_complete"] = check_result(
        not missing_metrics,
        {"missing": missing_metrics},
        "required fields: " + ", ".join(REQUIRED_METRICS),
    )
    checks["change_counts_valid"] = check_result(not invalid_counts, {"invalid": invalid_counts})

    master_value = metrics.get("master_data_version") if isinstance(metrics, dict) else None
    taxonomy_value = metrics.get("role_taxonomy_version") if isinstance(metrics, dict) else None
    checks["master_data_version"] = check_result(
        bool(master_value) and (expected_master is None or str(master_value) == str(expected_master)),
        master_value,
        f"expected {expected_master}" if expected_master is not None else "version must be present",
    )
    checks["taxonomy_version"] = check_result(
        bool(taxonomy_value) and (expected_taxonomy is None or str(taxonomy_value) == str(expected_taxonomy)),
        taxonomy_value,
        f"expected {expected_taxonomy}" if expected_taxonomy is not None else "version must be present",
    )

    if isinstance(metrics, dict) and not invalid_counts:
        processed = sum(metrics[k] for k in ("inserted_rows", "updated_rows", "unchanged_rows", "rejected_rows"))
        rejected = metrics["rejected_rows"]
        rejection_rate = (rejected / processed) if processed else 0.0
    else:
        rejection_rate = None

    if max_rejection_rate is None:
        checks["rejection_rate"] = check_result(rejection_rate is not None, rejection_rate, "observed only; no maximum configured")
    else:
        checks["rejection_rate"] = check_result(
            rejection_rate is not None and rejection_rate <= max_rejection_rate,
            rejection_rate,
            f"maximum allowed {max_rejection_rate:.4f}",
        )

    passed = all(c["passed"] for c in checks.values())
    report = {"passed": passed, "run_id": evidence["run_id"], "checks": checks, "evidence": evidence}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
