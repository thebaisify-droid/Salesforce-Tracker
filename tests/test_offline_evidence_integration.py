"""Offline integration of export -> review sample -> human labels -> assurance -> stage."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_candidate_exports import load_export
from scripts.prepare_candidate_review import prepare, FIELDS
from scripts.evaluate_candidate_reviews import load_reviewed_csv, evaluate_reviewed
from tracker.candidate_store import CandidateStore


class OfflineEvidenceIntegrationTests(unittest.TestCase):
    def test_round_trip_preserves_source_evidence_and_never_publishes(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            export = folder / "previously_exported.json"
            export.write_text(json.dumps({"items": [
                {"jobTitle": "Information Security Analyst", "jobUrl": "https://example.org/jobs/1",
                 "companyName": "Test Employer", "descriptionText": "ISO 27001"},
                {"jobTitle": "Data Analyst", "jobUrl": "https://example.org/jobs/2",
                 "companyName": "Test Employer", "descriptionText": "SQL"},
                {"jobTitle": "Security Guard", "jobUrl": "https://example.org/jobs/3"}
            ]}), encoding="utf-8")
            records = load_export(export, "Reed")
            self.assertEqual(records[0]["company"], "Test Employer")
            queue = prepare(records, max_per_stratum=10)
            self.assertEqual(len(queue), 3)
            self.assertEqual(sum(r["predicted_included"] for r in queue), 2)
            self.assertTrue(all(r["expected_included"] == "" for r in queue))
            for row in queue:
                row["expected_included"] = "false" if row["title"] == "Security Guard" else "true"
                row["expected_family"] = {
                    "Information Security Analyst": "Information Security Analysis",
                    "Data Analyst": "Data Analysis",
                    "Security Guard": ""
                }[row["title"]]
                row["reviewer"] = "fixture-reviewer"
                row["reviewed_at"] = "2026-10-08"
            reviewed_file = folder / "labelled.csv"
            with reviewed_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(queue)
            reviewed = load_reviewed_csv(reviewed_file)
            result = evaluate_reviewed(reviewed, minimum_samples=100)
            self.assertEqual(result["sample_size"], 3)
            self.assertFalse(result["passed"])
            self.assertFalse(result["publication_approved"])
            self.assertFalse(result["real_world_accuracy_validated"])
            with CandidateStore(folder / "candidate.db") as store:
                stats = store.ingest(records, "offline-e2e-test")
                snapshot = store.snapshot()
            self.assertEqual(stats["inserted"], 2)
            self.assertEqual(snapshot["total_vacancies"], 2)
            self.assertFalse(snapshot["publication_approved"])
            self.assertEqual({v["advertiser"] for v in snapshot["vacancies"]}, {"Test Employer"})

    def test_cannot_bypass_evidence_by_labelling_everything_positive(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "bad_review.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerow({
                    "sample_id": "review1", "source": "Reed",
                    "job_url": "https://example.org/jobs/1", "title": "Data Analyst",
                    "description_excerpt": "", "expected_included": "true",
                    "expected_family": "", "reviewer": "reviewer", "reviewed_at": "2026-10-08"
                })
            with self.assertRaises(ValueError):
                load_reviewed_csv(path)


if __name__ == "__main__":
    unittest.main()
