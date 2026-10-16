"""Read-only controls for five completed Apify datasets, no Actor or WP calls."""
from __future__ import annotations
import json
import unittest
from collections import Counter

from scripts.ba_quality_audit_20261016 import inspect, EVIDENCE

class BACompletedDatasetQualityAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = inspect()

    def test_all_161_completed_source_rows_and_actor_provenance(self):
        r=self.result
        self.assertEqual(r["total_source_rows_observed"],161)
        self.assertEqual(r["sources_succeeded"],5)
        self.assertEqual(r["dataset_counts"],{
            "CV-Library":30,"Totaljobs":25,"Reed UK":30,
            "Indeed UK":30,"JobServe":46,
        })
        self.assertEqual(len({x["actor_run_id"] for x in r["sources"]}),5)
        self.assertTrue(all(x["dataset_id"] for x in r["sources"]))
        self.assertFalse(r["publication_approved"])
        self.assertEqual(r["paid_actor_runs_started_by_audit"],0)
        self.assertEqual(r["wordpress_requests"],0)

    def test_drift_and_jobserve_30_row_overrun_are_not_waived(self):
        self.assertTrue(self.result["jobserve_output_limit_breach"])
        self.assertTrue(self.result["source_count_drift_warning"])
        observed={r["source"]:r["observed_count_growth"] for r in self.result["sources"]}
        self.assertEqual(observed,{"CV-Library":0,"Totaljobs":0,
                                   "Reed UK":30,"Indeed UK":1,"JobServe":22})
        self.assertFalse(self.result["billing_cost_verified"])

    def test_full_taxonomy_classification_is_preview_only(self):
        q=self.result["pipeline_qa_preview"]
        self.assertGreater(q["taxonomy_matched_after_url_and_duplicate_filters"],0)
        self.assertLessEqual(q["taxonomy_matched_after_url_and_duplicate_filters"],161)
        self.assertLessEqual(q["distinct_families"],22)
        self.assertEqual(sum(q["title_family_counts"].values()),
                         q["taxonomy_matched_after_url_and_duplicate_filters"])
        self.assertLessEqual(q["advertiser_sector_evidenced"],
                             q["taxonomy_matched_after_url_and_duplicate_filters"])
        self.assertTrue(self.result["status"].startswith("OFFLINE_AUDIT_ONLY"))
        print("OFFLINE_AUDIT_RESULT "+json.dumps({
            "counts":self.result["dataset_counts"],
            "match_count":q["taxonomy_matched_after_url_and_duplicate_filters"],
            "families":q["title_family_counts"],
            "source_accepted":q["source_accepted_counts"],
            "excluded":q["excluded_counts"],
            "possible_duplicate_rows":q["possible_duplicate_rows"],
            "sector_evidenced":q["advertiser_sector_evidenced"],
            "posted_dates_available":q["posted_dates_available"],
            "working_arrangement_available":q["working_arrangement_available"],
            "training_patterns":q["training_or_nonvacancy_patterns_in_candidate"],
            "publication_approved":False,"paid_actors_started":0,
        },sort_keys=True))

    def test_no_personal_contacts_embedded_in_trimmed_evidence(self):
        raw=EVIDENCE.read_text(encoding="utf8")
        self.assertLess(len(raw),200000)
        doc=json.loads(raw)
        self.assertEqual(sum(len(s["records"]) for s in doc["sources"]),161)
        for group in doc["sources"]:
            for row in group["records"]:
                self.assertFalse(any(k in row for k in ("contactEmail","contactPhone",
                    "contactName","extractedEmails","extractedPhones","descriptionHtml")))

if __name__=="__main__":
    unittest.main()
