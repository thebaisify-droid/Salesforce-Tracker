"""BA five-source staged data must neither launch collection nor publish."""
import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.ba_stage_five_source_data import stage

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "business-analysis-tracker/config/sector-evidence.json"


class TestBAFiveSourceStaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sector_map = json.loads(MAP.read_text(encoding="utf-8"))

    def example(self):
        def rec(name, rows):
            return {"name": name, "status": "SUCCEEDED", "attempted": True,
                    "run_id": "completed-" + name.lower().replace(" ", "-"),
                    "dataset_id": "existing-" + name.lower().replace(" ", "-"),
                    "observed_at": "2026-10-15T07:00:00Z", "records": rows}
        return {"schema": "ba-five-source-completed-batch/v1",
                "sources": [
                    rec("CV-Library", [{"title": "Business Analyst", "company": "Capgemini",
                                       "canonicalUrl": "https://www.cv-library.co.uk/job/12",
                                       "location": "London", "postedAt": "2026-10-14T09:00:00Z",
                                       "contractType": "Permanent", "changeType": "NEW"},
                                      {"title": "Business Analyst", "company": "Capgemini",
                                       "canonicalUrl": "https://www.cv-library.co.uk/job/99",
                                       "changeType": "EXPIRED"}]),
                    rec("Totaljobs", [{"rowType": "job", "title": "Business Analyst",
                                       "jobUrl": "https://www.totaljobs.com/job/ba/test-1",
                                       "employer": {"name": "Deloitte"}, "location": {"text": "London"},
                                       "employmentType": ["FULL_TIME"], "datePosted": "2026-10-13T08:00:00Z"}]),
                    rec("Reed UK", [{"title": "Data Analyst", "url": "https://www.reed.co.uk/jobs/data-analyst/123",
                                      "employer": "Falkirk Council", "location": "Scotland",
                                      "datePosted": "2026-10-12T00:00:00Z"}]),
                    rec("Indeed UK", [{"title": "Information Security Analyst",
                                        "url": "https://uk.indeed.com/viewjob?jk=abc",
                                        "company": "EY", "location": "London",
                                        "postedAt": "2026-10-11T00:00:00Z",
                                        "snippet": "Cyber security assurance."}]),
                    rec("JobServe", [{"title": "Business Analyst",
                                      "url": "https://www.jobserve.com/gb/en/QsTZ4",
                                      "company": "Bupa", "location": "London",
                                      "postedDateTime": "2026-10-10",
                                      "jobType": "Contract"}]),
                ]}

    def test_five_boards_stage_separately(self):
        report = stage(self.example(), self.sector_map)
        self.assertEqual(report["status"], "FIVE_SOURCES_RECEIVED_STAGED_ONLY")
        self.assertEqual(report["total_matching_advertisements"], 5)
        self.assertEqual(len({r["job_source"] for r in report["records"]}), 5)
        self.assertEqual(report["rejected"]["cv_expiry_event_ignored"], 1)
        self.assertFalse(report["wordpress_published"])
        self.assertTrue(report["salesforce_unchanged"])
        self.assertTrue(report["no_paid_runs_launched_by_stager"])
        self.assertTrue(all(x["original_advert_url"].startswith("https://") for x in report["records"]))
        self.assertTrue(all(x["end_client_sector"] == "Not specified" for x in report["records"]))
        self.assertTrue(all(x["sector_evidence_url"] for x in report["records"]))
        self.assertEqual({r["posted_date"] for r in report["records"]},
                         {"2026-10-10", "2026-10-11", "2026-10-12", "2026-10-13", "2026-10-14"})
        permanent = next(x for x in report["records"] if x["job_source"] == "CV-Library")
        self.assertEqual(permanent["employment"], "Permanent")
        totaljobs = next(x for x in report["records"] if x["job_source"] == "Totaljobs")
        self.assertEqual(totaljobs["employment"], "Not specified")  # full-time != permanent

    def test_missing_board_fails_closed_and_keeps_prior(self):
        batch = self.example()
        batch["sources"][-1]["status"] = "FAILED"
        result = stage(batch, self.sector_map)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["preserve_prior_snapshot"])
        self.assertEqual(result["records"], [])
        batch = self.example()
        batch["sources"] = batch["sources"][:4]
        self.assertTrue(stage(batch, self.sector_map)["preserve_prior_snapshot"])

    def test_incomplete_provenance_does_not_publish(self):
        batch = self.example()
        batch["sources"][0].pop("dataset_id")
        with self.assertRaises(ValueError):
            stage(batch, self.sector_map)


if __name__ == "__main__":
    unittest.main()
