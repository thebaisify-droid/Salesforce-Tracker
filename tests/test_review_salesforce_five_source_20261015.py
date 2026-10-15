import pathlib
import unittest
from scripts.review_salesforce_five_source_20261015 import SOURCES, analyse, map_row

class ReadonlyFiveSourceQualityTests(unittest.TestCase):
    def test_normalise_and_classify(self):
        row={"title":"Salesforce Developer","employer":{"name":"Company Ltd"},
             "datePosted":"2026-10-15T08:00:00Z",
             "url":"https://www.reed.co.uk/jobs/123",
             "descriptionSnippet":"Apex and Sales Cloud"}
        out=map_row(row,"Reed UK")
        self.assertEqual(out["advertiser"],"Company Ltd")
        self.assertEqual(out["relevance"],"CORE_CANDIDATE")
        self.assertFalse(out["publication_allowed"])

    def test_lifecycle_separation_and_dedup(self):
        payloads={dataset:[] for _,dataset,_ in SOURCES}
        # Each immutable dataset's expected row counts must be obeyed.
        for src,dataset,n in SOURCES:
            payloads[dataset]=[{"title":f"Salesforce Developer {i}",
                                "company":src,"url":"https://www.reed.co.uk/jobs/123",
                                "datePosted":"2026-10-15T08:00:00Z"}
                               for i in range(n)]
        payloads[SOURCES[0][1]][0]={"jobId":"abc","changeType":"EXPIRED","expiredAt":"2026-10-15T00:00:00Z"}
        payloads[SOURCES[1][1]][0]={"title":"Salesforce Developer 1","company":"CV-Library",
                                     "url":"https://www.totaljobs.com/job/123"}
        report,rows,events=analyse(payloads)
        self.assertEqual(report["raw_rows"],97)
        self.assertEqual(report["expiry_events"],1)
        self.assertEqual(report["advert_rows"],96)
        self.assertGreater(report["duplicate_excess"],0)
        self.assertFalse(report["publication_allowed"])
        self.assertEqual(report["actors_started"],0)
        self.assertEqual(len(events),1)
        self.assertTrue(all(not x["publication_allowed"] for x in rows))

    def test_source_count_mismatch_blocks(self):
        with self.assertRaises(ValueError):
            analyse({d:[] for _,d,_ in SOURCES})

    def test_readonly_workflow(self):
        w=pathlib.Path(".github/workflows/salesforce-five-source-review.yml").read_text()
        self.assertIn("workflow_dispatch:",w)
        self.assertNotIn("schedule:",w)
        self.assertNotIn("call_actor",w)
        self.assertNotIn("git push",w)
        self.assertNotIn("wordpress",w.lower())
        self.assertIn("review_salesforce_five_source_20261015",w)
