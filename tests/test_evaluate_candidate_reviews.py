import csv
import tempfile
import unittest
from pathlib import Path
from scripts.evaluate_candidate_reviews import load_reviewed_csv, evaluate_reviewed

class ReviewedMarketAssuranceTests(unittest.TestCase):
    def test_successful_small_review_is_not_production_validated(self):
        rows=[{"title":"SOC Analyst","expected_included":True,
               "expected_family":"Security Operations / SOC","source":"Reed"}]
        r=evaluate_reviewed(rows,minimum_samples=100)
        self.assertFalse(r["passed"])
        self.assertFalse(r["real_world_accuracy_validated"])
        self.assertFalse(r["publication_approved"])
        self.assertEqual(r["sources"]["Reed"],1)

    def test_review_evidence_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"review.csv"
            fields=["sample_id","source","job_url","title","description_excerpt",
                    "expected_included","expected_family","reviewer","reviewed_at"]
            with path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=fields)
                writer.writeheader()
                writer.writerow(dict(sample_id="a",source="Reed",job_url="https://example.org/job",
                                     title="SOC Analyst",description_excerpt="",
                                     expected_included="yes",expected_family="Security Operations / SOC",
                                     reviewer="",reviewed_at="2026-10-08"))
            with self.assertRaises(ValueError):
                load_reviewed_csv(path)

    def test_fully_reviewed_case(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"review.csv"
            fields=["sample_id","source","job_url","title","description_excerpt",
                    "expected_included","expected_family","reviewer","reviewed_at"]
            with path.open("w",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=fields)
                writer.writeheader()
                writer.writerow(dict(sample_id="a",source="Totaljobs",job_url="https://example.org/job",
                                     title="Data Analyst",description_excerpt="",
                                     expected_included="true",expected_family="Data Analysis",
                                     reviewer="reviewer-1",reviewed_at="2026-10-08"))
            records=load_reviewed_csv(path)
            self.assertEqual(len(records),1)
            self.assertTrue(evaluate_reviewed(records,minimum_samples=1)["reviewed_sample_thresholds_met"])
            self.assertFalse(evaluate_reviewed(records,minimum_samples=1)["real_world_accuracy_validated"])
            self.assertFalse(evaluate_reviewed(records,minimum_samples=1)["publication_approved"])

if __name__=="__main__":
    unittest.main()
