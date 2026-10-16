"""No-cost QA regression for source-observed, user-reviewed 124-record union."""
import unittest

from scripts.ba_20261016_124_scope_preflight import candidate

class ReviewedBA124ScopePreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=candidate()

    def test_valid_union_preserves_exact_manual_source_overrides(self):
        r=self.report
        self.assertEqual((r["automatic_22_family_matches"],r["user_kept_adverts"],
                          r["already_in_baseline"],r["newly_in_scope"],
                          r["combined_in_scope"],r["remaining_not_kept"]),
                         (87,39,2,37,124,37))
        self.assertEqual(sum(r["source_counts"].values()),124)
        self.assertEqual(sum(r["role_families"].values()),124)
        self.assertEqual(r["specific_new_advert_urls"],37)

    def test_user_scope_is_not_employer_verification_or_publication_authorization(self):
        r=self.report
        self.assertTrue(r["source_observed_only"])
        self.assertFalse(r["employer_openings_independently_verified"])
        self.assertFalse(r["publication_approved"])
        self.assertEqual(r["status"],"STAGED_NOT_PUBLISHED")
        self.assertEqual(r["actor_runs_started"],0)
        self.assertEqual(r["wordpress_requests"],0)

    def test_five_source_wordpress_schema_preflight(self):
        r=self.report
        self.assertTrue(r["five_source_receipt_gate_passed"])
        self.assertTrue(r["live_payload_schema_preflight_passed"])
        self.assertEqual(len(r["source_counts"]),5)
        self.assertEqual(r["source_posted_dates_known"],124)
        print("BA_REVIEWED_SCOPE_PREFLIGHT "+__import__("json").dumps(r,sort_keys=True))

if __name__=="__main__":
    unittest.main()
