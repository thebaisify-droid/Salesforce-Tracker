"""Offline tests: durable GitHub slot creation is single-winner and fail-closed."""
import unittest
from scripts.ba_slot_claim import claim_slot

SLOT = "2026-10-20T07:35:00+01:00"
ARGS = {"token": "offline-test", "repository": "example/tracker", "sha": "a" * 40}

class TestSlotClaim(unittest.TestCase):
    def test_first_claim_wins(self):
        calls = []
        def post(url, body):
            calls.append(body)
            return 201 if len(calls) == 1 else 422
        first = claim_slot(SLOT, **ARGS, post=post)
        second = claim_slot(SLOT, **ARGS, post=post)
        self.assertTrue(first["claimed"])
        self.assertFalse(second["claimed"])
        self.assertEqual(first["ref"], "refs/heads/ba-acquisition-slot-20261020")

    def test_conflicts_and_provider_errors_fail_closed(self):
        for code in (409, 422):
            self.assertFalse(claim_slot(SLOT, **ARGS, post=lambda *_: code)["claimed"])
        with self.assertRaises(RuntimeError):
            claim_slot(SLOT, **ARGS, post=lambda *_: 500)

    def test_reject_unapproved_slot_and_missing_credentials(self):
        for slot in ("2026-10-19T07:35:00+01:00", "2026-10-20T09:35:00+01:00"):
            with self.assertRaises(ValueError):
                claim_slot(slot, **ARGS, post=lambda *_: 201)
        with self.assertRaises(ValueError):
            claim_slot(SLOT, token="", repository="example/tracker", sha="a"*40,
                       post=lambda *_: 201)

if __name__ == "__main__":
    unittest.main()
