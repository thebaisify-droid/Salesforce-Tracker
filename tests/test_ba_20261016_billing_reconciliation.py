"""Regression for the one-time authenticated Apify run-cost evidence (offline only)."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECEIPTS=ROOT/"business-analysis-tracker/evidence/ba-20261016-actor-billing-verified.json"

class BillingReconciliationEvidence(unittest.TestCase):
    def test_authenticated_costs_fit_budget_and_exact_run_provenance(self):
        r=json.loads(RECEIPTS.read_text(encoding="utf8"))
        self.assertEqual(r["schema"],"ba-20261016-authenticated-run-costs/v1")
        self.assertEqual(len(r["runs"]),5)
        self.assertEqual(len({a["run_id"] for a in r["runs"]}),5)
        self.assertEqual(r["hard_monthly_ceiling_usd"],25)
        self.assertEqual(r["protected_salesforce_reserve_usd"],8)
        self.assertEqual(r["max_total_authorized_refresh_usd"],1.8)
        self.assertEqual(r["paid_actors_started_during_billing_audit"],0)
        self.assertEqual(r["wordpress_requests_during_billing_audit"],0)
        self.assertAlmostEqual(r["actual_five_run_total_usd"],0.433339,places=6)
        self.assertAlmostEqual(sum(a["actual_usd"] for a in r["runs"]),0.433339,places=6)
        self.assertTrue(all(a["actual_usd"]<=a["authorised_cap_usd"] for a in r["runs"]))
        self.assertTrue(r["all_within_individual_caps"])
        self.assertAlmostEqual(
            r["headroom_after_reserve_usd"],
            r["hard_monthly_ceiling_usd"]-r["protected_salesforce_reserve_usd"]
             -r["current_usage_snapshot_usd"],places=6)
        self.assertLess(r["actual_five_run_total_usd"],r["max_total_authorized_refresh_usd"])

if __name__=="__main__":
    unittest.main()
