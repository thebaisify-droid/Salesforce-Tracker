import unittest
from scripts.review_existing_candidate_pilot import extract
from scripts.candidate_evidence_gate import assess
class HistoricalPilotQualityTests(unittest.TestCase):
 def test_retains_all_three_sources(self):
  rows=extract({"results":[{"source":"Totaljobs","vacancies":[{"title":"Business Analyst","url":"https://example.org/a"}]},{"source":"Indeed UK","vacancies":[]},{"source":"JobServe","vacancies":[]}]})
  self.assertEqual(len(rows),1)
  gate=assess(rows)
  self.assertEqual(gate["publication_ready_count"],0)
  self.assertIn("EMPLOYER_UNVERIFIED",gate["records"][0]["flags"])
 def test_invalid_source_rejected(self):
  with self.assertRaises(ValueError):extract({"results":[{"source":"CV-Library","vacancies":[]}]})
