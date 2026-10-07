from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from tracker.normalize import utc_iso

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "database" / "schema.sql"

VACANCY_FIELDS = [
    "external_id", "display_title", "title_raw", "advertiser", "advertiser_type",
    "advertiser_type_confidence", "role_family", "role_seniority", "role_specialism",
    "role_confidence", "role_review_required", "end_client_name", "end_client_sector",
    "end_client_sector_confidence", "end_client_method", "sector_basis", "sector_review_required",
    "location", "employment_type", "contract_type", "salary_min", "salary_max", "salary_currency",
    "salary_period", "job_url", "description", "posted_at", "normalized_hash", "raw_json",
    "master_data_version", "role_taxonomy_version"
]


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type:
            self.conn.rollback()
        self.close()

    def upsert(self, record: dict[str, Any]) -> str:
        now = utc_iso()
        existing = self.conn.execute(
            "SELECT vacancy_id, normalized_hash FROM vacancies WHERE dedupe_key = ?",
            (record["dedupe_key"],),
        ).fetchone()

        if existing is None:
            fields = ["dedupe_key", *VACANCY_FIELDS, "first_seen_at", "last_seen_at"]
            values = [record.get(field) for field in ["dedupe_key", *VACANCY_FIELDS]] + [now, now]
            placeholders = ",".join("?" for _ in fields)
            cur = self.conn.execute(
                f"INSERT INTO vacancies ({','.join(fields)}) VALUES ({placeholders})",
                values,
            )
            vacancy_id = int(cur.lastrowid)
            outcome = "inserted"
        else:
            vacancy_id = int(existing["vacancy_id"])
            if existing["normalized_hash"] == record["normalized_hash"]:
                self.conn.execute("UPDATE vacancies SET last_seen_at = ?, is_active = 1 WHERE vacancy_id = ?", (now, vacancy_id))
                outcome = "unchanged"
            else:
                assignments = ",".join(f"{field} = ?" for field in VACANCY_FIELDS)
                values = [record.get(field) for field in VACANCY_FIELDS] + [now, vacancy_id]
                self.conn.execute(
                    f"UPDATE vacancies SET {assignments}, last_seen_at = ?, is_active = 1 WHERE vacancy_id = ?",
                    values,
                )
                outcome = "updated"

        source_name = str(record.get("source_name") or "unknown")
        source_record_id = str(record.get("source_record_id") or record["dedupe_key"])
        source_url = record.get("job_url")
        raw_hash = record["normalized_hash"]
        self.conn.execute(
            """
            INSERT INTO vacancy_sources(source_name, source_record_id, vacancy_id, source_url, first_seen_at, last_seen_at, raw_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_name, source_record_id) DO UPDATE SET
                vacancy_id=excluded.vacancy_id,
                source_url=excluded.source_url,
                last_seen_at=excluded.last_seen_at,
                raw_hash=excluded.raw_hash
            """,
            (source_name, source_record_id, vacancy_id, source_url, now, now, raw_hash),
        )
        return outcome

    def begin_run(self, run_id: str, master_version: str, taxonomy_version: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO refresh_runs(run_id, started_at, status, master_data_version, role_taxonomy_version) VALUES (?, ?, 'running', ?, ?)",
            (run_id, utc_iso(), master_version, taxonomy_version),
        )

    def finish_run(self, run_id: str, status: str, metrics: dict[str, int]) -> None:
        self.conn.execute(
            """
            UPDATE refresh_runs SET finished_at=?, status=?, inserted_rows=?, updated_rows=?, unchanged_rows=?, rejected_rows=?, role_review_rows=?, sector_review_rows=?
            WHERE run_id=?
            """,
            (
                utc_iso(), status, metrics.get("inserted_rows", 0), metrics.get("updated_rows", 0),
                metrics.get("unchanged_rows", 0), metrics.get("rejected_rows", 0),
                metrics.get("role_review_rows", 0), metrics.get("sector_review_rows", 0), run_id,
            ),
        )

    def dashboard_snapshot(self) -> dict[str, Any]:
        total = self.conn.execute("SELECT COUNT(*) FROM vacancies WHERE is_active=1").fetchone()[0]
        role_rows = self.conn.execute(
            "SELECT COALESCE(role_family,'Unresolved') label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY role_family ORDER BY value DESC"
        ).fetchall()
        sector_rows = self.conn.execute(
            "SELECT COALESCE(end_client_sector,'Unresolved') label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY end_client_sector ORDER BY value DESC"
        ).fetchall()
        advertiser_rows = self.conn.execute(
            "SELECT advertiser_type label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY advertiser_type ORDER BY value DESC"
        ).fetchall()
        review = self.conn.execute(
            "SELECT SUM(role_review_required), SUM(sector_review_required) FROM vacancies WHERE is_active=1"
        ).fetchone()
        latest = self.conn.execute(
            "SELECT run_id, started_at, finished_at, status, inserted_rows, updated_rows, unchanged_rows, rejected_rows FROM refresh_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return {
            "active_vacancies": int(total),
            "by_role_family": [dict(r) for r in role_rows],
            "by_sector": [dict(r) for r in sector_rows],
            "by_advertiser_type": [dict(r) for r in advertiser_rows],
            "review_queue": {"role": int(review[0] or 0), "sector": int(review[1] or 0)},
            "latest_run": dict(latest) if latest else None,
        }
