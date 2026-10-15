"""BA-only WordPress REST routes for hosts with plain permalink configuration.

The hosting access logs show that pretty /wp-json/... routes return 404.
Use WordPress's supported ?rest_route=... form on the fixed HTTPS site.
Do not import this module from the Salesforce delivery pipeline.
"""
from urllib.parse import urlsplit, parse_qs

HOST = "https://jobs.zarafytek.com"
AUTH_IDENTITY_URL = HOST + "/?rest_route=/wp/v2/users/me&context=edit"
BA_SNAPSHOT_URL = HOST + "/?rest_route=/business-analysis-tracker/v1/snapshot"
BA_PAGE_EDIT_URL = HOST + "/?rest_route=/wp/v2/pages/49&context=edit"
BA_PAGE_UPDATE_URL = HOST + "/?rest_route=/wp/v2/pages/49"


def verify_ba_rest_endpoint(url: str, route: str) -> bool:
    """Only accept exact BA-auth/receiver query routes on the approved site."""
    parsed = urlsplit(url)
    expected = {
        "/wp/v2/users/me": AUTH_IDENTITY_URL,
        "/business-analysis-tracker/v1/snapshot": BA_SNAPSHOT_URL,
        "/wp/v2/pages/49?context=edit": BA_PAGE_EDIT_URL,
        "/wp/v2/pages/49": BA_PAGE_UPDATE_URL,
    }.get(route)
    return bool(expected and url == expected and parsed.scheme == "https"
                and parsed.hostname == "jobs.zarafytek.com"
                and parsed.path == "/" and parsed.username is None and parsed.password is None)
