import io
import json
import unittest
from datetime import datetime, timezone
from scripts.send_salesforce_wordpress_snapshot_once import (
    build_envelope, publish_once, verify_destination, NoRedirect,
)
from scripts.validate_salesforce_wordpress_delivery import inspect


class SenderTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.dumps({
            "schema": "salesforce-hiring-dashboard/v1",
            "pipeline": {"quality_passed": True},
            "active_vacancies": 1,
            "vacancies": [{"title": "Salesforce Developer"}],
            "refresh": {"status": "success", "finished_at": "2026-10-14T11:00:00Z"},
        }).encode()

    def test_payload_and_target(self):
        report = inspect(self.snapshot, now=datetime(2026,10,14,12,tzinfo=timezone.utc))
        envelope = build_envelope(self.snapshot)
        self.assertEqual(envelope["sha256"], report["sha256"])
        verify_destination("https://jobs.zarafytek.com")
        for bad in ("http://jobs.zarafytek.com", "https://example.com",
                    "https://jobs.zarafytek.com.evil.test",
                    "https://jobs.zarafytek.com@other.test"):
            with self.assertRaises(ValueError):
                verify_destination(bad)

    def test_sender_rejects_empty_credentials_without_network(self):
        with self.assertRaises(ValueError):
            publish_once(self.snapshot, "", "", opener=None)

    def test_one_request_and_verified_ack(self):
        class FakeOpener:
            def __init__(self): self.calls = 0
            def open(self, request, timeout):
                self.calls += 1
                received = json.loads(request.data)
                self.payload = received
                return io.BytesIO(json.dumps({"accepted": True,
                                              "sha256": received["sha256"]}).encode())
        opener=FakeOpener()
        result=publish_once(self.snapshot,"test-user","test-password",opener=opener)
        self.assertTrue(result["checksum_verified"])
        self.assertEqual(opener.calls,1)
        self.assertEqual(opener.payload["snapshot"],self.snapshot.decode())

    def test_bad_receiver_digest_fails_closed(self):
        class BadOpener:
            def open(self,request,timeout):
                return io.BytesIO(b'{"accepted":true,"sha256":"no"}')
        with self.assertRaises(ValueError):
            publish_once(self.snapshot,"name","secret",opener=BadOpener())

    def test_redirect_is_forbidden(self):
        with self.assertRaises(ValueError):
            NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://evil.test")
