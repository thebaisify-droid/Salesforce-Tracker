"""Offline safety tests for the candidate research beta release boundary.

These tests cannot certify vacancy accuracy or representative coverage.
"""
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "candidate-beta" / "data" / "pilot-snapshot.json"


class CandidateReleaseFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_preview_has_no_publication_authority(self):
        data = self.snapshot
        self.assertIs(data["sample_only"], True)
        self.assertIs(data["beta_display_only"], True)
        self.assertIs(data["publication_approved"], False)
        self.assertIs(data["verified_representative_coverage"], False)

    def test_historical_counts_are_consistent(self):
        data = self.snapshot
        records = data["records"]
        self.assertEqual(data["record_count"], len(records))
        self.assertEqual(len(records), 30)
        self.assertEqual(data["role_family_target"], 22)
        self.assertEqual(Counter(r["source"] for r in records),
                         {"Totaljobs": 10, "Indeed UK": 10, "JobServe": 10})

    def test_no_sample_record_can_be_published(self):
        records = self.snapshot["records"]
        self.assertEqual(len({r["id"] for r in records}), len(records))
        self.assertTrue(all(r["title"].strip() and r["url"].startswith("https://")
                            for r in records))
        self.assertTrue(all(r["verification"] in {"SOURCE_ONLY_UNVERIFIED", "PAGE_VIEWED_NOT_VERIFIED"}
                            for r in records))
        self.assertTrue(all(r["publication_ready"] is False for r in records))

    def test_preview_only_reads_isolated_snapshot(self):
        html = (ROOT / "candidate-beta" / "index.html").read_text(encoding="utf-8")
        self.assertIn("pilot-snapshot.json", html)
        self.assertNotIn("dashboard/live-data.json", html)
        self.assertIn("Publication-verified vacancies", html)


if __name__ == "__main__":
    unittest.main()
