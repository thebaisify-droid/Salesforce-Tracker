import pathlib
import unittest
from scripts.verify_controlled_handoff import validate_handoff


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.snap = {"run_id": "run-new", "refresh": {"status": "success"}}
        self.status = {"run_id": "run-new", "status": "success",
                       "summary": {"quality_passed": True}}

    def test_valid_current_success(self):
        self.assertTrue(validate_handoff(self.snap, self.status, self.status)["ready_for_single_delivery"])

    def test_skipped_attempt_does_not_resend_old_success(self):
        skip = {"run_id": "run-skip", "status": "skipped"}
        with self.assertRaises(ValueError):
            validate_handoff(self.snap, skip, self.status)

    def test_mismatched_snapshot_run_id(self):
        with self.assertRaises(ValueError):
            validate_handoff({"run_id": "old", "refresh": {"status": "success"}},
                             self.status, self.status)

    def test_failed_or_unqualified_attempt(self):
        for change in ({"status": "failed"}, {"summary": {"quality_passed": False}}):
            bad = dict(self.status, **change)
            with self.assertRaises(ValueError):
                validate_handoff(self.snap, bad, bad)

    def test_delivery_is_independently_disabled(self):
        s = pathlib.Path(".github/workflows/salesforce-controlled-refresh.yml").read_text()
        self.assertIn("vars.SF_WORDPRESS_DELIVERY_ENABLED == 'true'", s)
        self.assertIn("verify_controlled_handoff", s)
        self.assertIn("send_salesforce_wordpress_snapshot_once", s)
        self.assertIn("vars.SF_CONTROLLED_REFRESH_ENABLED == 'true'", s)
        self.assertNotIn("git push", s)
