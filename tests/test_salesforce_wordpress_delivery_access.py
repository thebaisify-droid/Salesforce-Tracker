"""Offline checks for the read-only WordPress delivery gate."""
from __future__ import annotations
import base64
import io
import json
import unittest

from scripts.check_salesforce_wordpress_delivery_access import (
    NoRedirect, EXPECTED_USER, verify_access,
)


class TestDeliveryPreflight(unittest.TestCase):
    class FakeTransport:
        def __init__(self, user):
            self.user = user
            self.calls = 0
        def open(self, request, timeout):
            self.calls += 1
            assert request.get_method() == "GET"
            assert request.full_url.startswith("https://jobs.zarafytek.com/wp-json/wp/v2/users/me")
            decoded = base64.b64decode(request.get_header("Authorization").split(" ", 1)[1]).decode()
            assert decoded == EXPECTED_USER + ":dummy-password"
            return io.BytesIO(json.dumps(self.user).encode())

    def test_valid_dedicated_identity(self):
        transport = self.FakeTransport({"username": EXPECTED_USER,
            "capabilities": {"read": True, "sf_deliver_snapshot": True}})
        result = verify_access(EXPECTED_USER, "dummy-password", opener=transport)
        self.assertTrue(result["delivery_identity_verified"])
        self.assertEqual(transport.calls, 1)
        self.assertFalse(result["snapshot_sent"])

    def test_missing_credentials_dont_attempt_network(self):
        with self.assertRaises(ValueError):
            verify_access(EXPECTED_USER, "")
        with self.assertRaises(ValueError):
            verify_access("administrator", "dummy-password")

    def test_wrong_permissions_fail_closed(self):
        for user in (
            {"username": EXPECTED_USER, "capabilities": {"read": True}},
            {"username": "administrator", "capabilities": {"sf_deliver_snapshot": True}},
            {"username": EXPECTED_USER, "capabilities": {}},
            [],
        ):
            with self.assertRaises(ValueError):
                verify_access(EXPECTED_USER, "dummy-password", opener=self.FakeTransport(user))

    def test_redirect_is_forbidden(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://example.com")


if __name__ == "__main__":
    unittest.main()
