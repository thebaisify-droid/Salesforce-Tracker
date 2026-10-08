from __future__ import annotations

import html
import json
import re
import sqlite3
from datetime import datetime, timezone
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


def _norm_company(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
    if not text or text.startswith("unnamed ") or text.startswith("unknown "):
        return ""
    return " ".join(
        part for part in text.split()
        if part not in {"limited", "ltd", "plc", "llp", "group"}
    )


def _norm_title(value: str | None) -> str:
    text = (value or "").lower()
    text = re.sub(r"\bcloned\s+on\s+\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?.*$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _location_words(value: str | None) -> set[str]:
    stop = {"uk", "england", "united", "kingdom", "city", "remote", "hybrid"}
    return {
        token
        for token in re.findall(r"[a-z]+", (value or "").lower())
        if len(token) >= 4 and token not in stop
    }


def _date_value(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _market_identity_match(record: dict[str, Any], candidate: sqlite3.Row) -> bool:
    if _norm_title(record.get("display_title")) != _norm_title(candidate["display_title"]):
        return False

    record_company = _norm_company(record.get("advertiser") or record.get("end_client_name"))
    candidate_company = _norm_company(candidate["advertiser"] or candidate["end_client_name"])
    companies_known = bool(record_company and candidate_company)
    if companies_known and record_company != candidate_company:
        return False

    left_location = _location_words(record.get("location"))
    right_location = _location_words(candidate["location"])
    location_match = bool(left_location & right_location)
    if not location_match:
        return False

    left_date = _date_value(record.get("posted_at"))
    right_date = _date_value(candidate["posted_at"])
    date_gap = abs((left_date.date() - right_date.date()).days) if left_date and right_date else None
    if companies_known:
        return date_gap is None or date_gap <= 30

    # Baseline rows can intentionally omit the advertiser/end-client identity.
    # In that case only collapse a mirror when title+location are identical and
    # the posting dates are close enough to strongly indicate the same vacancy.
    return date_gap is not None and date_gap <= 3


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
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        columns = {
            row["name"]
            for row in self.conn.execute("PRAGMA table_info(vacancies)").fetchall()
        }
        additions = {
            "lifecycle_status": "TEXT NOT NULL DEFAULT 'ACTIVE'",
            "lifecycle_reason": "TEXT",
            "lifecycle_updated_at": "TEXT",
            "last_verified_at": "TEXT",
            "unavailable_streak": "INTEGER NOT NULL DEFAULT 0",
            "unavailable_first_seen_at": "TEXT",
        }
        for name, definition in additions.items():
            if name not in columns:
                self.conn.execute(f"ALTER TABLE vacancies ADD COLUMN {name} {definition}")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vacancies_lifecycle_status ON vacancies(lifecycle_status)"
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lifecycle_checks (
              check_id INTEGER PRIMARY KEY AUTOINCREMENT,
              vacancy_id INTEGER NOT NULL REFERENCES vacancies(vacancy_id) ON DELETE CASCADE,
              checked_at TEXT NOT NULL,
              result TEXT NOT NULL,
              evidence_type TEXT NOT NULL,
              http_status INTEGER,
              checked_url TEXT,
              final_url TEXT,
              detail TEXT
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lifecycle_checks_vacancy ON lifecycle_checks(vacancy_id, checked_at)"
        )

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
            title = (record.get("display_title") or "").strip()
            if title:
                identity_candidates = self.conn.execute(
                    """
                    SELECT vacancy_id, normalized_hash, display_title, description,
                           advertiser, end_client_name, location, posted_at, salary_min, salary_max
                    FROM vacancies
                    WHERE is_active=1
                    ORDER BY vacancy_id
                    """
                ).fetchall()
                matches = [
                    candidate
                    for candidate in identity_candidates
                    if _market_identity_match(record, candidate)
                ]
                if len(matches) == 1:
                    existing = matches[0]
                    cross_source_match = True

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

        self.conn.execute(
            """
            UPDATE vacancies SET
              is_active=1,
              lifecycle_status='ACTIVE',
              lifecycle_reason='seen_in_source',
              lifecycle_updated_at=?,
              last_verified_at=?,
              unavailable_streak=0,
              unavailable_first_seen_at=NULL
            WHERE vacancy_id=?
            """,
            (now, now, vacancy_id),
        )

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

    def record_lifecycle_observation(
        self,
        vacancy_id: int,
        *,
        result: str,
        evidence_type: str,
        checked_at: str,
        checked_url: str | None = None,
        final_url: str | None = None,
        http_status: int | None = None,
        detail: str | None = None,
        confirmations: int = 2,
        min_confirmation_hours: float = 12.0,
    ) -> str:
        result = result.upper()
        if result not in {"AVAILABLE", "UNAVAILABLE", "INCONCLUSIVE"}:
            raise ValueError(f"unsupported lifecycle result: {result}")

        current = self.conn.execute(
            """
            SELECT lifecycle_status, unavailable_streak, unavailable_first_seen_at
            FROM vacancies WHERE vacancy_id=?
            """,
            (vacancy_id,),
        ).fetchone()
        if current is None:
            raise ValueError(f"unknown vacancy_id: {vacancy_id}")

        self.conn.execute(
            """
            INSERT INTO lifecycle_checks(
              vacancy_id, checked_at, result, evidence_type, http_status,
              checked_url, final_url, detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vacancy_id, checked_at, result, evidence_type, http_status,
                checked_url, final_url, detail,
            ),
        )

        if result == "AVAILABLE":
            self.conn.execute(
                """
                UPDATE vacancies SET
                  is_active=1,
                  lifecycle_status='ACTIVE',
                  lifecycle_reason=?,
                  lifecycle_updated_at=?,
                  last_verified_at=?,
                  unavailable_streak=0,
                  unavailable_first_seen_at=NULL
                WHERE vacancy_id=?
                """,
                (evidence_type, checked_at, checked_at, vacancy_id),
            )
            return "ACTIVE"

        if result == "INCONCLUSIVE":
            self.conn.execute(
                """
                UPDATE vacancies SET
                  last_verified_at=?,
                  unavailable_streak=0,
                  unavailable_first_seen_at=NULL
                WHERE vacancy_id=?
                """,
                (checked_at, vacancy_id),
            )
            return str(current["lifecycle_status"] or "ACTIVE")

        streak = int(current["unavailable_streak"] or 0) + 1
        first_seen = current["unavailable_first_seen_at"] or checked_at
        confirm = False
        try:
            first_dt = datetime.fromisoformat(str(first_seen).replace("Z", "+00:00"))
            checked_dt = datetime.fromisoformat(str(checked_at).replace("Z", "+00:00"))
            elapsed_hours = (checked_dt - first_dt).total_seconds() / 3600
            confirm = streak >= confirmations and elapsed_hours >= min_confirmation_hours
        except ValueError:
            confirm = False

        status = "CONFIRMED_EXPIRED" if confirm else "POSSIBLY_EXPIRED"
        self.conn.execute(
            """
            UPDATE vacancies SET
              is_active=?,
              lifecycle_status=?,
              lifecycle_reason=?,
              lifecycle_updated_at=?,
              last_verified_at=?,
              unavailable_streak=?,
              unavailable_first_seen_at=?
            WHERE vacancy_id=?
            """,
            (
                0 if confirm else 1,
                status,
                evidence_type,
                checked_at,
                checked_at,
                streak,
                first_seen,
                vacancy_id,
            ),
        )
        return status

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
        lifecycle_rows = self.conn.execute(
            "SELECT lifecycle_status label, COUNT(*) value FROM vacancies GROUP BY lifecycle_status ORDER BY value DESC, label"
        ).fetchall()
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
              lifecycle_status, lifecycle_reason, lifecycle_updated_at, last_verified_at,
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
                "lifecycle": {
                    "status": row["lifecycle_status"] or "ACTIVE",
                    "reason": row["lifecycle_reason"],
                    "updated_at": row["lifecycle_updated_at"],
                    "last_verified_at": row["last_verified_at"],
                },
                "review": {
                    "role": bool(row["role_review_required"]),
                    "sector": bool(row["sector_review_required"]),
                },
                "sources": sources_by_vacancy.get(vacancy_id, []),
            })

        inactive_vacancies = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT job_url url, display_title title, location, posted_at
                FROM vacancies
                WHERE lifecycle_status='CONFIRMED_EXPIRED'
                """
            ).fetchall()
        ]

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
            "lifecycle": {str(row["label"]): int(row["value"]) for row in lifecycle_rows},
            "_inactive_vacancies": inactive_vacancies,
            "latest_run": dict(latest) if latest else None,
            "vacancies": vacancies,
        }
