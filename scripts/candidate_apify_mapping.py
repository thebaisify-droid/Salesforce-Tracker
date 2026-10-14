"""Source-specific allowlist normalisation for completed Apify datasets.

Only vacancy fields are retained. CV-Library expiry events are kept in an
isolated event ledger, never as vacancies or automatic deletions.
"""
from __future__ import annotations
from typing import Any
from urllib.parse import urlsplit

def text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None

def pick(row: dict, *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        value = text(value)
        if value:
            return value
    return None

def nested(row: dict, key: str, child: str) -> str | None:
    obj = row.get(key)
    return text(obj.get(child)) if isinstance(obj, dict) else None

def safe_url(value: Any) -> str | None:
    url = text(value)
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return url

def normalise_dataset(rows: list[dict[str, Any]], source: str) -> tuple[list[dict], list[dict], dict]:
    if not isinstance(rows, list):
        raise ValueError("Expected dataset array")
    vacancies, expiry = [], []
    stats = {"input_rows":len(rows), "invalid_rows":0, "expiry_events":0}
    for row in rows:
        if not isinstance(row, dict):
            stats["invalid_rows"] += 1
            continue
        if source == "CV-Library" and row.get("changeType") == "EXPIRED":
            job_id = pick(row, "jobId")
            expired_at = pick(row, "expiredAt")
            if job_id and expired_at:
                expiry.append({"job_id":job_id,"expired_at":expired_at,"source":"CV-Library",
                               "status":"REVIEW_ONLY_NOT_APPLIED"})
            else:
                stats["invalid_rows"] += 1
            continue
        title = pick(row, "title", "jobTitle")
        url = safe_url(pick(row, "url", "jobUrl", "canonicalUrl", "sourceUrl"))
        company = pick(row, "company", "employer", "companyName") or nested(row, "company", "name") or nested(row, "employer", "name")
        location = pick(row, "location", "job_location") or nested(row, "location", "text")
        posted = pick(row, "postedAt", "postedDateTime", "postedDate", "datePosted")
        description = pick(row, "description", "descriptionText", "snippet", "descriptionSnippet")
        if not title or not url:
            stats["invalid_rows"] += 1
            continue
        vacancies.append({"title":title,"url":url,"company":company,"location":location,
                          "posted_at":posted,"description":description,"source":source,
                          "publication_approved":False})
    stats["expiry_events"] = len(expiry)
    stats["vacancy_rows"] = len(vacancies)
    return vacancies, expiry, stats
