"""Offline, non-publishing freshness and duplicate review for candidate vacancies.

This module never starts Apify Actors, mutates databases or approves publication.
Cross-board duplicate signals are intentionally conservative review flags, never
automatic removals.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import re
import unicodedata
from typing import Any

from tracker.business_product_delivery_security import classify_raw
from scripts.build_candidate_market_dashboard import _clean_url

ALLOWED_SOURCES = frozenset(("CV-Library", "Totaljobs", "Indeed UK", "JobServe", "Reed"))
FRESHNESS_DAYS = 7


def posting_day(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        pass
    for fmt in ("%A, %d %B %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _word_key(value: str) -> str:
    # Normalize spacing, capitalization and punctuation without dropping
    # seniority, product names or employer identity.
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"\w+", normalized, flags=re.UNICODE))


def _possible_duplicate_key(row: dict[str, Any]) -> tuple[str, str, str] | None:
    title, employer, location = (
        row.get("title"), row.get("company"), row.get("location")
    )
    if not all(isinstance(v, str) and v.strip() for v in (title, employer, location)):
        return None
    return _word_key(title), _word_key(employer), _word_key(location)


def assess_refresh_quality(
    records: list[dict[str, Any]], *, as_of: date | None = None
) -> dict[str, Any]:
    if not isinstance(records, list):
        raise ValueError("Expected a list of normalised candidate rows")
    as_of = as_of or datetime.now(timezone.utc).date()
    classified = []
    invalid_source = 0
    matched = 0
    missing_dates = stale = future = fresh = manual_role_review = 0
    sources_seen = set()
    exact_urls: dict[str, set[str]] = defaultdict(set)
    url_seen = set()
    exact_url_repeated_rows = 0
    signatures: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for row in records:
        if not isinstance(row, dict):
            invalid_source += 1
            continue
        source = row.get("source")
        if source not in ALLOWED_SOURCES:
            invalid_source += 1
            continue
        sources_seen.add(source)
        decision = classify_raw(row)
        if not decision["included"]:
            continue
        url = _clean_url(row.get("url"))
        if not url or not url.startswith("https://"):
            invalid_source += 1
            continue
        matched += 1
        manual_role_review += int(bool(decision["review_required"]))
        day = posting_day(row.get("posted_at"))
        if day is None:
            missing_dates += 1
        elif day > as_of:
            future += 1
        elif (as_of - day).days > FRESHNESS_DAYS:
            stale += 1
        else:
            fresh += 1

        normalized_url = url.casefold()
        if normalized_url in url_seen:
            exact_url_repeated_rows += 1
        url_seen.add(normalized_url)
        exact_urls[normalized_url].add(source)
        signature = _possible_duplicate_key(row)
        if signature:
            signatures[signature].add(source)

    # A group with multiple sources signals possible duplication, not certainty.
    candidate_groups = sum(len(source_set) > 1 for source_set in signatures.values())
    exact_url_cross_source_groups = sum(
        len(source_set) > 1 for source_set in exact_urls.values()
    )
    reasons = ["independent_live_vacancy_verification_missing",
               "publication_requires_separate_approval"]
    if stale:
        reasons.append("stale_posting_dates")
    if missing_dates:
        reasons.append("missing_posting_dates")
    if future:
        reasons.append("future_posting_dates")
    if invalid_source:
        reasons.append("invalid_or_unknown_source_rows")
    if manual_role_review:
        reasons.append("ambiguous_role_classification")
    if candidate_groups or exact_url_cross_source_groups:
        reasons.append("possible_cross_source_duplicates_require_review")
    return {
        "schema": "candidate-refresh-quality/v1",
        "mode": "HISTORICAL_REVIEW_ONLY",
        "as_of_date": as_of.isoformat(),
        "freshness_window_days": FRESHNESS_DAYS,
        "input_job_rows": len(records),
        "classified_rows": matched,
        "classified_fresh": fresh,
        "classified_stale": stale,
        "classified_missing_date": missing_dates,
        "classified_future_date": future,
        "role_review_required": manual_role_review,
        "invalid_or_unknown_source_rows": invalid_source,
        "exact_url_repeated_rows": exact_url_repeated_rows,
        "exact_url_cross_source_groups": exact_url_cross_source_groups,
        "possible_title_employer_location_cross_source_groups": candidate_groups,
        "sources_seen": sorted(sources_seen),
        "release_blockers": reasons,
        "ready_for_publication": False,
        "publication_approved": False,
        "acquisition_enabled": False,
        "auto_apply_expiry_events": False,
        "note": "Posting recency does not establish an open vacancy. "
                "Possible cross-board duplicates require independent adjudication. "
                "Counts are not representative market estimates.",
    }
