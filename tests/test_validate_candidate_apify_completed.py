import unittest
from datetime import date

from scripts.validate_candidate_apify_completed import posting_day, validate_completed_runs
from scripts.import_candidate_apify_runs import ACTOR_IDS

class ApifyCompletedPythonValidationTests(unittest.TestCase):
    def test_date_formats(self):
        self.assertEqual(posting_day("2026-10-10T03:00:00Z"), date(2026,10,10))
        self.assertEqual(posting_day("Thursday, 8 October 2026"),date(2026,10,8))
        self.assertIsNone(posting_day("not a date"))

    def test_one_shot_five_sources_and_protected_publication(self):
        manifest={"publication_approved":False,"actor_runs_to_launch":0,"runs":[
            {"source":source,"run_id":"run0"+str(i)+"ABC"} for i, source in
            enumerate(["JobServe","Indeed UK","Reed","Totaljobs","CV-Library"],1)
        ]}
        ids={e["run_id"]:e["source"] for e in manifest["runs"]}
        datasets={source:"dataset0"+str(i)+"ABC" for i,source in enumerate(ACTOR_IDS,1)}
        data={
          "JobServe":[{"title":"Senior Business Analyst","url":"https://example.org/1","postedDate":"Thursday, 8 October 2026"}],
          "Indeed UK":[{"title":"Security Guard","url":"https://example.org/2","postedAt":"2026-09-01T00:00:00Z"}],
          "Reed":[{"title":"Product Owner","url":"https://example.org/3","datePosted":"2026-10-09T00:00:00Z"}],
          "Totaljobs":[{"title":"Data Analyst","jobUrl":"https://example.org/4","datePosted":"2026-10-06T00:00:00Z","company":{"name":"Example"},"location":{"text":"London"}}],
          "CV-Library":[{"title":"SOC Analyst","canonicalUrl":"https://example.org/5","postedAt":"2026-10-10T00:00:00Z"},{"jobId":"expired-job-key","changeType":"EXPIRED","expiredAt":"2026-10-10T00:00:00Z"}]
        }
        by_dataset={datasets[s]:s for s in datasets}
        calls=[]
        def mock_get(route, token):
            calls.append(route)
            if route.startswith("actor-runs/"):
                source=ids[route.split("/")[-1]]
                return {"data":{"status":"SUCCEEDED","actId":ACTOR_IDS[source],"defaultDatasetId":datasets[source]}}
            ds=route.split("/")[1]
            source=by_dataset[ds]
            if route.endswith("/items?clean=false&limit=1000"):
                return data[source]
            return {"data":{"itemCount":len(data[source])}}
        report=validate_completed_runs(manifest,token="dummy",getter=mock_get,today=date(2026,10,14))
        self.assertEqual(report["run_count"],5)
        self.assertEqual(report["raw_rows"],6)
        self.assertEqual(report["normalized_job_rows"],5)
        self.assertEqual(report["expiry_events_review_only"],1)
        self.assertEqual(report["unique_classified_vacancies"],4)
        self.assertEqual(sum(x["count"] for x in report["role_family_counts"]),4)
        self.assertFalse(report["publication_approved"])
        self.assertFalse(report["acquisition_enabled"])
        self.assertEqual(report["actor_runs_started"],0)
        self.assertFalse(report["refresh_quality"]["ready_for_publication"])
        self.assertEqual(report["refresh_quality"]["classified_rows"],4)
        self.assertEqual(report["refresh_quality"]["classified_fresh"],3)
        self.assertEqual(report["refresh_quality"]["classified_stale"],1)
        self.assertEqual(len(calls),15)
        self.assertTrue(all(s.startswith(("actor-runs/","datasets/")) for s in calls))

    def test_refuse_publication_enabled_manifests_before_network(self):
        with self.assertRaisesRegex(ValueError,"Only explicitly disabled"):
            validate_completed_runs({"publication_approved":True,"actor_runs_to_launch":0,"runs":[]},
                                    token="unused",getter=lambda *args: self.fail("network"))
