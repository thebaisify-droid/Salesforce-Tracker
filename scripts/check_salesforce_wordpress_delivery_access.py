"""Read-only WordPress delivery authentication preflight.

A scheduled acquisition must not spend Apify credits unless the dedicated
WordPress snapshot receiver identity is already able to deliver the feed.
This module never sends a snapshot, stores credentials or runs an Actor.
"""
from __future__ import annotations

import base64
import json
import os
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

USER_ENDPOINT = "https://jobs.zarafytek.com/wp-json/wp/v2/users/me?context=edit"
EXPECTED_USER = "sf_snapshot_delivery"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Unexpected redirect from WordPress authentication endpoint")


def verify_access(username: str, password: str, opener=None) -> dict:
    if username != EXPECTED_USER or not password:
        raise ValueError("Dedicated snapshot delivery credentials are missing or incorrect")
    token = base64.b64encode((username + ":" + password).encode()).decode()
    req = Request(
        USER_ENDPOINT,
        method="GET",
        headers={
            "Authorization": "Basic " + token,
            "Accept": "application/json",
            "User-Agent": "salesforce-delivery-readonly-preflight/1",
        },
    )
    transport = opener or build_opener(HTTPSHandler(), NoRedirect())
    with transport.open(req, timeout=15) as response:
        user = json.load(response)
    if not isinstance(user, dict):
        raise ValueError("WordPress identity response is invalid")
    identity = user.get("username") or user.get("slug")
    if identity != EXPECTED_USER:
        raise ValueError("WordPress authentication resolved to an unexpected user")
    capabilities = user.get("capabilities") or user.get("extra_capabilities") or {}
    if not isinstance(capabilities, dict) or capabilities.get("sf_deliver_snapshot") is not True:
        raise ValueError("WordPress transport identity lacks snapshot-delivery permission")
    return {
        "delivery_identity_verified": True,
        "receiver_permission_verified": True,
        "actors_started": 0,
        "snapshot_sent": False,
    }


def main() -> int:
    username = os.environ.get("SF_WP_USERNAME", "")
    password = os.environ.get("SF_WP_APPLICATION_PASSWORD", "")
    try:
        result = verify_access(username, password)
    except Exception as error:
        # Error text never includes credentials or response body.
        print(json.dumps({"delivery_preflight_passed": False, "reason": type(error).__name__,
                          "actors_started": 0, "snapshot_sent": False}))
        return 2
    print(json.dumps({"delivery_preflight_passed": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
