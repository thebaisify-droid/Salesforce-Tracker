from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from tracker.store import Store

UNAVAILABLE_MARKERS = (
    "job has expired",
    "job is no longer available",
    "this job is no longer available",
    "vacancy has closed",
    "vacancy is closed",
    "job has been removed",
    "job no longer exists",
    "position has been filled",
    "no longer accepting applications",
    "this vacancy is no longer available",
    "this role is no longer available",
)


@dataclass
class UrlObservation:
    result: str
    evidence_type: str
    checked_url: str
    final_url: str | None = None
    http_status: int | None = None
    detail: str | None = None


def utc_iso(value: datetime | None = None) -> str:
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def assess_response(
    *,
    checked_url: str,
    http_status: int,
    body: str,
    final_url: str | None = None,
) -> UrlObservation:
    lowered = body.lower()
    for marker in UNAVAILABLE_MARKERS:
        if marker in lowered:
            return UrlObservation(
                "UNAVAILABLE",
                "BODY_UNAVAILABLE_MARKER",
                checked_url,
                final_url,
                http_status,
                marker,
            )

    if 200 <= http_status < 300:
        if final_url:
            original = urlsplit(checked_url)
            final = urlsplit(final_url)
            if original.netloc == final.netloc and original.path not in {"", "/"} and final.path in {"", "/"}:
                return UrlObservation(
                    "INCONCLUSIVE",
                    "REDIRECTED_TO_SITE_ROOT",
                    checked_url,
                    final_url,
                    http_status,
                )
        return UrlObservation(
            "AVAILABLE",
            "HTTP_SUCCESS",
            checked_url,
            final_url,
            http_status,
        )

    if http_status in {404, 410}:
        return UrlObservation(
            "UNAVAILABLE",
            f"HTTP_{http_status}",
            checked_url,
            final_url,
            http_status,
        )

    return UrlObservation(
        "INCONCLUSIVE",
        f"HTTP_{http_status}",
        checked_url,
        final_url,
        http_status,
    )


def check_url(url: str, *, timeout_seconds: int = 8, max_bytes: int = 256_000) -> UrlObservation:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; ZarafyTek-Salesforce-Lifecycle/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-GB,en;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = int(getattr(response, "status", 200))
            final_url = response.geturl()
            body = response.read(max_bytes).decode("utf-8", errors="ignore")
            return assess_response(
                checked_url=url,
                http_status=status,
                body=body,
                final_url=final_url,
            )
    except HTTPError as exc:
        status = int(exc.code)
        body = ""
        try:
            body = exc.read(max_bytes).decode("utf-8", errors="ignore")
        except Exception:
            pass
        return assess_response(
            checked_url=url,
            http_status=status,
            body=body,
            final_url=exc.geturl() if hasattr(exc, "geturl") else url,
        )
    except (URLError, TimeoutError, OSError) as exc:
        return UrlObservation(
            "INCONCLUSIVE",
            "NETWORK_ERROR",
            url,
            detail=str(exc)[:240],
        )
    except Exception as exc:
        return UrlObservation(
            "INCONCLUSIVE",
            "CHECK_ERROR",
            url,
            detail=str(exc)[:240],
        )


def _candidate_rows(store: Store, *, now: datetime, min_age_days: int, limit: int) -> list[Any]:
    cutoff = utc_iso(now - timedelta(days=min_age_days))
    return store.conn.execute(
        """
        SELECT vacancy_id, display_title, job_url, posted_at, first_seen_at,
               lifecycle_status, last_verified_at
        FROM vacancies
        WHERE is_active=1
          AND job_url IS NOT NULL
          AND job_url <> ''
          AND COALESCE(posted_at, first_seen_at) <= ?
        ORDER BY
          CASE WHEN last_verified_at IS NULL THEN 0 ELSE 1 END,
          COALESCE(last_verified_at, '') ASC,
          COALESCE(posted_at, first_seen_at) ASC,
          vacancy_id ASC
        LIMIT ?
        """,
        (cutoff, limit),
    ).fetchall()


def _candidate_urls(store: Store, vacancy_id: int, primary_url: str | None, max_urls: int = 2) -> list[str]:
    values: list[str] = []
    if primary_url:
        values.append(primary_url)
    for row in store.conn.execute(
        """
        SELECT source_url
        FROM vacancy_sources
        WHERE vacancy_id=? AND source_url IS NOT NULL AND source_url <> ''
        ORDER BY last_seen_at DESC, source_name
        """,
        (vacancy_id,),
    ):
        if row["source_url"] not in values:
            values.append(row["source_url"])
    return values[:max_urls]


