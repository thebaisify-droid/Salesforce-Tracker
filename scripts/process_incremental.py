from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from tracker.classify import versions
from tracker.normalize import load_records, normalize
from tracker.relevance import salesforce_relevance
from tracker.store import Store


def main() -> int:
    p = argparse.ArgumentParser(description="Normalize, classify, deduplicate and upsert incremental Salesforce vacancies")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--metrics", required=True)
    p.add_argument("--database", default=os.environ.get("TRACKER_DATABASE_PATH", "data/salesforce_tracker.db"))
    args = p.parse_args()

    input_dir = Path(args.input_dir)
    counts = {
        "inserted_rows": 0,
        "updated_rows": 0,
        "unchanged_rows": 0,
        "rejected_rows": 0,
        "irrelevant_rows": 0,
        "role_review_rows": 0,
        "sector_review_rows": 0,
    }
    source_rows: dict[str, int] = {}
    source_relevant_rows: dict[str, int] = {}
    source_irrelevant_rows: dict[str, int] = {}
    irrelevant_reasons: Counter[str] = Counter()
    master_version, taxonomy_version = versions()

    with Store(args.database) as store:
        store.begin_run(args.run_id, master_version, taxonomy_version)
        try:
            for path in sorted(input_dir.glob("*")):
                if not path.is_file():
                    continue
                source_name = path.stem
                records = load_records(path)
                source_rows[source_name] = len(records)
                source_relevant_rows[source_name] = 0
                source_irrelevant_rows[source_name] = 0
                for raw in records:
                    relevant, relevance_reason = salesforce_relevance(raw)
                    if not relevant:
                        counts["irrelevant_rows"] += 1
                        source_irrelevant_rows[source_name] += 1
                        irrelevant_reasons[relevance_reason] += 1
                        continue
                    source_relevant_rows[source_name] += 1
                    try:
                        record = normalize(raw, source_name)
                        if not record.get("display_title"):
                            raise ValueError("missing job title")
                        outcome = store.upsert(record)
                        counts[f"{outcome}_rows"] += 1
                        counts["role_review_rows"] += int(record["role_review_required"])
                        counts["sector_review_rows"] += int(record["sector_review_required"])
                    except Exception:
                        counts["rejected_rows"] += 1
            store.finish_run(args.run_id, "success", counts)
        except Exception:
            store.finish_run(args.run_id, "failed", counts)
            raise

    metrics = {
        **counts,
        "source_rows": source_rows,
        "source_relevant_rows": source_relevant_rows,
        "source_irrelevant_rows": source_irrelevant_rows,
        "irrelevant_reasons": dict(irrelevant_reasons),
        "master_data_version": master_version,
        "role_taxonomy_version": taxonomy_version,
    }
    Path(args.metrics).write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
