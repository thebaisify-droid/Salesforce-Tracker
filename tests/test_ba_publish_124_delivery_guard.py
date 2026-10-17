"""No-network authorization, content and expiry tests for reviewed BA delivery."""
from __future__ import annotations
import unittest
from datetime import datetime,timezone,timedelta
from scripts.ba_publish_reviewed_124_once import (
    gate,FINISHED_AT,EXPECTED_BRANCH,EXACT_COMMIT_MESSAGE,
)
from scripts.ba_20261016_124_scope_preflight import candidate
from scripts.ba_atomic_snapshot_sender import envelope

class BAOneTimeReviewedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.env={
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_REF":EXPECTED_BRANCH,
            "GITHUB_RUN_ATTEMPT":"1",
            "BA_TRIGGER_MESSAGE":EXACT_COMMIT_MESSAGE,
            "BA_WP_DELIVERY_APPROVAL":"EXPLICIT_APPROVAL"
        }
        self.finished=datetime.fromisoformat(FINISHED_AT.replace("Z","+00:00"))

    def test_push_gate_valid_only_in_fresh_window(self):
        self.assertEqual(gate(self.finished+timedelta(hours=6),self.env)["mode"],"ONE_TIME_DELIVERY")
        for now in (self.finished-timedelta(minutes=1),
                    self.finished+timedelta(hours=35,minutes=30),
                    self.finished+timedelta(days=2)):
            with self.assertRaises(RuntimeError):
                gate(now,self.env)

    def test_push_gate_refuses_manual_untrusted_reruns_and_actor_credentials(self):
        for key,bad in (
            ("GITHUB_EVENT_NAME","workflow_dispatch"),
            ("GITHUB_REF","refs/heads/main"),
            ("GITHUB_RUN_ATTEMPT","2"),
            ("BA_TRIGGER_MESSAGE","other"),
            ("BA_WP_DELIVERY_APPROVAL",""),
            ("APIFY_TOKEN","do-not-use")
        ):
            env=dict(self.env,key=bad)
            env[key]=bad
            with self.subTest(key=key),self.assertRaises(RuntimeError):
                gate(self.finished+timedelta(hours=3),env)

    def test_exact_124_record_live_snapshot_package(self):
        report,live=candidate(return_snapshot=True)
        self.assertEqual(report["combined_in_scope"],124)
        self.assertTrue(report["live_payload_schema_preflight_passed"])
        self.assertEqual(len(live["records"]),124)
        self.assertEqual(live["schema"],"ba-live-snapshot/v1")
        self.assertTrue(live["quality"]["passed"])
        self.assertEqual(
            datetime.fromisoformat(live["refresh"]["finished_at"].replace("Z","+00:00")),
            self.finished,
        )
        self.assertEqual(len({r["id"] for r in live["records"]}),124)
        self.assertEqual(len(live["sources"]),5)
        self.assertEqual(len(envelope(live)["sha256"]),64)
        self.assertTrue(all(r["original_advert_url"].startswith("https://")
                            and r["source_observed_only"] for r in live["records"]))

if __name__=="__main__":
    unittest.main()
