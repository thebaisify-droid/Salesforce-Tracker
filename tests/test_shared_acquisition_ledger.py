"""Offline integration tests; never start paid Actors or publish snapshots."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from scripts.shared_dataset_reuse import fingerprint
from scripts.shared_acquisition_ledger import (
    SharedLedger, record_verified, replay_verified, apify_get_only)
from scripts.shared_refresh_controller import audit


class SharedAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = SharedLedger(Path(self.temp.name) / "data" / "ledger.json")
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.request = {
            "provider": "apify_actor", "identifier": "wildorigins/indeed-jobs",
            "actor_input": {"query": "Salesforce", "country": "uk", "maxResults": 2},
            "window": {"since": (self.now - timedelta(hours=12)).isoformat(),
                       "until": self.now.isoformat()},
        }
        self.rows = [{"title": "Salesforce BA", "url": "https://example.com/job/1"},
                     {"title": "Business Analyst", "url": "https://example.com/job/2"}]
        self.metadata = {
            "identifier": "wildorigins/indeed-jobs", "provider": "apify_actor",
            "verified_request_sha256": fingerprint(**self.request),
            "status": "SUCCEEDED", "dataset_verified": True, "qa_passed": True,
            "run_id": "Run_123456", "dataset_id": "Data_123456",
            "apify_actor_id": "Actor_123456", "dataset_items": 2,
            "approved_max_items": 2, "completed_at": self.now.isoformat(),
        }

    def store(self):
        entry = record_verified(self.request, self.metadata, self.rows)
        self.assertTrue(self.ledger.append(entry))
        return entry

    def test_atomic_idempotent_and_only_metadata(self):
        entry = self.store()
        self.assertFalse(self.ledger.append(entry))
        self.assertEqual(len(self.ledger.read()), 1)
        self.assertNotIn("Salesforce BA", self.ledger.path.read_text())
        self.assertEqual(self.ledger.find(self.request, now=self.now), entry)

    def test_different_query_or_window_is_not_reusable(self):
        self.store()
        search = {**self.request, "actor_input":
                  {**self.request["actor_input"], "query": "business analyst"}}
        window = {**self.request, "window":
                  {**self.request["window"], "since": self.now.isoformat()}}
        self.assertIsNone(self.ledger.find(search, now=self.now))
        self.assertIsNone(self.ledger.find(window, now=self.now))
        self.assertIsNone(self.ledger.find(self.request, now=self.now + timedelta(hours=25)))

    def test_overshoot_wrong_identity_qa_and_secrets_rejected(self):
        for change in ({"dataset_items": 3}, {"approved_max_items": 1},
                       {"identifier": "wrong"}, {"qa_passed": False},
                       {"dataset_verified": False}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    record_verified(self.request, {**self.metadata, **change}, self.rows)
        with self.assertRaises(ValueError):
            record_verified({**self.request, "actor_input": {"apiToken": "secret"}},
                            self.metadata, self.rows)
        with self.assertRaises(ValueError):
            record_verified({**self.request, "provider": "apify_task"},
                            self.metadata, self.rows)

    def test_verified_dataset_replay_and_corruption_block(self):
        receipt = self.store()
        calls = []
        def get(endpoint):
            calls.append(endpoint)
            if endpoint.startswith("actor-runs/"):
                return {"status": "SUCCEEDED", "actId": receipt["apify_actor_id"],
                        "defaultDatasetId": receipt["dataset_id"],
                        "finishedAt": receipt["completed_at"]}
            if "/items?" in endpoint:
                return list(self.rows)
            return {"itemCount": 2}
        result = replay_verified(self.request, self.ledger, get, now=self.now)
        self.assertEqual(result["actors_started"], 0)
        self.assertEqual(result["rows"], self.rows)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(not x.startswith("acts/") for x in calls))
        def tampered(endpoint):
            return [{"title": "tampered"}, self.rows[1]] if "/items?" in endpoint else get(endpoint)
        with self.assertRaises(ValueError):
            replay_verified(self.request, self.ledger, tampered, now=self.now)

    def test_invalid_manifest_and_no_paid_endpoints(self):
        self.store()
        payload = json.loads(self.ledger.path.read_text())
        payload["receipts"][0]["qa_passed"] = False
        self.ledger.path.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            self.ledger.read()
        with self.assertRaises(ValueError):
            apify_get_only("acts/wildorigins~indeed-jobs/runs", "example")
        with self.assertRaises(ValueError):
            apify_get_only("actor-runs/Run_123456", "")

    def test_controller_budget_and_paused_publication(self):
        result = audit()
        self.assertEqual(result["status"], "READ_ONLY_NO_SPEND")
        self.assertEqual(result["account_cap_expected_usd"], 19)
        self.assertTrue(result["ba_paid_collection_paused"])
        self.assertEqual(result["validated_reuses"], [])
        self.assertEqual(result["measured_avoided_actor_cost_usd"], 0)
        self.assertFalse(result["live_activated"])


if __name__ == "__main__":
    unittest.main()
