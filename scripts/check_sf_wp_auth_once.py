"""One-shot WordPress snapshot receiver authentication probe; never sends vacancy data."""
from __future__ import annotations
import base64
import json
import os
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

URL = "https://jobs.zarafytek.com/index.php?rest_route=/salesforce-tracker/v1/snapshot"

class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Redirect prohibited")

def check(username: str, password: str, opener=None):
    if not username or not password:
        raise ValueError("Missing service credentials")
    if username != "sf_snapshot_delivery":
        raise ValueError("Unexpected delivery identity")
    # The empty JSON envelope cannot be accepted as a snapshot. Expected
    # response is HTTP 400 sf_bad_envelope, AFTER authorization succeeds.
    token = base64.b64encode((username + ":" + password).encode()).decode()
    request = Request(URL, data=b"{}", method="POST", headers={
        "Authorization": "Basic " + token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    transport = opener or build_opener(HTTPSHandler(), RejectRedirects())
    try:
        with transport.open(request, timeout=15):
            raise RuntimeError("Unexpected successful upload response")
    except HTTPError as exc:
        if exc.code != 400:
            raise RuntimeError("Auth probe failed (unexpected HTTP status)") from None
        try:
            result = json.loads(exc.read())
        except (ValueError, TypeError):
            raise RuntimeError("Auth probe failed (unrecognised response)") from None
        if result.get("code") != "sf_bad_envelope":
            raise RuntimeError("Auth probe failed (unexpected error code)")
    return {"authenticated": True, "receiver_permission_confirmed": True,
            "snapshot_uploaded": False, "actors_started": 0}

if __name__ == "__main__":
    status = check(os.environ.get("SF_WP_USERNAME", ""),
                   os.environ.get("SF_WP_APPLICATION_PASSWORD", ""))
    print(json.dumps(status, sort_keys=True))
