import unittest
from scripts.plan_salesforce_five_source_pilot import plan, TOTAL_CAP, REQUIRED

class FiveSourcePilotPlanTests(unittest.TestCase):
    def test_exact_five_sources_and_hard_caps(self):
        p = plan()
        self.assertEqual(len(p["sources"]), 5)
        self.assertEqual(round(sum(x["max_total_charge_usd"] for x in p["sources"]), 2), TOTAL_CAP)
        self.assertEqual(TOTAL_CAP, 0.90)
        self.assertEqual(p["required_sources"], list(REQUIRED))
        self.assertTrue(all(x["run_limit"] == 1 for x in p["sources"]))
        self.assertTrue(all(x["requested_max_results"] <= 20 for x in p["sources"]))

    def test_never_executes_or_publishes(self):
        p = plan()
        self.assertFalse(p["paid_pilot_authorised"])
        self.assertFalse(p["workflow_dispatch_enabled"])
        self.assertFalse(p["wordpress_publication_enabled"])
        self.assertFalse(p["production_database_writes_enabled"])
        self.assertEqual(p["actor_runs_started"], 0)
        self.assertEqual(p["auto_retries"], 0)
        self.assertFalse(p["jobserve_sdk_usage"])
