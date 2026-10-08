import unittest

from scripts.build_candidate_market_dashboard import build_snapshot

class CandidateMarketDashboardTests(unittest.TestCase):
    def test_separate_tracks_and_deduplication(self):
        rows = [
            {"title": "Senior Business Analyst", "url": "https://jobs.test/a?utm_source=x", "company": "A"},
            {"title": "Senior Business Analyst", "url": "https://jobs.test/a", "company": "A"},
            {"title": "SOC Analyst", "url": "https://jobs.test/soc", "company": "B"},
            {"title": "Cyber Security Consultant", "url": "https://jobs.test/cyber", "company": "C"},
            {"title": "Security Guard", "url": "https://jobs.test/guard"},
        ]
        result = build_snapshot(rows, "2026-10-08T12:00:00Z")
        self.assertEqual(result["total_vacancies"], 3)
        self.assertEqual([x["value"] for x in result["by_track"]], [1, 2])
        self.assertEqual(result["rejections"]["duplicate"], 1)
        self.assertEqual(result["rejections"]["excluded"], 1)
        self.assertEqual(result["mode"], "offline_candidate_only")
        self.assertFalse(result["acquisition_enabled"])
        self.assertFalse(result["publication_approved"])

    def test_invalid_records_do_not_publish(self):
        records = [
            {"title": "Data Analyst", "url": "javascript:alert(1)"},
            {"title": "Product Owner"},
            {"title": "IT Security Manager", "url": "https://jobs.test/it"},
            "bad row",
        ]
        out = build_snapshot(records, "2026-10-08T12:00:00Z")
        self.assertEqual(out["total_vacancies"], 1)
        self.assertEqual(out["rejections"]["invalid"], 2)
        self.assertEqual(out["rejections"]["malformed"], 1)

    def test_all_families_represented_in_zero_state(self):
        out = build_snapshot([], "2026-10-08T12:00:00Z")
        self.assertEqual(len(out["by_role_family"]), 22)
        self.assertEqual(out["total_vacancies"], 0)

if __name__ == "__main__":
    unittest.main()
