"""Historical BA tracker source-only evidence and family checks; no paid calls."""
import json
import unittest
from pathlib import Path
from scripts.build_ba_tracker_existing_pilot import build

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "candidate-beta" / "data" / "pilot-snapshot.json"
CYBER = ROOT / "business-analysis-tracker" / "data" / "completed-cyber-pilots.json"


class TestBusinessAnalysisExistingPilot(unittest.TestCase):
    def setUp(self):
        self.pilot = json.loads(PILOT.read_text(encoding="utf-8"))
        self.cyber = json.loads(CYBER.read_text(encoding="utf-8"))

    def test_combined_historical_snapshot(self):
        result = build(self.pilot, self.cyber)
        self.assertEqual(result["source_record_count"], 65)
        self.assertEqual(result["retained_record_count"], 36)
        self.assertEqual(len(result["job_families"]), 22)
        self.assertEqual(result["umbrella_filter"]["name"], "Information Security / Cyber Security")
        self.assertFalse(result["publication_approved"])
        self.assertFalse(result["live_refresh_enabled"])
        self.assertEqual(result["new_paid_apify_runs"], 0)
        self.assertEqual(result["excluded"]["outside_taxonomy_or_needs_context"], 5)
        self.assertEqual(sum(result["by_family"].values()), 36)
        self.assertEqual(sum(result["by_source"].values()), 36)
        self.assertEqual(sum(row["track"] == "SECURITY" for row in result["records"]), 7)
        self.assertTrue(all(row["url"].startswith("https://") for row in result["records"]))
        self.assertTrue(all(row["source_observed_only"] for row in result["records"]))
        self.assertEqual(len({row["url"] for row in result["records"]}), 36)
        self.assertTrue(any(row["posted_date"] is None for row in result["records"]))
        self.assertTrue(any(row["posted_date"] for row in result["records"]))

    def test_fail_closed_if_pilot_claims_publication(self):
        self.pilot["publication_approved"] = True
        with self.assertRaises(ValueError):
            build(self.pilot, self.cyber)

    def test_fail_closed_on_cyber_data_without_source_only_flag(self):
        self.cyber["records"][0]["source_observed_only"] = False
        with self.assertRaises(ValueError):
            build(self.pilot, self.cyber)


if __name__ == "__main__":
    unittest.main()
