"""Strict, no-network BA publication assurance before WordPress delivery.

Works on the existing completed source observations. A historical *posted*
date is reported, never mistaken for an expired *source observation*.
No employer availability check, acquisition or network request is performed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

EXPECTED = {"CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe"}
MAX_RECORDS = 450


def observed_time(raw: object) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Missing source observation timestamp")
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Malformed source observation timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("Source observation timestamp must contain timezone")
    return dt.astimezone(timezone.utc)


def validate_publication(snapshot: dict, now: datetime) -> dict:
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("An aware validation clock is required")
    now = now.astimezone(timezone.utc)
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "ba-live-snapshot/v1":
        raise ValueError("Invalid BA live snapshot schema")
    refresh, quality = snapshot.get("refresh"), snapshot.get("quality")
    if (not isinstance(refresh, dict) or refresh.get("status") != "success"
            or refresh.get("source_observed_not_employer_confirmed") is not True
            or not isinstance(quality, dict) or quality.get("passed") is not True
            or quality.get("independently_confirmed_open") is not False):
        raise ValueError("Data quality or source-observed provenance gate failed")
    receipts = snapshot.get("sources")
    if not isinstance(receipts, list) or len(receipts) != 5:
        raise ValueError("Exactly five source receipts required")
    by_source = {}
    for source in receipts:
        if (not isinstance(source, dict) or source.get("source") not in EXPECTED
                or source["source"] in by_source or source.get("status") != "SUCCEEDED"
                or source.get("attempted") is not True
                or not isinstance(source.get("run_id"), str) or not source["run_id"]
                or not isinstance(source.get("dataset_id"), str) or not source["dataset_id"]):
            raise ValueError("Incomplete, repeated or unverified source receipt")
        by_source[source["source"]] = source
    if set(by_source) != EXPECTED:
        raise ValueError("Five known sources must be represented by receipts")
    rows = snapshot.get("records")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_RECORDS:
        raise ValueError("Empty or oversized publication batch")
    if quality.get("matched_advertisements") != len(rows):
        raise ValueError("QA matched count and source rows differ")
    seen_ids, seen_adverts = set(), set()
    old_90, missing_post_date, missing_sector = 0, 0, 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed advert record")
        source = row.get("source")
        receipt = by_source.get(source)
        if (receipt is None or row.get("source_run_id") != receipt["run_id"]
                or row.get("dataset_id") != receipt["dataset_id"]
                or row.get("source_observed_only") is not True
                or row.get("job_source") != source):
            raise ValueError("Advert source/run/dataset provenance mismatch")
        url = row.get("url")
        if not isinstance(url, str) or row.get("original_advert_url") != url:
            raise ValueError("Original advert URL mismatch")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Unsafe original advert URL")
        ident = row.get("id")
        if (not isinstance(ident, str) or not ident or ident in seen_ids
                or (source, url) in seen_adverts):
            raise ValueError("Duplicate or empty advert ID/source URL")
        seen_ids.add(ident)
        seen_adverts.add((source, url))
        if not isinstance(row.get("title"), str) or not row["title"].strip():
            raise ValueError("Missing advert title")
        if not isinstance(row.get("role_family"), str) or not row["role_family"].strip():
            raise ValueError("Missing registered role family")
        observed = observed_time(row.get("observed_at"))
        if observed < now - timedelta(days=30) or observed > now + timedelta(minutes=15):
            raise ValueError("Outside 30-day source observation window")
        posted = row.get("posted_date")
        if posted in (None, ""):
            missing_post_date += 1
        else:
            if not isinstance(posted, str) or len(posted) != 10:
                raise ValueError("Malformed original posted date")
            try:
                posted_day = date.fromisoformat(posted)
            except ValueError as exc:
                raise ValueError("Malformed original posted date") from exc
            if posted_day > now.date():
                raise ValueError("Posted date is in the future")
            if (now.date() - posted_day).days > 90:
                old_90 += 1
        if row.get("sector") in ("Not specified", None, ""):
            missing_sector += 1
    return {
        "status": "BA_PUBLICATION_ASSURANCE_PASSED",
        "records": len(rows),
        "distinct_source_adverts": len(seen_adverts),
        "source_receipts": len(by_source),
        "historical_post_dates_over_90_days": old_90,
        "missing_post_dates": missing_post_date,
        "sector_not_evidenced": missing_sector,
        "source_observed_not_employer_confirmed": True,
        "actors_started": 0,
        "wordpress_requests": 0,
    }