def _aggregate(observations: list[UrlObservation]) -> UrlObservation:
    available = [item for item in observations if item.result == "AVAILABLE"]
    if available:
        chosen = available[0]
        return UrlObservation(
            "AVAILABLE",
            chosen.evidence_type,
            chosen.checked_url,
            chosen.final_url,
            chosen.http_status,
            "at least one source URL is available",
        )
    unavailable = [item for item in observations if item.result == "UNAVAILABLE"]
    if unavailable:
        chosen = unavailable[0]
        return UrlObservation(
            "UNAVAILABLE",
            chosen.evidence_type,
            chosen.checked_url,
            chosen.final_url,
            chosen.http_status,
            f"{len(unavailable)} source URL(s) explicitly unavailable; no source URL confirmed available",
        )
    chosen = observations[0] if observations else UrlObservation("INCONCLUSIVE", "NO_URL", "")
    return UrlObservation(
        "INCONCLUSIVE",
        chosen.evidence_type,
        chosen.checked_url,
        chosen.final_url,
        chosen.http_status,
        chosen.detail,
    )


def lifecycle_counts(store: Store) -> dict[str, int]:
    return {
        str(row["lifecycle_status"]): int(row["value"])
        for row in store.conn.execute(
            "SELECT lifecycle_status, COUNT(*) value FROM vacancies GROUP BY lifecycle_status"
        )
    }


def run_verification(
    store: Store,
    *,
    now: datetime | None = None,
    min_age_days: int = 14,
    limit: int = 20,
    confirmations: int = 2,
    min_confirmation_hours: float = 12.0,
    timeout_seconds: int = 8,
    max_workers: int = 6,
    dry_run: bool = False,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    checked_at = utc_iso(now)
    candidates = _candidate_rows(store, now=now, min_age_days=min_age_days, limit=limit)

    urls_by_vacancy: dict[int, list[str]] = {}
    title_by_vacancy: dict[int, str] = {}
    current_by_vacancy: dict[int, str] = {}
    for row in candidates:
        vacancy_id = int(row["vacancy_id"])
        urls_by_vacancy[vacancy_id] = _candidate_urls(store, vacancy_id, row["job_url"])
        title_by_vacancy[vacancy_id] = str(row["display_title"])
        current_by_vacancy[vacancy_id] = str(row["lifecycle_status"] or "ACTIVE")

    observations_by_vacancy: dict[int, list[UrlObservation]] = defaultdict(list)
    futures = {}
    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        for vacancy_id, urls in urls_by_vacancy.items():
            for url in urls:
                future = executor.submit(check_url, url, timeout_seconds=timeout_seconds)
                futures[future] = vacancy_id
        for future in as_completed(futures):
            vacancy_id = futures[future]
            try:
                observations_by_vacancy[vacancy_id].append(future.result())
            except Exception as exc:
                observations_by_vacancy[vacancy_id].append(
                    UrlObservation("INCONCLUSIVE", "WORKER_ERROR", "", detail=str(exc)[:240])
                )

    observation_counts: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    items: list[dict[str, Any]] = []
    for row in candidates:
        vacancy_id = int(row["vacancy_id"])
        observations = observations_by_vacancy.get(vacancy_id, [])
        aggregate = _aggregate(observations)
        observation_counts[aggregate.result] += 1
        before = current_by_vacancy[vacancy_id]
        after = before
        if not dry_run:
            after = store.record_lifecycle_observation(
                vacancy_id,
                result=aggregate.result,
                evidence_type=aggregate.evidence_type,
                checked_at=checked_at,
                checked_url=aggregate.checked_url or None,
                final_url=aggregate.final_url,
                http_status=aggregate.http_status,
                detail=aggregate.detail,
                confirmations=confirmations,
                min_confirmation_hours=min_confirmation_hours,
            )
        transition_counts[f"{before}->{after}"] += 1
        items.append({
            "vacancy_id": vacancy_id,
            "title": title_by_vacancy[vacancy_id],
            "before": before,
            "after": after,
            "observation": aggregate.result,
            "evidence_type": aggregate.evidence_type,
            "url_checks": [asdict(item) for item in observations],
        })

    return {
        "schema": "salesforce-lifecycle/v1",
        "passed": True,
        "checked_at": checked_at,
        "dry_run": dry_run,
        "policy": {
            "min_age_days": min_age_days,
            "limit": limit,
            "confirmations_required": confirmations,
            "min_confirmation_hours": min_confirmation_hours,
            "rule": "Only repeated explicit unavailable evidence can confirm expiry; inconclusive checks never expire a vacancy.",
        },
        "candidates_selected": len(candidates),
        "observations": dict(observation_counts),
        "transitions": dict(transition_counts),
        "lifecycle_counts": lifecycle_counts(store),
        "items": items,
    }
