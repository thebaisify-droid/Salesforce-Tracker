import json
import unittest
from pathlib import Path
from scripts.export_candidate_beta_review import export_review, FIELDS

class CandidateReviewExportTests(unittest.TestCase):
    def test_real_snapshot_review_handoff_never_invents_verification(self):
        source=json.loads(Path("candidate-beta/data/pilot-snapshot.json").read_text())
        rows=export_review(source)
        self.assertEqual(len(rows),30)
        self.assertEqual(len({r["id"] for r in rows}),30)
        self.assertTrue(all(r["title"] and r["url"] and r["source"] for r in rows))
        for r in rows:
            for key in FIELDS[8:]:
                self.assertEqual(r[key],"",key)
    def test_rejects_published_or_unknown_evidence(self):
        snap={"sample_only":True,"publication_approved":False,"records":[
            {"id":"a","source":"S","title":"T","url":"https://example.org",
             "publication_ready":False,"verification":"UNKNOWN"}]}
        with self.assertRaises(ValueError):
            export_review(snap)
        snap["records"][0]["verification"]="SOURCE_ONLY_UNVERIFIED"
        snap["publication_approved"]=True
        with self.assertRaises(ValueError):
            export_review(snap)

if __name__=="__main__":
    unittest.main()
