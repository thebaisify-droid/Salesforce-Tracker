"""No network, Actor starts, scheduled GitHub jobs or WordPress writes."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from scripts.shared_dataset_reuse import fingerprint
from scripts.shared_acquisition_ledger import SharedLedger, record_verified
from scripts.shared_ledger_archive import make_archive, restore_archive
from scripts.shared_acquisition_schedule import due_slot, SUMMER, WINTER
from scripts.shared_acquisition_handoff import dual_readonly_handoff, summarise


class JointNextStageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = SharedLedger(self.root / "a" / "ledger.json")
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.req = {"provider": "apify_actor", "identifier": "wildorigins/indeed-jobs",
                    "actor_input": {"query": "Salesforce", "country": "uk", "maxResults": 2},
                    "window": {"since": (self.now - timedelta(hours=12)).isoformat(),
                               "until": self.now.isoformat()}}
        self.rows = [{"title": "Salesforce BA"}, {"title": "Business Analyst"}]
        self.metadata = {
            "identifier": self.req["identifier"], "provider": "apify_actor",
            "verified_request_sha256": fingerprint(**self.req),
            "status": "SUCCEEDED", "dataset_verified": True, "qa_passed": True,
            "run_id": "Run_123456", "dataset_id": "Data_123456",
            "apify_actor_id": "Actor_123456", "dataset_items": 2,
            "approved_max_items": 2, "completed_at": self.now.isoformat(),
        }

    def test_integrity_archive_restores_into_empty_durable_ledger(self):
        self.a.append(record_verified(self.req, self.metadata, self.rows))
        path = self.root / "transfer.zip"
        manifest = make_archive(self.a, path)
        self.assertEqual(manifest["receipts"], 1)
        self.assertFalse(manifest["contains_raw_adverts"])
        b = SharedLedger(self.root / "b" / "ledger.json")
        result = restore_archive(path, b)
        self.assertEqual(result["receipts"], 1)
        self.assertEqual(b.find(self.req, now=self.now)["run_id"], "Run_123456")
        with self.assertRaises(ValueError):
            restore_archive(path, b)

    def test_tampered_checksum_and_extra_member_rejected(self):
        self.a.append(record_verified(self.req, self.metadata, self.rows))
        path = self.root / "good.zip"
        make_archive(self.a, path)
        import zipfile
        with zipfile.ZipFile(path, "r") as archive:
            contents = {name: archive.read(name) for name in archive.namelist()}
        manifest = json.loads(contents["state/shared_acquisition_manifest.json"])
        manifest["ledger_sha256"] = "0" * 64
        contents["state/shared_acquisition_manifest.json"] = json.dumps(manifest).encode()
        broken = self.root / "broken.zip"
        with zipfile.ZipFile(broken, "w") as archive:
            for name, blob in contents.items():
                archive.writestr(name, blob)
        with self.assertRaises(ValueError):
            restore_archive(broken, SharedLedger(self.root / "target" / "ledger.json"))
        with zipfile.ZipFile(broken, "a") as archive:
            archive.writestr("../../outside.txt", "injection")
        with self.assertRaises(ValueError):
            restore_archive(broken, SharedLedger(self.root / "target" / "ledger.json"))

    def test_two_distinct_independently_classifiable_raw_copies(self):
        receipt = record_verified(self.req, self.metadata, self.rows)
        self.a.append(receipt)
        def getter(endpoint):
            if endpoint.startswith("actor-runs/"):
                return {"status": "SUCCEEDED", "defaultDatasetId": "Data_123456",
                        "actId": "Actor_123456", "finishedAt": receipt["completed_at"]}
            if "/items?" in endpoint:
                return self.rows
            return {"itemCount": 2}
        handoff = dual_readonly_handoff(self.req, ledger=self.a,
                                      getter=getter, now=self.now)
        self.assertEqual(handoff["status"], "TWO_INDEPENDENT_UNCLASSIFIED_INPUTS_NOT_PUBLISHED")
        self.assertEqual(handoff["actors_started"], 0)
        self.assertFalse(handoff["consumer_quality_passed"])
        handoff["salesforce_raw_records"][0]["title"] = "modified"
        self.assertEqual(handoff["ba_raw_records"][0]["title"], "Salesforce BA")
        self.assertNotIn("ba_raw_records", summarise(handoff))
        self.assertNotIn("salesforce_raw_records", summarise(handoff))

    def test_summer_winter_dst_and_wrong_cron(self):
        s = due_slot(datetime(2026, 10, 23, 6, 35, tzinfo=timezone.utc), cron=SUMMER)
        w = due_slot(datetime(2026, 11, 6, 7, 35, tzinfo=timezone.utc), cron=WINTER)
        self.assertTrue(s["due"])
        self.assertTrue(w["due"])
        self.assertEqual(s["local_time"], "2026-10-23T07:15:00+01:00")
        self.assertEqual(w["local_time"], "2026-11-06T07:15:00+00:00")
        self.assertFalse(due_slot(datetime(2026, 10, 23, 7, 35,
                                           tzinfo=timezone.utc), cron=WINTER)["due"])
        self.assertFalse(due_slot(datetime(2026, 11, 6, 7, 35,
                                           tzinfo=timezone.utc), cron=WINTER, attempt=2)["due"])
        self.assertFalse(due_slot(datetime(2026, 10, 24, 6, 30,
                                           tzinfo=timezone.utc), cron=SUMMER)["due"])
        self.assertFalse(due_slot(datetime(2026, 10, 23, 9, 20,
                                           tzinfo=timezone.utc), cron=SUMMER)["due"])


if __name__ == "__main__":
    unittest.main()
