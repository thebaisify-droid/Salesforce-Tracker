"""Prevent BA role gap and budget drift without launching acquisition."""
import unittest
from scripts.ba_gap_readiness import check, GAPS

class BAGapReadinessTests(unittest.TestCase):
    def test_gap_queries_and_five_slot_coverage(self):
        result=check()
        self.assertEqual(result["status"],"OFFLINE_GAP_READINESS_NO_COST")
        self.assertEqual({r["family"] for r in result["missing_family_queries"]},set(GAPS))
        self.assertTrue(all(r["query"] and 1<=r["earliest_rotation_slot"]<=5 for r in result["missing_family_queries"]))
        self.assertEqual(result["all_22_taxonomy_families_have_rotation_by_slot"],5)

    def test_paused_and_correct_monetary_caps(self):
        r=check()
        self.assertFalse(r["paid_refresh_enabled"])
        self.assertEqual(r["actor_runs_started"],0)
        self.assertEqual(r["wordpress_snapshots_sent"],0)
        self.assertEqual(r["budget"],{"monthly_limit_usd":19,"monthly_ba_allowance_usd":11,
                                      "max_total_charge_usd":1.2,"salesforce_reserve_usd":8})

if __name__=="__main__":
    unittest.main()
