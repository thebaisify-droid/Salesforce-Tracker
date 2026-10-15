"""Five-source end-to-end dry run, offline fixtures and fail-closed source checks."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from scripts.ba_e2e_offline import run_offline
from scripts.ba_stage_five_source_data import link
ROOT=Path(__file__).resolve().parents[1]
MAP=ROOT/"business-analysis-tracker/config/sector-evidence.json"
BOARDS=[
 ("CV-Library",{"title":"Business Analyst","url":"https://www.cv-library.co.uk/job/test001","company":"Bupa","postedAt":"2026-10-14","location":"London"}),
 ("Totaljobs",{"title":"Product Owner","jobUrl":"https://www.totaljobs.com/job/test002","employer":{"name":"Deloitte"},"datePosted":"2026-10-14","location":"Leeds","rowType":"job"}),
 ("Reed UK",{"title":"Business Analyst","url":"https://www.reed.co.uk/jobs/test003","employer":"Falkirk Council","datePosted":"2026-10-14","location":"Scotland"}),
 ("Indeed UK",{"title":"Business Analyst","url":"https://uk.indeed.com/viewjob?jk=synthetic04","company":"Capgemini","postedAt":"2026-10-14","location":"UK"}),
 ("JobServe",{"title":"Business Analyst","url":"https://www.jobserve.com/gb/en/test005","company":"Dunelm","postedDateTime":"2026-10-14","location":"Manchester"}),
]
def example():
    return {"schema":"ba-five-source-completed-batch/v1",
     "sources":[{"name":name,"status":"SUCCEEDED","attempted":True,
       "run_id":"offline-test-run-"+str(i),"dataset_id":"offline-test-dataset-"+str(i),
       "observed_at":"2026-10-15T15:00:00Z","records":[deepcopy(row)]}
       for i,(name,row) in enumerate(BOARDS)]}
class TestBAE2EDryRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads(MAP.read_text(encoding="utf8"))
    def test_full_five_source_package_has_no_side_effects(self):
        from scripts.ba_stage_five_source_data import field, urlsplit
        self.assertEqual(field(BOARDS[0][1], 'url'), 'https://www.cv-library.co.uk/job/test001')
        self.assertEqual(urlsplit('https://www.cv-library.co.uk/job/test001').scheme, 'https')
        self.assertEqual(link(BOARDS[0][1], 'CV-Library'), 'https://www.cv-library.co.uk/job/test001')
        r=run_offline(example(),self.evidence)
        self.assertEqual(r["status"],"DRY_RUN_PASS_NOT_PUBLISHED")
        self.assertEqual(r["matched"],5)
        self.assertEqual(r["actors_started"],0)
        self.assertEqual(r["wordpress_requests"],0)
        self.assertEqual(r["package"]["rows"],5)
        self.assertIn("View original advert",r["package"]["table_fragment"])
        self.assertEqual(r["package"]["embedded_json_fragment"].count('"source_run_id"'),5)
        self.assertEqual({x["source"] for x in r["candidate"]["records"]},{x[0] for x in BOARDS})
        self.assertTrue(all(x["sector_evidence_url"] for x in r["candidate"]["records"]))
    def test_failed_or_missing_fifth_source_never_publishes(self):
        d=example()
        d["sources"][-1]["status"]="FAILED"
        self.assertEqual(run_offline(d,self.evidence)["status"],"BLOCKED_PRESERVE_LIVE_SNAPSHOT")
        d=example()
        d["sources"].pop()
        with self.assertRaises(ValueError):
            run_offline(d,self.evidence)
    def test_bad_url_fails_data_quality(self):
        d=example()
        d["sources"][0]["records"][0]["url"]="http://unsafe.example/job"
        with self.assertRaisesRegex(ValueError,"NOT_ALL_FIVE_SOURCES_PRESENT"):
            run_offline(d,self.evidence)
if __name__=="__main__":unittest.main()
