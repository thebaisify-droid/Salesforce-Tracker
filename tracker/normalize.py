from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tracker.classify import classify, versions

COLLECTION_KEYS = ("records", "jobs", "vacancies", "items", "data", "results", "postings")
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid"}


def load_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            for key in COLLECTION_KEYS:
                if isinstance(payload.get(key), list):
                    return [r for r in payload[key] if isinstance(r, dict)]
    except json.JSONDecodeError:
        records = []
        for line in text.splitlines():
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    records.append(value)
        return records
    raise ValueError(f"Unsupported collector payload shape in {path}")


def first_value(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip()
        return value or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [text_value(v) for v in value]
        return ", ".join(v for v in parts if v) or None
    if isinstance(value, dict):
        for key in ("display_name", "name", "formatted", "text", "address"):
            if value.get(key):
                return str(value[key]).strip()
        parts = [value.get(k) for k in ("city", "locality", "region", "state", "postalCode", "country")]
        text = ", ".join(str(v).strip() for v in parts if v)
        return text or json.dumps(value, sort_keys=True)
    return str(value).strip() or None


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
        if not parts.scheme or not parts.netloc:
            return url.strip()
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))
    except Exception:
        return url.strip()


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("£", "").strip())
    except (TypeError, ValueError):
        return None


def _salary(raw: dict[str, Any]) -> tuple[float | None, float | None, str, str | None]:
    minimum = _float(first_value(raw, "salary_min", "salaryMin", "min_salary", "minSalary", "salaryFrom"))
    maximum = _float(first_value(raw, "salary_max", "salaryMax", "max_salary", "maxSalary", "salaryTo"))
    currency = text_value(first_value(raw, "salary_currency", "salaryCurrency", "currency"))
    period = text_value(first_value(raw, "salary_period", "salaryPeriod"))

    nested = raw.get("salary")
    if isinstance(nested, dict):
        raw_text = str(nested.get("rawText") or "")
        match = re.search(r"£\s*([\d,]+(?:\.\d+)?)\s*[-–]\s*(?:£\s*)?([\d,]+(?:\.\d+)?)", raw_text)
        if match:
            minimum = _float(match.group(1))
            maximum = _float(match.group(2))
        else:
            minimum = minimum if minimum is not None else _float(nested.get("min"))
            maximum = maximum if maximum is not None else _float(nested.get("max"))
        currency = currency or text_value(nested.get("currency"))
        period = period or text_value(nested.get("period"))

    return minimum, maximum, currency or "GBP", period


def _employment_type(raw: dict[str, Any]) -> str | None:
    value = first_value(raw, "employment_type", "employmentType", "employment_type_name", "workType", "jobTypes", "working_pattern")
    if value not in (None, "", [], {}):
        return text_value(value)
    if raw.get("isFullTime") is True:
        return "Full-time"
    if raw.get("isPartTime") is True:
        return "Part-time"
    return None


def normalize(raw: dict[str, Any], source_name: str) -> dict[str, Any]:
    title = text_value(first_value(raw, "title", "title_raw", "job_title", "jobTitle", "position", "name"))
    advertiser = text_value(first_value(raw, "advertiser", "company", "company_name", "companyName", "employer", "recruiter", "posted_by"))
    description = text_value(first_value(
        raw, "description", "descriptionText", "description_full", "descriptionFull",
        "job_description", "jobDescription", "body", "summary", "snippet",
        "descriptionSnippet", "description_snippet", "textSnippet", "skills_text"
    )) or ""
    location = text_value(first_value(raw, "location", "job_location", "jobLocation", "city", "city_name"))
    url = canonical_url(text_value(first_value(
        raw, "job_url", "jobUrl", "canonicalUrl", "url", "sourceUrl", "source_url",
        "link", "permalink", "application_url", "applicationUrl", "apply_url", "applyUrl", "externalUrl", "redirect_url"
    )))
    external_id = text_value(first_value(
        raw, "id", "job_id", "jobId", "externalId", "jobKey", "jobReference",
        "reference", "ref", "vacancy_id", "guid"
    )) or url
    posted_at = text_value(first_value(
        raw, "posted_at", "postedAt", "posted_at_datetime", "posted_date_time",
        "postedDateTime", "posted_date", "postedDate", "datePosted", "publishFromDate", "posted",
        "published_at", "publishedAt", "date", "created", "created_at", "createdAt"
    ))
    salary_min, salary_max, salary_currency, salary_period = _salary(raw)

    dedupe_basis = url or "|".join((title or "", advertiser or "", location or "", (posted_at or "")[:10])).lower()
    dedupe_key = hashlib.sha256(dedupe_basis.encode("utf-8")).hexdigest()

    classification = classify(title, advertiser, description)
    master_version, taxonomy_version = versions()
    normalized = {
        "dedupe_key": dedupe_key,
        "external_id": external_id,
        "display_title": title,
        "title_raw": title,
        "advertiser": advertiser,
        "location": location,
        "employment_type": _employment_type(raw),
        "contract_type": text_value(first_value(raw, "contract_type", "contractType", "contract_type_name", "jobType", "job_type", "contract_length")),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": salary_currency,
        "salary_period": salary_period,
        "job_url": url,
        "description": description,
        "posted_at": posted_at,
        "source_name": source_name,
        "source_record_id": external_id or dedupe_key,
        "master_data_version": master_version,
        "role_taxonomy_version": taxonomy_version,
        **classification,
    }
    normalized["role_specialism"] = json.dumps(normalized["role_specialism"], ensure_ascii=False)
    hash_payload = {k: v for k, v in normalized.items() if k not in {"source_name", "source_record_id"}}
    normalized["normalized_hash"] = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    normalized["raw_json"] = json.dumps(raw, sort_keys=True, ensure_ascii=False)
    return normalized


def utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
