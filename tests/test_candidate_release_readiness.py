import unittest
from scripts.candidate_release_readiness import assess

class CandidateReadinessTests(unittest.TestCase):
    def test_no_data_fails_closed(self):
        r=assess(assurance={}, evidence={})
        self.assertFalse(r["ready_for_review"])
        self.assertFalse(r["publication_approved"])
        self.assertFalse(r["paid_acquisition_enabled"])
        self.assertIn("no_human_labelled_source_evidence",r["reasons"])
    def test_synthetic_cannot_pass(self):
        a={"evidence_level":"labelled_fixtures_only","passed":True,"sample_size":200,
           "sources":{"CV-Library":50,"Totaljobs":50,"Reed":50,"JobServe":50}}
        e={k:True for k in ("source_authenticity_confirmed","independent_review_confirmed",
           "unbiased_sampling_confirmed","cross_source_deduplication_checked",
           "account_spend_limit_confirmed_at_or_below_19_usd",
           "independent_database_restore_tested","website_filter_navigation_tested")}
        e["configured_role_families"]=22
        r=assess(assurance=a,evidence=e)
        self.assertFalse(r["ready_for_review"])
        self.assertIn("no_human_labelled_source_evidence",r["reasons"])
    def test_missing_jobserve_blocks_readiness(self):
        a={"evidence_level":"human_labelled_source_records","passed":True,"sample_size":120,
           "sources":{"CV-Library":40,"Totaljobs":40,"Reed":40}}
        e={k:True for k in ("source_authenticity_confirmed","independent_review_confirmed",
           "unbiased_sampling_confirmed","cross_source_deduplication_checked",
           "account_spend_limit_confirmed_at_or_below_19_usd",
           "independent_database_restore_tested","website_filter_navigation_tested")}
        e["configured_role_families"]=22
        r=assess(assurance=a,evidence=e)
        self.assertFalse(r["ready_for_review"])
        self.assertIn("missing_core_source_review_coverage",r["reasons"])

    def test_complete_evidence_still_never_automatically_publishes(self):
        a={"evidence_level":"human_labelled_source_records","passed":True,"sample_size":120,
           "sources":{"CV-Library":30,"Totaljobs":30,"Reed":30,"JobServe":30}}
        e={k:True for k in ("source_authenticity_confirmed","independent_review_confirmed",
           "unbiased_sampling_confirmed","cross_source_deduplication_checked",
           "account_spend_limit_confirmed_at_or_below_19_usd",
           "independent_database_restore_tested","website_filter_navigation_tested")}
        e["configured_role_families"]=22
        r=assess(assurance=a,evidence=e)
        self.assertTrue(r["ready_for_review"])
        self.assertFalse(r["publication_approved"])
        self.assertFalse(r["paid_acquisition_enabled"])

if __name__=="__main__":
    unittest.main()
