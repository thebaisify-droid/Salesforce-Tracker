import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_candidate_apify_runs import acquire

class CompletedDatasetImportTests(unittest.TestCase):
    def test_succeeded_dataset_is_read_only_and_unpublished(self):
        calls = []
        def get(route, token):
            calls.append(route)
            if route.startswith("actor-runs/"):
                return {"data":{"status":"SUCCEEDED","defaultDatasetId":"datasetABCDE","startedAt":"2026-10-10T08:00:00Z"}}
            return [{"title":"Senior Business Analyst","url":"https://example.org/jobs/1","company":"Employer"}]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/"review"
            report = acquire({"runs":[{"source":"Indeed UK","run_id":"runABCDE"}]},out,"dummy",get)
            self.assertEqual(report["actor_runs_started"],0)
            self.assertFalse(report["publication_approved"])
            self.assertEqual(report["results"][0]["normalized_rows"],1)
            self.assertEqual(len(calls),2)
            self.assertTrue(all(route.startswith(("actor-runs/","datasets/")) for route in calls))
            normalized=json.loads((out/"indeed-uk-runABCDE-candidate.json").read_text())
            self.assertEqual(normalized[0]["source"],"Indeed UK")

    def test_failed_run_never_downloads_or_writes(self):
        calls=[]
        def get(route, token):
            calls.append(route)
            return {"data":{"status":"FAILED","defaultDatasetId":"datasetABCDE"}}
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"review"
            with self.assertRaises(ValueError):
                acquire({"runs":[{"source":"JobServe","run_id":"runABCDE"}]},path,"dummy",get)
            self.assertFalse(path.exists())
            self.assertEqual(calls,["actor-runs/runABCDE"])

    def test_manifest_rejects_unknown_sources_before_requests(self):
        def fail(*args):
            self.fail("No provider request should occur")
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                acquire({"runs":[{"source":"Other","run_id":"runABCDE"}]},Path(temp)/"review","dummy",fail)

    def test_cannot_target_dashboard(self):
        with self.assertRaises(ValueError):
            acquire({"runs":[{"source":"Indeed UK","run_id":"runABCDE"}]},Path("candidate-beta/data"),"dummy")

if __name__ == "__main__":
    unittest.main()
