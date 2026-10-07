from __future__ import annotations

import argparse
import json
import os
import sys
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


def _request_json(url: str, *, method: str = "GET", headers: dict[str, str] | None = None, body: Any = None, timeout: int = 240) -> Any:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    req = Request(url, data=data, method=method, headers=request_headers)
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_list(payload: Any, collection_key: str | None = None) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        keys = [collection_key] if collection_key else ["records", "jobs", "vacancies", "items", "data"]
        for key in keys:
            if key and isinstance(payload.get(key), list):
                return [x for x in payload[key] if isinstance(x, dict)]
    raise RuntimeError("source response did not contain a recognised record list")


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
        query = _subst(cfg.get("query", {}), values)
        if query:
            url += ("&" if "?" in url else "?") + urlencode(query)
        headers = _subst(cfg.get("headers", {}), values)
        payload = _request_json(url, method=cfg.get("method", "GET"), headers=headers, body=_subst(cfg.get("body"), values))
        return _extract_list(payload, cfg.get("collection_key"))

    if provider == "apify_actor":
        actor_id = _subst(cfg.get("actor_id") or cfg.get("actor_id_env", "env:APIFY_ACTOR_ID"), values)
        token = _subst(cfg.get("token", "env:APIFY_TOKEN"), values)
        actor_input = _subst(cfg.get("input", {}), values)
        params = {"token": token, "format": "json", "clean": "true"}
        url = f"https://api.apify.com/v2/acts/{quote(actor_id, safe='~')}/run-sync-get-dataset-items?{urlencode(params)}"
        payload = _request_json(url, method="POST", body=actor_input, timeout=int(cfg.get("timeout_seconds", 300)))
        return _extract_list(payload, cfg.get("collection_key"))

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
