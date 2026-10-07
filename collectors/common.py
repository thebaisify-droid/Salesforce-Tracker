from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def _subst(value: Any, values: dict[str, str]) -> Any:
    if isinstance(value, str):
        for key, replacement in values.items():
            value = value.replace("{" + key + "}", replacement)
        if value.startswith("env:"):
            env_name = value[4:]
            env_value = os.environ.get(env_name)
            if env_value is None:
                raise RuntimeError(f"required environment variable is missing: {env_name}")
            return env_value
        return value
    if isinstance(value, list):
        return [_subst(v, values) for v in value]
    if isinstance(value, dict):
        return {k: _subst(v, values) for k, v in value.items()}
    return value


def _request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: Any = None,
    timeout: int = 240,
) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, method=method, headers=request_headers)
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _request_form_json(url: str, form: dict[str, str], timeout: int = 60) -> Any:
    req = Request(
        url,
        data=urlencode(form).encode("utf-8"),
        method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_list(payload: Any, collection_key: str | None = None) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        keys = [collection_key] if collection_key else ["records", "jobs", "vacancies", "items", "data", "results", "postings"]
        for key in keys:
            if key and isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
    raise RuntimeError("source response did not contain a recognised record list")


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            seconds = float(value) / 1000 if float(value) > 10_000_000_000 else float(value)
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        text = str(value).strip()
        if text.isdigit():
            return _parse_time(int(text))
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            text += "T00:00:00+00:00"
        elif text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def _filter_window(records: list[dict[str, Any]], field: str | None, since: str, until: str) -> list[dict[str, Any]]:
    if not field:
        return records
    start = _parse_time(since)
    end = _parse_time(until)
    if not start or not end:
        return records
    filtered: list[dict[str, Any]] = []
    for record in records:
        raw_value = record.get(field)
        timestamp = _parse_time(raw_value)
        if timestamp is None:
            continue
        raw_text = str(raw_value).strip()
        if len(raw_text) == 10 and raw_text[4] == "-" and raw_text[7] == "-":
            # A date-only source has no clock precision. Include the whole
            # boundary date rather than risk dropping a valid overlap record.
            if start.date() <= timestamp.date() <= end.date():
                filtered.append(record)
        elif start <= timestamp <= end:
            filtered.append(record)
    return filtered


def _collect_adzuna(cfg: dict[str, Any], values: dict[str, str]) -> list[dict[str, Any]]:
    app_id = _subst(cfg.get("app_id", "env:ADZUNA_APP_ID"), values)
    app_key = _subst(cfg.get("app_key", "env:ADZUNA_APP_KEY"), values)
    country = str(cfg.get("country", "gb"))
    query = str(cfg.get("query", "Salesforce"))
    where = cfg.get("where")
    results_per_page = int(cfg.get("results_per_page", 50))
    max_pages = int(cfg.get("max_pages", 10))
    since_dt = _parse_time(values["since"])
    until_dt = _parse_time(values["until"])
    days = 4
    if since_dt and until_dt:
        days = max(1, math.ceil((until_dt - since_dt).total_seconds() / 86400) + 1)

    rows: list[dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": results_per_page,
            "what": query,
            "sort_by": "date",
            "max_days_old": days,
            "content-type": "application/json",
        }
        if where:
            params["where"] = where
        url = f"https://api.adzuna.com/v1/api/jobs/{quote(country)}/search/{page}?{urlencode(params)}"
        payload = _request_json(url, timeout=int(cfg.get("timeout_seconds", 90)))
        page_rows = _extract_list(payload, "results")
        rows.extend(page_rows)
        if len(page_rows) < results_per_page:
            break
    return _filter_window(rows, "created", values["since"], values["until"])


def _collect_lightcast_uk(cfg: dict[str, Any], values: dict[str, str]) -> list[dict[str, Any]]:
    client_id = _subst(cfg.get("client_id", "env:LIGHTCAST_CLIENT_ID"), values)
    client_secret = _subst(cfg.get("client_secret", "env:LIGHTCAST_CLIENT_SECRET"), values)
    token_payload = _request_form_json(
        "https://auth.emsicloud.com/connect/token",
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
            "scope": "postings:uk",
        },
    )
    token = token_payload.get("access_token")
    if not token:
        raise RuntimeError("Lightcast authentication returned no access token")

    limit = int(cfg.get("limit", 10))
    max_pages = int(cfg.get("max_pages", 20))
    keyword = str(cfg.get("keyword", "Salesforce"))
    fields = cfg.get(
        "fields",
        ["id", "posted", "expired", "body", "city_name", "company_name", "title_raw", "url", "score",
         "employment_type_name", "contract_type_name", "salary"],
    )
    start = (_parse_time(values["since"]) or datetime.now(timezone.utc)).date().isoformat()
    end = (_parse_time(values["until"]) or datetime.now(timezone.utc)).date().isoformat()

    rows: list[dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {token}"}
    for page in range(1, max_pages + 1):
        body = {
            "filter": {
                "when": {"start": start, "end": end},
                "keywords": {"query": keyword, "type": "phrase"},
            },
            "fields": fields,
            "order": ["posted"],
            "limit": limit,
            "page": page,
        }
        payload = _request_json(
            "https://api.lightcast.io/uk-jpa/postings",
            method="POST",
            headers=headers,
            body=body,
            timeout=int(cfg.get("timeout_seconds", 90)),
        )
        page_rows = _extract_list(payload, cfg.get("collection_key"))
        rows.extend(page_rows)
        if len(page_rows) < limit:
            break
    return _filter_window(rows, "posted", values["since"], values["until"])


def collect(slot: int, *, since: str, until: str) -> list[dict[str, Any]]:
    path = ROOT / "config" / "sources" / f"source_{slot}.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not cfg.get("ready"):
        raise RuntimeError(f"source_{slot} is not configured yet; set ready=true after selecting the live provider")

    values = {"since": since, "until": until}
    provider = cfg.get("provider")

    if provider == "fixture":
        fixture_path = ROOT / _subst(cfg["path"], values)
        return _extract_list(json.loads(fixture_path.read_text(encoding="utf-8")), cfg.get("collection_key"))

    if provider == "http_json":
        url = _subst(cfg["url"], values)
        query = _subst(cfg.get("query_params", cfg.get("query", {})), values)
        if query:
            url += ("&" if "?" in url else "?") + urlencode(query)
        headers = _subst(cfg.get("headers", {}), values)
        payload = _request_json(
            url,
            method=cfg.get("method", "GET"),
            headers=headers,
            body=_subst(cfg.get("body"), values),
            timeout=int(cfg.get("timeout_seconds", 240)),
        )
        return _filter_window(
            _extract_list(payload, cfg.get("collection_key")),
            cfg.get("window_field"),
            since,
            until,
        )

    if provider == "adzuna":
        return _collect_adzuna(cfg, values)

    if provider == "lightcast_uk":
        return _collect_lightcast_uk(cfg, values)

    if provider == "apify_actor":
        actor_id = _subst(cfg.get("actor_id") or cfg.get("actor_id_env", "env:APIFY_ACTOR_ID"), values)
        token = _subst(cfg.get("token", "env:APIFY_TOKEN"), values)
        actor_input = _subst(cfg.get("input", {}), values)
        params = {"token": token, "format": "json", "clean": "true"}
        url = f"https://api.apify.com/v2/acts/{quote(actor_id, safe='~')}/run-sync-get-dataset-items?{urlencode(params)}"
        payload = _request_json(url, method="POST", body=actor_input, timeout=int(cfg.get("timeout_seconds", 300)))
        rows = _extract_list(payload, cfg.get("collection_key"))
        return _filter_window(rows, cfg.get("window_field"), since, until)

    if provider == "apify_task":
        task_id = _subst(cfg.get("task_id") or cfg.get("task_id_env", "env:APIFY_TASK_ID"), values)
        token = _subst(cfg.get("token", "env:APIFY_TOKEN"), values)
        params = {"token": token, "format": "json", "clean": "true"}
        url = f"https://api.apify.com/v2/actor-tasks/{quote(task_id, safe='~')}/run-sync-get-dataset-items?{urlencode(params)}"
        payload = _request_json(url, method="POST", timeout=int(cfg.get("timeout_seconds", 300)))
        rows = _extract_list(payload, cfg.get("collection_key"))
        return _filter_window(rows, cfg.get("window_field"), since, until)

    raise RuntimeError(f"unsupported provider for source_{slot}: {provider!r}")


def run_slot(slot: int) -> int:
    p = argparse.ArgumentParser(description=f"Collect incremental records for source slot {slot}")
    p.add_argument("--incremental", action="store_true")
    p.add_argument("--since", required=True)
    p.add_argument("--until", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    try:
        records = collect(slot, since=args.since, until=args.until)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"source": slot, "records": len(records), "output": str(output)}))
        return 0
    except Exception as exc:
        print(f"source_{slot} collection failed: {exc}", file=sys.stderr)
        return 2
