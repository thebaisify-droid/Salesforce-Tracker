from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from tracker.normalize import canonical_url

SOURCE_LABELS = {
    "source_1": "CV-Library",
    "source_2": "Totaljobs",
    "source_3": "Reed",
}

ROLE_DISPLAY_ALIASES = {
    "Engineering / Development": "Development / Engineering",
    "Programme / Project Delivery": "Delivery / Programme",
    "Functional Consulting": "Consulting / Functional",
    "Administration / Platform": "Platform / Administration",
    "Product / Ownership": "Product / Platform Ownership",
    "Sales / Pre-Sales": "Sales / Account Management",
    "Quality / Release / DevOps": "Testing / QA",
}

SECTOR_DISPLAY_ALIASES = {
    "Unresolved": "Unknown",
}


def _key(url: str | None, title: str | None, location: str | None, posted_at: str | None) -> str:
    clean = canonical_url(url)
    if clean:
        return "url:" + clean.lower()
    return "fallback:" + "|".join((title or "", location or "", (posted_at or "")[:10])).lower()


def _source_items(row: dict[str, Any]) -> list[dict[str, Any]]:
    primary = row.get("primary_source_label")
    apply_url = row.get("apply_url")
    items = []
    for key in row.get("source_keys") or []:
        label = SOURCE_LABELS.get(key, key)
        items.append({
            "key": key,
            "label": label,
            "url": apply_url if label == primary else None,
        })
    if not items and primary:
        reverse = {v: k for k, v in SOURCE_LABELS.items()}
        items.append({"key": reverse.get(primary, primary), "label": primary, "url": apply_url})
    return items


def baseline_vacancy(row: dict[str, Any]) -> dict[str, Any]:
    sector = row.get("sector") or "Unknown"
    return {
        "id": row.get("legacy_id"),
        "legacy_id": row.get("legacy_id"),
        "title": row.get("title"),
        "relevance": row.get("relevance") or "ADJACENT",
        "advertiser": None,
        "advertiser_type": "MIXED_OR_UNKNOWN",
        "role_family": row.get("role_family") or "Unresolved",
        "seniority": row.get("seniority") or "Standard",
        "specialisms": [],
        "end_client_name": row.get("employer_client"),
        "sector": sector,
        "location": row.get("location"),
        "work_mode": row.get("work_mode"),
        "employment_type": row.get("employment"),
        "contract_type": row.get("contract_detail"),
        "salary": {"min": None, "max": None, "currency": "GBP", "period": None},
        "salary_text": row.get("pay_text") or "Not disclosed",
        "url": row.get("apply_url"),
        "posted_at": row.get("posted_at"),
        "first_seen_at": row.get("posted_at"),
        "last_seen_at": row.get("posted_at"),
        "review": {"role": False, "sector": sector in {"Unknown", "Unresolved"}},
        "sources": _source_items(row),
        "baseline": True,
    }


def canonical_role_family(value: str | None) -> str:
    value = value or "Unresolved"
    return ROLE_DISPLAY_ALIASES.get(value, value)


def canonical_sector(vacancy: dict[str, Any]) -> str:
    advertiser = (vacancy.get("advertiser") or "").strip().lower()
    if advertiser == "salesforce" or advertiser.startswith("salesforce "):
        return "Technology Services"
    value = vacancy.get("sector") or "Unknown"
    return SECTOR_DISPLAY_ALIASES.get(value, value)


def live_relevance(vacancy: dict[str, Any]) -> str:
    title = (vacancy.get("title") or "").lower()
    direct = ("salesforce", "sfdc", "mulesoft", "sales cloud", "service cloud", "experience cloud", "marketing cloud")
    return "CORE" if any(term in title for term in direct) else "ADJACENT"


