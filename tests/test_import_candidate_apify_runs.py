import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_candidate_apify_runs import acquire, ACTOR_IDS

class CompletedDatasetImportTests(unittest.TestCase):
    def test_all_five_actor_ids_are_pinned(self):
        self.assertEqual(ACTOR_IDS, {
            "JobServe":"iEeTOwSjZDvAshw7Y",
            "Indeed UK":"BkcKc9frZp43LeRM7",
            "Totaljobs":"RO7aokuNWfmP0kV0G",
            "CV-Library":"T0edvAvD8lVcvc58G",
            "Reed":"4iavHborUyvW5vQgz",
        })

    def test_succeeded_dataset_is_read_only_and_unpublished(self):
        calls = []
        def get(route, token):
            calls.append(route)
            if route.startswith("actor-runs/"):
                return {"data":{"status":"SUCCEEDED","actId":"iEeTOwSjZDvAshw7Y","defaultDatasetId":"datasetABCDE","startedAt":"2026-10-10T08:00:00Z"}}
            if route == "datasets/datasetABCDE":
                return {"data":{"itemCount":1}}
            return [{"title":"Senior Business Analyst","url":"https://example.org/jobs/1","company":"Employer","postedDate":"Thursday, 8 October 2026"}]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/"review"
            report = acquire({"runs":[{"source":"JobServe","run_id":"runABCDE"}]},out,"dummy",get)
            self.assertEqual(report["actor_runs_started"],0)
            self.assertFalse(report["publication_approved"])
            self.assertEqual(report["results"][0]["normalized_rows"],1)
            self.assertEqual(len(calls),3)
            self.assertTrue(all(route.startswith(("actor-runs/","datasets/")) for route in calls))
            normalized=json.loads((out/"jobserve-runABCDE-candidate.json").read_text())
            self.assertEqual(normalized[0]["source"],"JobServe")
            self.assertEqual(normalized[0]["posted_at"],"Thursday, 8 October 2026")

    def test_actor_identity_mismatch_fails_closed(self):
        def get(route, token):
            return {"data":{"status":"SUCCEEDED","actId":"wrong","defaultDatasetId":"datasetABCDE"}}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Actor identity mismatch"):
                acquire({"runs":[{"source":"JobServe","run_id":"runABCDE"}]},Path(temp)/"review","dummy",get)

    def test_incomplete_dataset_fails_closed(self):
        def get(route, token):
            if route.startswith("actor-runs/"):
                return {"data":{"status":"SUCCEEDED","actId":"iEeTOwSjZDvAshw7Y","defaultDatasetId":"datasetABCDE"}}
            if route == "datasets/datasetABCDE":
                return {"data":{"itemCount":2}}
            return [{"title":"Business Analyst","url":"https://example.org/a"}]
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "Dataset count mismatch"):
                acquire({"runs":[{"source":"JobServe","run_id":"runABCDE"}]},Path(temp)/"review","dummy",get)

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
