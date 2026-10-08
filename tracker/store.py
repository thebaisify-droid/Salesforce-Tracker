from __future__ import annotations

import html
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from tracker.normalize import utc_iso

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "database" / "schema.sql"

SOURCE_LABELS = {
    "source_1": "CV-Library",
    "source_2": "Totaljobs",
    "source_3": "Reed",
    "source_4": "Indeed UK",
    "source_5": "JobServe",
}

VACANCY_FIELDS = [
    "external_id", "display_title", "title_raw", "advertiser", "advertiser_type",
    "advertiser_type_confidence", "role_family", "role_seniority", "role_specialism",
    "role_confidence", "role_review_required", "end_client_name", "end_client_sector",
    "end_client_sector_confidence", "end_client_method", "sector_basis", "sector_review_required",
    "location", "employment_type", "contract_type", "salary_min", "salary_max", "salary_currency",
    "salary_period", "job_url", "description", "posted_at", "normalized_hash", "raw_json",
    "master_data_version", "role_taxonomy_version"
]


def _content_signature(title: str | None, description: str | None) -> str | None:
    if not title or not description or len(description) < 200:
        return None
    clean_title = re.sub(r"\W+", " ", title.lower()).strip()
    clean_description = html.unescape(re.sub(r"<[^>]+>", " ", description))
    clean_description = re.sub(r"\W+", " ", clean_description.lower()).strip()
    if len(clean_description) < 160:
        return None
    return clean_title + "\n" + clean_description


def _specialisms(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [value]
    return [str(item) for item in parsed] if isinstance(parsed, list) else [str(parsed)]


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
        cross_source_match = False

        if existing is None:
            signature = _content_signature(record.get("display_title"), record.get("description"))
            if signature:
                candidates = self.conn.execute(
                    "SELECT vacancy_id, normalized_hash, display_title, description FROM vacancies WHERE lower(display_title)=lower(?)",
                    (record.get("display_title"),),
                ).fetchall()
                for candidate in candidates:
                    if _content_signature(candidate["display_title"], candidate["description"]) == signature:
                        existing = candidate
                        cross_source_match = True
                        break

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
            if cross_source_match:
                self.conn.execute(
                    "UPDATE vacancies SET last_seen_at = ?, is_active = 1 WHERE vacancy_id = ?",
                    (now, vacancy_id),
                )
                outcome = "unchanged"
            elif existing["normalized_hash"] == record["normalized_hash"]:
                self.conn.execute(
                    "UPDATE vacancies SET last_seen_at = ?, is_active = 1 WHERE vacancy_id = ?",
                    (now, vacancy_id),
                )
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
            "SELECT COALESCE(role_family,'Unresolved') label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY role_family ORDER BY value DESC, label"
        ).fetchall()
        sector_rows = self.conn.execute(
            "SELECT COALESCE(end_client_sector,'Unresolved') label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY end_client_sector ORDER BY value DESC, label"
        ).fetchall()
        advertiser_rows = self.conn.execute(
            "SELECT advertiser_type label, COUNT(*) value FROM vacancies WHERE is_active=1 GROUP BY advertiser_type ORDER BY value DESC, label"
        ).fetchall()
        review = self.conn.execute(
            "SELECT SUM(role_review_required), SUM(sector_review_required) FROM vacancies WHERE is_active=1"
        ).fetchone()
        latest = self.conn.execute(
            "SELECT run_id, started_at, finished_at, status, inserted_rows, updated_rows, unchanged_rows, rejected_rows, master_data_version, role_taxonomy_version FROM refresh_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()

        source_rows = self.conn.execute(
            """
            SELECT source_name, COUNT(DISTINCT vacancy_id) value
            FROM vacancy_sources
            GROUP BY source_name
            ORDER BY value DESC, source_name
            """
        ).fetchall()

        vacancy_rows = self.conn.execute(
            """
            SELECT
              vacancy_id, display_title, advertiser, advertiser_type,
              role_family, role_seniority, role_specialism,
              end_client_name, end_client_sector, location,
              employment_type, contract_type,
              salary_min, salary_max, salary_currency, salary_period,
              job_url, posted_at, first_seen_at, last_seen_at,
              role_review_required, sector_review_required
            FROM vacancies
            WHERE is_active=1
            ORDER BY COALESCE(posted_at, first_seen_at) DESC, vacancy_id DESC
            """
        ).fetchall()

        sources_by_vacancy: dict[int, list[dict[str, Any]]] = {}
        for row in self.conn.execute(
            "SELECT vacancy_id, source_name, source_url FROM vacancy_sources ORDER BY vacancy_id, source_name"
        ):
            item = {
                "key": row["source_name"],
                "label": SOURCE_LABELS.get(row["source_name"], row["source_name"]),
                "url": row["source_url"],
            }
            sources_by_vacancy.setdefault(int(row["vacancy_id"]), []).append(item)

        vacancies: list[dict[str, Any]] = []
        for row in vacancy_rows:
            vacancy_id = int(row["vacancy_id"])
            vacancies.append({
                "id": vacancy_id,
                "title": row["display_title"],
                "advertiser": row["advertiser"],
                "advertiser_type": row["advertiser_type"],
                "role_family": row["role_family"] or "Unresolved",
                "seniority": row["role_seniority"] or "Standard",
                "specialisms": _specialisms(row["role_specialism"]),
                "end_client_name": row["end_client_name"],
                "sector": row["end_client_sector"] or "Unresolved",
                "location": row["location"],
                "employment_type": row["employment_type"],
                "contract_type": row["contract_type"],
                "salary": {
                    "min": row["salary_min"],
                    "max": row["salary_max"],
                    "currency": row["salary_currency"],
                    "period": row["salary_period"],
                },
                "url": row["job_url"],
                "posted_at": row["posted_at"],
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "review": {
                    "role": bool(row["role_review_required"]),
                    "sector": bool(row["sector_review_required"]),
                },
                "sources": sources_by_vacancy.get(vacancy_id, []),
            })

        return {
            "active_vacancies": int(total),
            "by_role_family": [dict(r) for r in role_rows],
            "by_sector": [dict(r) for r in sector_rows],
            "by_advertiser_type": [dict(r) for r in advertiser_rows],
            "by_source": [
                {
                    "key": row["source_name"],
                    "label": SOURCE_LABELS.get(row["source_name"], row["source_name"]),
                    "value": int(row["value"]),
                }
                for row in source_rows
            ],
            "review_queue": {"role": int(review[0] or 0), "sector": int(review[1] or 0)},
            "latest_run": dict(latest) if latest else None,
            "vacancies": vacancies,
        }
