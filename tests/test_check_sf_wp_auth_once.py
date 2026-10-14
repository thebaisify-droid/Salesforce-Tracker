import io
import unittest
from urllib.error import HTTPError
from scripts.check_sf_wp_auth_once import check

class FakeOpener:
    def __init__(self, code, name):
        self.calls = 0
        self.code, self.name = code, name
    def open(self, request, timeout):
        self.calls += 1
        assert request.data == b"{}"
        raise HTTPError(request.full_url, self.code, "response", {},
                        io.BytesIO(('{ "code": "'+self.name+'" }').encode()))

class AuthProbeTests(unittest.TestCase):
    def test_expected_validation_error_proves_receiver_authorised(self):
        fake = FakeOpener(400, "sf_bad_envelope")
        result = check("sf_snapshot_delivery", "dummy-not-real", opener=fake)
        self.assertTrue(result["authenticated"])
        self.assertFalse(result["snapshot_uploaded"])
        self.assertEqual(fake.calls, 1)
    def test_denied_permission_fails_closed(self):
        fake = FakeOpener(403, "rest_forbidden")
        with self.assertRaisesRegex(RuntimeError, "HTTP 403; code rest_forbidden"):
            check("sf_snapshot_delivery", "dummy", opener=fake)
        self.assertEqual(fake.calls, 1)
    def test_wrong_response_fails_closed(self):
        with self.assertRaises(RuntimeError):
            check("sf_snapshot_delivery", "dummy", opener=FakeOpener(400,"other"))
    def test_missing_credentials_fails_before_network(self):
        with self.assertRaises(ValueError):
            check("sf_snapshot_delivery","")

    def test_unknown_error_is_redacted(self):
        fake = FakeOpener(401, "unexpected-secret-content")
        with self.assertRaisesRegex(RuntimeError, "HTTP 401; code other") as caught:
            check("sf_snapshot_delivery", "dummy", opener=fake)
        self.assertNotIn("unexpected-secret-content", str(caught.exception))
