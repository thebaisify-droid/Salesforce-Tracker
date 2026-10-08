import json,unittest
from pathlib import Path
class CandidateBetaIsolationTests(unittest.TestCase):
 def setUp(self):
  self.data=json.loads(Path("candidate-beta/data/pilot-snapshot.json").read_text())
  self.html=Path("candidate-beta/index.html").read_text()
 def test_historical_sample_only(self):
  self.assertEqual(len(self.data["records"]),30)
  self.assertEqual({r["source"] for r in self.data["records"]},{"Totaljobs","Indeed UK","JobServe"})
  self.assertFalse(self.data["publication_approved"])
  self.assertFalse(self.data["verified_representative_coverage"])
  self.assertTrue(all(r["publication_ready"] is False for r in self.data["records"]))
 def test_no_production_link_or_fake_metrics(self):
  self.assertIn("BETA",self.html)
  self.assertIn("not</strong> representative",self.html)
  self.assertNotIn("dashboard/live-data.json",self.html)
  self.assertIn("textNode(r.title)",self.html)
 def test_external_links_safe(self):
  from urllib.parse import urlsplit
  self.assertTrue(all(urlsplit(r["url"]).scheme=="https" for r in self.data["records"]))
if __name__=="__main__":unittest.main()
