"""Phase 3 no-spend integration tests, all source/API responses simulated."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest

from scripts.shared_checkpoint_selector import NAME, WORKFLOW_PATH, choose
from scripts.shared_completed_run_intake import intake_existing, raw_quality
from scripts.shared_acquisition_ledger import SharedLedger
from scripts.shared_acquisition_handoff import dual_readonly_handoff
from scripts.shared_dual_shadow import audit_dual
from scripts.shared_ledger_archive import make_archive, restore_archive
from scripts.ba_e2e_offline import run_offline
from scripts.ba_stage_five_source_data import MAPPING


class JointPhaseThreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = SharedLedger(Path(self.tmp.name) / "state" / "ledger.json")
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.request = {
            "provider": "apify_actor", "identifier": "wildorigins/indeed-jobs",
            "actor_input": {"query": "Salesforce", "country": "uk", "maxResults": 2},
            "window": {"since": (self.now - timedelta(hours=5)).isoformat(),
                       "until": (self.now - timedelta(minutes=3)).isoformat()},
        }
        self.rows = [
            {"title": "Salesforce Business Analyst",
             "url": "https://uk.indeed.com/viewjob?jk=offlinetest1",
             "company": "Example Consultancy", "description": "Configure Salesforce Sales Cloud"},
            {"title": "Data Analyst", "url": "https://uk.indeed.com/viewjob?jk=offlinetest2",
             "company": "Example Company", "description": "SQL and analytics"},
        ]
        self.run = {
            "status": "SUCCEEDED", "actId": "BkcKc9frZp43LeRM7",
            "defaultDatasetId": "Dataset12345", "defaultKeyValueStoreId": "Store123456",
            "finishedAt": (self.now - timedelta(minutes=2)).isoformat(),
        }

    def getter(self, route):
        if route == "actor-runs/Run_123456":
            return dict(self.run)
        if route == "key-value-stores/Store123456/records/INPUT":
            return dict(self.request["actor_input"])
        if route == "datasets/Dataset12345":
            return {"itemCount": 2}
        if route == "datasets/Dataset12345/items?clean=false&offset=0&limit=2":
            return list(self.rows)
        raise AssertionError("Unexpected endpoint, possible paid call: " + route)

    def intake(self, getter=None, **kwargs):
        return intake_existing(self.request, ledger=self.ledger,
            run_id="Run_123456", actor_id="BkcKc9frZp43LeRM7",
            maximum_items=2, getter=getter or self.getter,
            source_quality=raw_quality, **kwargs)

    def test_verified_existing_run_archive_restore_and_independent_classifiers(self):
        answer = self.intake()
        self.assertEqual(answer["actors_started"], 0)
        self.assertEqual(answer["wordpress_requests"], 0)
        self.assertEqual(len(self.ledger.read()), 1)
        handoff = dual_readonly_handoff(self.request, ledger=self.ledger,
            getter=self.getter, now=self.now)
        sf = audit_dual(handoff["salesforce_raw_records"])
        ba = audit_dual(handoff["ba_raw_records"])
        self.assertEqual(sf["salesforce_relevant"], 1)
        self.assertEqual(ba["ba_relevant"], 2)
        self.assertEqual(ba["cross_scope"], 1)
        self.assertEqual(ba["ba_role_family_count_configured"], 22)
        self.assertFalse(sf["coverage_approved"])
        self.assertFalse(ba["publication_approved"])
        handoff["salesforce_raw_records"][0]["title"] = "Changed"
        self.assertEqual(handoff["ba_raw_records"][0]["title"], "Salesforce Business Analyst")
        archive = Path(self.tmp.name) / "checkpoint.zip"
        make_archive(self.ledger, archive)
        restored = SharedLedger(Path(self.tmp.name) / "recovered" / "ledger.json")
        self.assertEqual(restore_archive(archive, restored)["receipts"], 1)
        self.assertEqual(restored.find(self.request, now=self.now)["run_id"], "Run_123456")

    def test_reject_wrong_actor_input_or_status_or_oversized_dataset(self):
        for change in ({"status": "FAILED"}, {"actId": "WrongActor"},
                       {"defaultDatasetId": None}, {"defaultKeyValueStoreId": None}):
            with self.subTest(change=change):
                def bad(route):
                    result = self.getter(route)
                    return {**result, **change} if route.startswith("actor-runs/") else result
                with self.assertRaises(ValueError):
                    self.intake(getter=bad)
        wrong_query = {**self.request, "actor_input":
                       {**self.request["actor_input"], "query": "business analyst"}}
        with self.assertRaisesRegex(ValueError, "effective input"):
            intake_existing(wrong_query, ledger=self.ledger, run_id="Run_123456",
                actor_id="BkcKc9frZp43LeRM7", maximum_items=2,
                getter=self.getter, source_quality=raw_quality)
        with self.assertRaises(ValueError):
            intake_existing(self.request, ledger=self.ledger, run_id="Run_123456",
                actor_id="BkcKc9frZp43LeRM7", maximum_items=1,
                getter=self.getter, source_quality=raw_quality)
        with self.assertRaises(ValueError):
            intake_existing(self.request, ledger=self.ledger, run_id="Run_123456",
                actor_id="BkcKc9frZp43LeRM7", maximum_items=2,
                getter=self.getter, source_quality=lambda rows: False)
        self.assertEqual(self.ledger.read(), [])

    def test_checkpoint_picks_only_latest_successful_expected_run(self):
        listing = {"total_count": 1, "artifacts": [{
            "id": 42, "name": NAME, "expired": False,
            "created_at": (self.now - timedelta(hours=1)).isoformat(),
            "workflow_run": {"id": 101, "head_branch": "feature/shared-acquisition-cost-guards-oct2026"},
        }]}
        def good(_):
            return {"id": 101, "status": "completed", "conclusion": "success",
                    "head_branch": "feature/shared-acquisition-cost-guards-oct2026",
                    "path": WORKFLOW_PATH}
        options = {"branch": "feature/shared-acquisition-cost-guards-oct2026",
                   "current_run_id": 500, "get_run": good, "now": self.now}
        self.assertEqual(choose(listing, **options)["run_id"], 101)
        with self.assertRaises(ValueError):
            choose(listing, **{**options, "get_run":
                               lambda _: {**good(None), "conclusion": "failure"}})
        listing["total_count"] = 2
        with self.assertRaises(ValueError):
            choose(listing, **options)
        listing["total_count"] = 1
        listing["artifacts"][0]["expired"] = True
        with self.assertRaises(ValueError):
            choose(listing, **options)
        self.assertFalse(choose({"total_count": 0, "artifacts": []},
                        **options)["found"])

    def test_salesforce_actual_incremental_sqlite_shadow_without_publication(self):
        """Run the existing production normalizer/upsert against an isolated DB."""
        from unittest.mock import patch
        from scripts.process_incremental import main as process_salesforce
        self.intake()
        handoff = dual_readonly_handoff(self.request, ledger=self.ledger,
            getter=self.getter, now=self.now)
        root = Path(self.tmp.name)
        raw = root / "shadow-run" / "raw"
        raw.mkdir(parents=True)
        (raw / "source_4.json").write_text(json.dumps(
            handoff["salesforce_raw_records"]), encoding="utf-8")
        db = root / "isolated-salesforce-shadow.db"
        metrics = root / "sf-shadow-metrics.json"
        args = ["sf-process-incremental", "--input-dir", str(raw),
                "--run-id", "shadow-salesforce-001", "--metrics", str(metrics),
                "--database", str(db)]
        with patch("sys.argv", args):
            self.assertEqual(process_salesforce(), 0)
        report = json.loads(metrics.read_text(encoding="utf-8"))
        self.assertEqual(report["inserted_rows"], 1)
        self.assertEqual(report["irrelevant_rows"], 1)
        self.assertEqual(report["rejected_rows"], 0)
        import sqlite3
        with sqlite3.connect(db) as conn:
            stored = conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
        self.assertEqual(stored, 1)
        self.assertFalse((root / "dashboard" / "live-data.json").exists())

    def test_existing_ba_five_board_classification_and_delivery_preview(self):
        boards = [
            ("CV-Library", {"title": "Business Analyst", "url": "https://www.cv-library.co.uk/job/test001",
                            "company": "Bupa", "postedAt": "2026-10-14", "location": "London"}),
            ("Totaljobs", {"title": "Product Owner", "jobUrl": "https://www.totaljobs.com/job/test002",
                           "employer": {"name": "Deloitte"}, "datePosted": "2026-10-14",
                           "location": "Leeds", "rowType": "job"}),
            ("Reed UK", {"title": "Business Analyst", "url": "https://www.reed.co.uk/jobs/test003",
                         "employer": "Falkirk Council", "datePosted": "2026-10-14", "location": "Scotland"}),
            ("Indeed UK", {"title": "Business Analyst", "url": "https://uk.indeed.com/viewjob?jk=synthetic04",
                           "company": "Capgemini", "postedAt": "2026-10-14", "location": "UK"}),
            ("JobServe", {"title": "Business Analyst", "url": "https://www.jobserve.com/gb/en/test005",
                          "company": "Dunelm", "postedDateTime": "2026-10-14", "location": "Manchester"}),
        ]
        batch = {"schema": "ba-five-source-completed-batch/v1", "sources": [
            {"name": src, "status": "SUCCEEDED", "attempted": True,
             "run_id": "offline-run-" + str(i), "dataset_id": "offline-data-" + str(i),
             "observed_at": "2026-10-15T15:00:00Z", "records": [job]}
            for i, (src, job) in enumerate(boards)
        ]}
        evidence = json.loads(MAPPING.read_text(encoding="utf-8"))
        result = run_offline(batch, evidence)
        self.assertEqual(result["status"], "DRY_RUN_PASS_NOT_PUBLISHED")
        self.assertEqual(result["matched"], 5)
        self.assertEqual(result["wordpress_requests"], 0)
        self.assertEqual(result["actors_started"], 0)
        self.assertFalse(result["package"]["delivery_approved"])


if __name__ == "__main__":
    unittest.main()
