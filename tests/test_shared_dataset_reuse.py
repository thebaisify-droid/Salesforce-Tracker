"""All tests are offline: no tokens, Apify Actor starts or WordPress posts."""
import unittest
from datetime import datetime, timedelta, timezone
from scripts.shared_dataset_reuse import fingerprint, reusable_receipt, configured_overlap


class SharedAcquisitionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
        self.params = dict(
            provider="apify_actor",
            identifier="wildorigins/indeed-jobs",
            actor_input={"query": "Salesforce", "country": "uk", "maxResults": 30},
            window={"since": "2026-10-19T00:00:00Z", "until": "2026-10-20T00:00:00Z"},
        )
        self.request_hash = fingerprint(**self.params)
        self.receipt = {
            "request_sha256": self.request_hash,
            "status": "SUCCEEDED",
            "dataset_verified": True,
            "qa_passed": True,
            "run_id": "example_actor_run",
            "dataset_id": "example_dataset",
            "dataset_sha256": "a" * 64,
            "dataset_items": 20,
            "completed_at": (self.now - timedelta(hours=1)).isoformat(),
        }

    def test_identical_input_is_canonical(self):
        copy = {**self.params, "actor_input":
                {"maxResults": 30, "country": "uk", "query": "Salesforce"}}
        self.assertEqual(self.request_hash, fingerprint(**copy))

    def test_different_search_or_result_limit_not_reusable(self):
        for overrides in ({"query": "business analyst"}, {"maxResults": 60},
                          {"country": "us"}):
            actor_input = {**self.params["actor_input"], **overrides}
            self.assertNotEqual(self.request_hash,
                                fingerprint(**{**self.params, "actor_input": actor_input}))
        self.assertNotEqual(self.request_hash, fingerprint(**{
            **self.params, "window": {**self.params["window"], "since": "2026-10-18T00:00:00Z"}}))
        self.assertNotEqual(self.request_hash, fingerprint(**{
            **self.params, "provider": "apify_task", "identifier": "saved_task"}))

    def test_verified_recent_completed_dataset_can_be_reused(self):
        self.assertTrue(reusable_receipt(self.request_hash, self.receipt, now=self.now))

    def test_fails_closed_on_missing_qa_metadata_or_wrong_input(self):
        variants = [
            {"qa_passed": False}, {"dataset_verified": False}, {"status": "FAILED"},
            {"request_sha256": "0" * 64}, {"dataset_items": 0},
            {"dataset_items": True}, {"dataset_sha256": ""}, {"run_id": ""},
            {"completed_at": "not-a-timestamp"}, {"completed_at":
                (self.now - timedelta(hours=25)).isoformat()},
            {"completed_at": (self.now + timedelta(minutes=5)).isoformat()},
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertFalse(reusable_receipt(
                    self.request_hash, {**self.receipt, **variant}, now=self.now))

    def test_current_sf_ba_queries_cannot_be_claimed_as_shared(self):
        audit = configured_overlap()
        self.assertEqual(audit["status"], "READ_ONLY_NO_ACTORS_LAUNCHED")
        self.assertEqual(audit["current_exact_input_matches"], [])
        self.assertEqual(audit["current_verified_cost_saving_usd"], 0)
        self.assertTrue(any(r["ba_source"] == "Indeed UK" for r in audit["same_actor_non_reusable"]))
        self.assertTrue(any(r["ba_source"] == "JobServe" for r in audit["same_actor_non_reusable"]))


if __name__ == "__main__":
    unittest.main()
