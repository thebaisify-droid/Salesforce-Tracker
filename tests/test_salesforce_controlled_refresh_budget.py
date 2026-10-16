import pathlib
import unittest
from scripts.salesforce_controlled_refresh_budget import check_account, MAX_RUN_USD


class ControlledRefreshSafetyTests(unittest.TestCase):
    def payload(self, used=8.0, cap=19.0):
        return {"data":{"limits":{"maxMonthlyUsageUsd":cap},
                        "current":{"monthlyUsageUsd":used}}}

    def test_five_source_worst_case(self):
        self.assertEqual(MAX_RUN_USD, 0.90)
        r = check_account(self.payload(7.95))
        self.assertEqual(r["account_limit_usd"],19.0)
        self.assertEqual(check_account(self.payload(7.95,25.0))["account_limit_usd"],25.0)
        self.assertEqual(r["protected_reserve_usd"],8.0)
        self.assertEqual(r["actors_started"],0)
        self.assertFalse(r["automatic_publication"])

    def test_insufficient_reserve_fails_closed(self):
        with self.assertRaises(ValueError):
            check_account(self.payload(10.2))

    def test_wrong_limit_and_missing_usage_rejected(self):
        for payload in (self.payload(1,30), {"data":{}},
                        self.payload(20,19)):
            with self.assertRaises(ValueError):
                check_account(payload)

    def test_schedule_has_enable_gate_and_no_publication(self):
        folder = pathlib.Path(".github/workflows")
        controlled = (folder/"salesforce-controlled-refresh.yml").read_text()
        legacy = (folder/"daily-refresh.yml").read_text()
        self.assertIn("vars.SF_CONTROLLED_REFRESH_ENABLED == 'true'",controlled)
        self.assertIn("vars.SF_LEGACY_REFRESH_ENABLED == 'true'",legacy)
        self.assertIn("shared-apify-acquisition",controlled)
        self.assertIn("salesforce_controlled_refresh_budget",controlled)
        self.assertIn("pipeline.daily_refresh --config config/pipeline.json --scheduled",controlled)
        self.assertNotIn("git push",controlled)
        self.assertIn("vars.SF_WORDPRESS_DELIVERY_ENABLED == 'true'", controlled)
        self.assertIn("verify_controlled_handoff", controlled)
        self.assertIn("SF_WP_APPLICATION_PASSWORD: ${{ secrets.SF_WP_APPLICATION_PASSWORD }}",controlled)
