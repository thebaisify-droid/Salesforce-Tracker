import tempfile
import unittest
from pathlib import Path
from tracker.candidate_store import CandidateStore

class CandidateStoreTests(unittest.TestCase):
    def test_idempotent_ingest_history_and_track_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "candidate.db"
            with CandidateStore(path) as db:
                first = db.ingest([
                    {"title": "Data Analyst", "url": "https://jobs.test/1?utm_source=test", "source": "Reed"},
                    {"title": "SOC Analyst", "url": "https://jobs.test/2", "source": "CV Library"},
                ], "batch-1", at="2026-10-08T12:00:00Z")
                self.assertEqual(first["inserted"], 2)
                next_run = db.ingest([
                    {"title": "Data Analyst", "url": "https://jobs.test/1", "source": "Totaljobs"},
                    {"title": "Security Guard", "url": "https://jobs.test/3"},
                ], "batch-2", at="2026-10-09T12:00:00Z")
                self.assertEqual(next_run, {"inserted": 0, "updated": 1, "rejected": 1})
                snapshot = db.snapshot()
                self.assertEqual(snapshot["total_vacancies"], 2)
                self.assertEqual([x["value"] for x in snapshot["by_track"]], [1, 1])
                job = next(x for x in snapshot["vacancies"] if x["title"] == "Data Analyst")
                self.assertEqual(job["sources"], ["Reed", "Totaljobs"])
                self.assertEqual(job["first_seen_at"], "2026-10-08T12:00:00Z")
                self.assertEqual(job["last_seen_at"], "2026-10-09T12:00:00Z")
                self.assertFalse(snapshot["publication_approved"])
                self.assertFalse(snapshot["acquisition_enabled"])

    def test_duplicate_batch_is_rejected_without_partial_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            with CandidateStore(Path(folder) / "candidate.db") as db:
                rows = [{"title": "IT Security Analyst", "url": "https://jobs.test/a"}]
                db.ingest(rows, "same")
                with self.assertRaises(ValueError):
                    db.ingest(rows, "same")
                self.assertEqual(db.snapshot()["total_vacancies"], 1)

    def test_protect_salesforce_database_name(self):
        with self.assertRaises(ValueError):
            CandidateStore("data/salesforce_tracker.db")

if __name__ == "__main__":
    unittest.main()