def _merge_sources(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in [*(left or []), *(right or [])]:
        key = str(item.get("key") or item.get("label") or "")
        if not key:
            continue
        if key not in merged:
            merged[key] = dict(item)
        elif not merged[key].get("url") and item.get("url"):
            merged[key]["url"] = item["url"]
    return sorted(merged.values(), key=lambda item: item.get("label") or "")


def merge_with_baseline(live_snapshot: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    by_key: dict[str, dict[str, Any]] = {}
    baseline_keys: set[str] = set()

    for row in baseline.get("rows") or []:
        vacancy = baseline_vacancy(row)
        key = _key(vacancy.get("url"), vacancy.get("title"), vacancy.get("location"), vacancy.get("posted_at"))
        by_key[key] = vacancy
        baseline_keys.add(key)

    for raw in live_snapshot.get("vacancies") or []:
        live = dict(raw)
        live["relevance"] = live_relevance(live)
        live["role_family"] = canonical_role_family(live.get("role_family"))
        live["sector"] = canonical_sector(live)
        if (live.get("advertiser") or "").strip().lower() == "salesforce":
            review = dict(live.get("review") or {})
            review["sector"] = False
            live["review"] = review
        live["salary_text"] = None
        live["work_mode"] = live.get("work_mode")
        live["baseline"] = False
        key = _key(live.get("url"), live.get("title"), live.get("location"), live.get("posted_at"))
        if key in by_key:
            base = by_key[key]
            base["sources"] = _merge_sources(base.get("sources", []), live.get("sources", []))
            base["last_seen_at"] = live.get("last_seen_at") or base.get("last_seen_at")
            base["url"] = live.get("url") or base.get("url")
            base["advertiser"] = live.get("advertiser") or base.get("advertiser")
            base["advertiser_type"] = live.get("advertiser_type") or base.get("advertiser_type")
            base["review"] = live.get("review") or base.get("review")
            salary = live.get("salary") or {}
            if salary.get("min") is not None or salary.get("max") is not None:
                base["salary"] = salary
            if not base.get("end_client_name"):
                base["end_client_name"] = live.get("end_client_name")
        else:
            by_key[key] = live

    vacancies = sorted(
        by_key.values(),
        key=lambda item: ((item.get("posted_at") or ""), str(item.get("id") or "")),
        reverse=True,
    )

    role_counts = Counter((item.get("role_family") or "Unresolved") for item in vacancies)
    sector_counts = Counter((item.get("sector") or "Unresolved") for item in vacancies)
    relevance_counts = Counter((item.get("relevance") or "ADJACENT") for item in vacancies)
    advertiser_counts = Counter((item.get("advertiser_type") or "MIXED_OR_UNKNOWN") for item in vacancies)
    source_counts: Counter[str] = Counter()
    for vacancy in vacancies:
        for source in {item.get("key") for item in vacancy.get("sources") or [] if item.get("key")}:
            source_counts[source] += 1

    review_role = sum(bool((item.get("review") or {}).get("role")) for item in vacancies)
    review_sector = sum(bool((item.get("review") or {}).get("sector")) for item in vacancies)

    baseline_date = baseline.get("baseline_date")
    post_baseline_new = sum(
        1
        for key, item in by_key.items()
        if key not in baseline_keys and (item.get("first_seen_at") or "")[:10] > str(baseline_date or "")
    )

    merged = dict(live_snapshot)
    merged.update({
        "active_vacancies": len(vacancies),
        "by_role_family": [{"label": key, "value": value} for key, value in role_counts.most_common()],
        "by_sector": [{"label": key, "value": value} for key, value in sector_counts.most_common()],
        "by_relevance": [{"label": key, "value": value} for key, value in relevance_counts.most_common()],
        "by_advertiser_type": [{"label": key, "value": value} for key, value in advertiser_counts.most_common()],
        "by_source": [
            {"key": key, "label": SOURCE_LABELS.get(key, key), "value": value}
            for key, value in source_counts.most_common()
        ],
        "review_queue": {"role": review_role, "sector": review_sector},
        "vacancies": vacancies,
        "baseline": {
            "date": baseline_date,
            "frozen_baseline": int(baseline.get("frozen_baseline") or 0),
            "late_discoveries": int(baseline.get("late_discoveries") or 0),
            "confirmed_expired": int(baseline.get("confirmed_expired") or 0),
            "post_baseline_new": post_baseline_new,
            "master_rows": int(baseline.get("active_vacancies") or 0),
        },
    })
    return merged
