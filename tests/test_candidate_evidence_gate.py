import unittest
from scripts.candidate_evidence_gate import assess,identity_url
class EvidenceGateTests(unittest.TestCase):
 def test_incomplete_pilot_metadata_blocked(self):
  r=assess([{"title":"Business Analyst","source":"Indeed UK","url":"https://uk.indeed.com/viewjob?jk=abc"}])
  self.assertEqual(r["publication_ready_count"],0)
  self.assertIn("DESCRIPTION_UNAVAILABLE",r["records"][0]["flags"])
  self.assertFalse(r["publication_approved"])
 def test_url_id_and_duplicate(self):
  self.assertEqual(identity_url("https://uk.indeed.com/viewjob?jk=A23"),identity_url("https://uk.indeed.com/jobs?q=ba&jk=A23"))
  r=assess([{"title":"Business Analyst","url":"https://uk.indeed.com/viewjob?jk=xyz"},{"title":"Business Analyst","url":"https://uk.indeed.com/jobs?jk=xyz"}])
  self.assertIn("DUPLICATE_URL",r["records"][1]["flags"])
 def test_cross_source_duplicate_suspected(self):
  common={"title":"Senior Business Analyst","employer":"Example Ltd","location":"England"}
  r=assess([{**common,"source":"JobServe","url":"https://example.org/a"},{**common,"source":"Totaljobs","url":"https://example.com/b"}])
  self.assertIn("POTENTIAL_CROSS_SOURCE_DUPLICATE",r["records"][0]["flags"])
 def test_production_never_approved(self):
  self.assertFalse(assess([])["passed"])
  self.assertFalse(assess([])["security_coverage_verified"])
if __name__=="__main__":unittest.main()
