"""Verify isolated Business Analysis historical pilot builder, with zero paid calls."""
import json
import unittest
from pathlib import Path
from scripts.build_ba_tracker_existing_pilot import build

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "candidate-beta" / "data" / "pilot-snapshot.json"


class TestBusinessAnalysisExistingPilot(unittest.TestCase):
    def test_build_keeps_exact_family_framework_without_fake_freshness(self):
        result = build(json.loads(PILOT.read_text(encoding="utf-8")))
        self.assertEqual(result["source_record_count"], 30)
        self.assertEqual(result["retained_record_count"], 25)
        self.assertEqual(len(result["job_families"]), 22)
        self.assertEqual(result["umbrella_filter"]["name"], "Information Security / Cyber Security")
        self.assertFalse(result["publication_approved"])
        self.assertFalse(result["live_refresh_enabled"])
        self.assertEqual(result["new_paid_apify_runs"], 0)
        self.assertEqual(result["excluded"]["outside_taxonomy_or_needs_context"], 5)
        self.assertTrue(all(row["url"].startswith("https://") for row in result["records"]))
        self.assertTrue(all(row["posted_date"] is None for row in result["records"]))
        self.assertTrue(all(row["source_observed_only"] for row in result["records"]))

    def test_source_only_guard(self):
        pilot = json.loads(PILOT.read_text(encoding="utf-8"))
        pilot["publication_approved"] = True
        with self.assertRaises(ValueError):
            build(pilot)


if __name__ == "__main__":
    unittest.main()
