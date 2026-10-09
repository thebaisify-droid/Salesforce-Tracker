import unittest
from scripts.prepare_candidate_review import prepare

class PrepareCandidateReviewTests(unittest.TestCase):
    def test_keeps_negative_cases_and_never_auto_labels(self):
        rows = [
            {"title":"SOC Analyst","url":"https://example.test/1?utm_source=x","source":"Reed"},
            {"title":"SOC Analyst","url":"https://example.test/1","source":"Reed"},
            {"title":"Security Guard","url":"https://example.test/2","source":"Reed"},
            {"title":"Data Analyst","url":"https://example.test/3","source":"Totaljobs"}
        ]
        sample=prepare(rows)
        self.assertEqual(len(sample), 3)
        self.assertTrue(any(not x["predicted_included"] for x in sample))
        self.assertTrue(all(x["expected_included"] == "" and x["reviewer"] == "" for x in sample))
        self.assertTrue(all(x["sample_id"] and x["job_url"] for x in sample))
    def test_deterministic_stratified_cap(self):
        rows=[{"title":"Data Analyst","url":f"https://example.test/{i}","source":"Reed"} for i in range(12)]
        self.assertEqual(prepare(rows,3),prepare(list(reversed(rows)),3))
        self.assertEqual(len(prepare(rows,3)),3)
    def test_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            prepare([],0)

if __name__ == "__main__":
    unittest.main()
