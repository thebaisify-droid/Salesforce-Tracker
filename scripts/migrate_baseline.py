from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tracker.normalize import canonical_url
from tracker.store import Store, VACANCY_FIELDS


def dedupe_key(url: str | None, title: str | None, location: str | None, posted_at: str | None) -> str:
    clean = canonical_url(url)
    basis = clean or "|".join((title or "", location or "", (posted_at or "")[:10]))
    return hashlib.sha256(basis.lower().encode("utf-8")).hexdigest()


def normalized_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def source_label_to_key(label: str) -> str:
    mapping = {"CV-Library": "source_1", "Totaljobs": "source_2", "Reed": "source_3"}
    return mapping.get(label, label)


def baseline_record(row: dict[str, Any], captured_at: str) -> dict[str, Any]:
    key = dedupe_key(row.get("apply_url"), row.get("title"), row.get("location"), row.get("posted_at"))
    sector = row.get("sector") or "Unknown"
    return {
        "dedupe_key": key,
        "external_id": row.get("legacy_id"),
        "display_title": row.get("title") or "Untitled vacancy",
        "title_raw": row.get("title"),
        "advertiser": None,
        "advertiser_type": "MIXED_OR_UNKNOWN",
        "advertiser_type_confidence": 0.0,
        "role_family": row.get("role_family") or "Unresolved",
        "role_seniority": row.get("seniority") or "Standard",
        "role_specialism": "[]",
        "role_confidence": 1.0,
        "role_review_required": 0,
        "end_client_name": row.get("employer_client"),
        "end_client_sector": sector,
        "end_client_sector_confidence": 1.0 if sector not in {"Unknown", "Unresolved"} else 0.0,
        "end_client_method": "VALIDATED_BASELINE_2026_10_06",
        "sector_basis": "VALIDATED_BASELINE",
        "sector_review_required": int(sector in {"Unknown", "Unresolved"}),
        "location": row.get("location"),
        "employment_type": row.get("employment"),
        "contract_type": row.get("contract_detail"),
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "GBP",
        "salary_period": None,
        "job_url": canonical_url(row.get("apply_url")),
        "description": "",
        "posted_at": row.get("posted_at"),
        "normalized_hash": normalized_hash(row),
        "raw_json": json.dumps({"baseline": row}, sort_keys=True, ensure_ascii=False),
        "master_data_version": "1.5.1-baseline",
        "role_taxonomy_version": "2.2",
        "first_seen_at": captured_at,
        "last_seen_at": captured_at,
    }


def migrate(database: Path, baseline_path: Path) -> dict[str, Any]:
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    captured_at = str(payload.get("captured_at") or payload.get("baseline_date") or "2026-10-06T00:00:00Z")
    if len(rows) != 45:
        raise RuntimeError(f"expected 45 validated baseline rows, found {len(rows)}")

    stats = {
        "baseline_rows": len(rows),
        "database_before": 0,
        "database_after": 0,
        "inserted_missing_baseline": 0,
        "matched_existing": 0,
        "source_links_added": 0,
        "duplicate_baseline_keys": 0,
    }

    seen_keys: set[str] = set()
    with Store(database) as store:
        stats["database_before"] = int(store.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0])

        for row in rows:
            record = baseline_record(row, captured_at)
            key = record["dedupe_key"]
            if key in seen_keys:
                stats["duplicate_baseline_keys"] += 1
                continue
            seen_keys.add(key)

            existing = store.conn.execute(
                "SELECT vacancy_id FROM vacancies WHERE dedupe_key = ?",
                (key,),
            ).fetchone()

            if existing:
                vacancy_id = int(existing["vacancy_id"])
                stats["matched_existing"] += 1
            else:
                fields = ["dedupe_key", *VACANCY_FIELDS, "first_seen_at", "last_seen_at"]
                values = [record.get(field) for field in fields]
                placeholders = ",".join("?" for _ in fields)
                cur = store.conn.execute(
                    f"INSERT INTO vacancies ({','.join(fields)}) VALUES ({placeholders})",
                    values,
                )
                vacancy_id = int(cur.lastrowid)
                stats["inserted_missing_baseline"] += 1

            source_keys = list(row.get("source_keys") or [])
            if not source_keys and row.get("primary_source_label"):
                source_keys = [source_label_to_key(str(row["primary_source_label"]))]

            for source_name in source_keys:
                source_url = canonical_url(row.get("apply_url")) if source_label_to_key(str(row.get("primary_source_label") or "")) == source_name else None
                source_record_id = f"baseline:{row.get('legacy_id')}:{source_name}"
                before = store.conn.total_changes
                store.conn.execute(
                    """
                    INSERT OR IGNORE INTO vacancy_sources(
                        source_name, source_record_id, vacancy_id, source_url,
                        first_seen_at, last_seen_at, raw_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_name,
                        source_record_id,
                        vacancy_id,
                        source_url,
                        captured_at,
                        captured_at,
                        record["normalized_hash"],
                    ),
                )
                if store.conn.total_changes > before:
                    stats["source_links_added"] += 1

        stats["database_after"] = int(store.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0])
        canonical_duplicates = store.conn.execute(
            """
            SELECT COUNT(*) FROM (
              SELECT job_url, COUNT(*) c
              FROM vacancies
              WHERE job_url IS NOT NULL AND job_url <> ''
              GROUP BY job_url
              HAVING c > 1
            )
            """
        ).fetchone()[0]
        stats["duplicate_job_urls"] = int(canonical_duplicates)

    stats["passed"] = (
        stats["database_after"] >= 45
        and stats["duplicate_baseline_keys"] == 0
        and stats["duplicate_job_urls"] == 0
    )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate the validated 6 Oct Salesforce master into persistent SQLite state")
    parser.add_argument("--database", default="data/salesforce_tracker.db")
    parser.add_argument("--baseline", default="config/baseline_2026-10-06.json")
    parser.add_argument("--report", default="state/baseline_migration.json")
    args = parser.parse_args()

    result = migrate(Path(args.database), Path(args.baseline))
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
