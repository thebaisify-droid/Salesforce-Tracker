"""Single-attempt authenticated sender; defaults to offline validation only.

Never runs Apify, starts a workflow, schedules a refresh, or retries HTTP.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from scripts.validate_salesforce_wordpress_delivery import inspect

ENDPOINT = "https://jobs.zarafytek.com/wp-json/salesforce-tracker/v1/snapshot"


def build_envelope(raw: bytes) -> dict:
    return {"snapshot": raw.decode("utf-8"), "sha256": hashlib.sha256(raw).hexdigest()}


def verify_destination(value: str) -> None:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname != "jobs.zarafytek.com"
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise ValueError("Only the exact HTTPS WordPress site is authorised")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("WordPress delivery redirects are forbidden")


def publish_once(raw: bytes, username: str, app_password: str, *, opener=None) -> dict:
    if not username or not app_password:
        raise ValueError("Missing WordPress application credentials")
    envelope = build_envelope(raw)
    token = base64.b64encode((username + ":" + app_password).encode()).decode()
    request = Request(ENDPOINT, data=json.dumps(envelope).encode("utf-8"), method="POST",
                      headers={"Authorization": "Basic " + token, "Content-Type": "application/json",
                               "Accept": "application/json", "User-Agent": "sf-one-shot-publisher/1"})
    # Caller only supplies preverified, current snapshots. One request only.
    transport = opener or build_opener(HTTPSHandler(), NoRedirect())
    with transport.open(request, timeout=20) as response:
        payload = json.load(response)
    if payload.get("accepted") is not True or payload.get("sha256") != envelope["sha256"]:
        raise ValueError("Receiver acknowledgement does not match snapshot")
    return {"sent": True, "checksum_verified": True, "sha256": envelope["sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dashboard/live-data.json")
    parser.add_argument("--site", default="https://jobs.zarafytek.com")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    verify_destination(args.site)
    raw = Path(args.input).read_bytes()
    report = inspect(raw)
    if not args.send:
        print(json.dumps({"mode": "DRY_RUN_ONLY", **report}, sort_keys=True))
        return 0
    if os.environ.get("SF_DELIVERY_APPROVED") != "yes":
        raise SystemExit("One-time publication approval not provided")
    result = publish_once(raw, os.environ.get("SF_WP_USERNAME", ""),
                          os.environ.get("SF_WP_APPLICATION_PASSWORD", ""))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
