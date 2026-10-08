"""Independent SQLite staging store for candidate market vacancies.

No Apify calls, existing Salesforce DB access, or publication side effects.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.build_candidate_market_dashboard import _clean_url, _field, ALLOWED, COMPANY_KEYS, LOCATION_KEYS, SOURCE_KEYS, DATE_KEYS, URL_KEYS
from tracker.business_product_delivery_security import classify_raw

SCHEMA = """
CREATE TABLE IF NOT EXISTS candidate_vacancies (
    identity_key TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    advertiser TEXT,
    location TEXT,
    posted_at TEXT,
    track TEXT NOT NULL CHECK (track IN ('SECURITY','BUSINESS_PRODUCT_DELIVERY')),
    role_family TEXT NOT NULL,
    matched_title TEXT NOT NULL,
    review_required INTEGER NOT NULL CHECK (review_required IN (0,1)),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidate_sources (
    identity_key TEXT NOT NULL REFERENCES candidate_vacancies(identity_key),
    source TEXT NOT NULL,
    PRIMARY KEY (identity_key, source)
);
CREATE TABLE IF NOT EXISTS candidate_ingestions (
    batch_id TEXT PRIMARY KEY,
    ingested_at TEXT NOT NULL,
    inserted INTEGER NOT NULL,
    updated INTEGER NOT NULL,
    rejected INTEGER NOT NULL
);
"""

def identity_key(url: str) -> str:
    """Conservative URL identity. Cross-board similarity is NOT auto-merged."""
    return hashlib.sha256(url.lower().encode("utf-8")).hexdigest()

class CandidateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.resolve().name == "salesforce_tracker.db":
            raise ValueError("Salesforce tracker database is protected")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.conn.close()

    def ingest(self, rows: list[dict[str, Any]], batch_id: str, at: str | None = None) -> dict[str, int]:
        if not isinstance(rows, list):
            raise ValueError("rows must be a list")
        stamp = at or datetime.now(timezone.utc).isoformat()
        stats = {"inserted": 0, "updated": 0, "rejected": 0}
        with self.conn:
            if self.conn.execute("SELECT 1 FROM candidate_ingestions WHERE batch_id=?", (batch_id,)).fetchone():
                raise ValueError("batch_id already ingested")
            for raw in rows:
                if not isinstance(raw, dict):
                    stats["rejected"] += 1
                    continue
                decision = classify_raw(raw)
                if not decision["included"]:
                    stats["rejected"] += 1
                    continue
                title = _field(raw, ALLOWED)
                url = _clean_url(_field(raw, URL_KEYS))
                if not title or not url:
                    stats["rejected"] += 1
                    continue
                key = identity_key(url)
                exists = self.conn.execute("SELECT 1 FROM candidate_vacancies WHERE identity_key=?", (key,)).fetchone()
                if exists:
                    self.conn.execute("UPDATE candidate_vacancies SET last_seen_at=?, review_required=? WHERE identity_key=?",
                                      (stamp, int(decision["review_required"]), key))
                    stats["updated"] += 1
                else:
                    self.conn.execute("""INSERT INTO candidate_vacancies
                        (identity_key,title,url,advertiser,location,posted_at,track,role_family,matched_title,review_required,first_seen_at,last_seen_at)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (key,title,url,_field(raw,COMPANY_KEYS),_field(raw,LOCATION_KEYS),
                         _field(raw,DATE_KEYS),decision["track"],decision["role_family"],
                         decision["matched_title"],int(decision["review_required"]),stamp,stamp))
                    stats["inserted"] += 1
                source = _field(raw, SOURCE_KEYS) or "unknown"
                self.conn.execute("INSERT OR IGNORE INTO candidate_sources(identity_key,source) VALUES (?,?)", (key,source))
            self.conn.execute("INSERT INTO candidate_ingestions VALUES (?,?,?,?,?)",
                              (batch_id,stamp,stats["inserted"],stats["updated"],stats["rejected"]))
        return stats

    def snapshot(self) -> dict[str, Any]:
        from scripts.build_candidate_market_dashboard import build_snapshot
        self.conn.row_factory = sqlite3.Row
        rows = [dict(r) for r in self.conn.execute("SELECT * FROM candidate_vacancies ORDER BY posted_at DESC, identity_key")]
        data = [{"title": r["title"], "url": r["url"], "company": r["advertiser"],
                 "location": r["location"], "posted_at": r["posted_at"]} for r in rows]
        snapshot = build_snapshot(data)
        snapshot["mode"] = "offline_sqlite_candidate_only"
        snapshot["review_required"] = sum(int(r["review_required"]) for r in rows)
        snapshot["vacancies"] = [
            {**item, "first_seen_at": rows_by_url[item["url"]]["first_seen_at"],
             "last_seen_at": rows_by_url[item["url"]]["last_seen_at"],
             "sources": self._sources(rows_by_url[item["url"]]["identity_key"])}
            for item in snapshot["vacancies"]
        ] if (rows_by_url := {r["url"]: r for r in rows}) else []
        return snapshot

    def _sources(self, key: str) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT source FROM candidate_sources WHERE identity_key=? ORDER BY source", (key,))]
