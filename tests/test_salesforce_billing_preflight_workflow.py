import pathlib
import unittest

class ManualBillingPreflightTests(unittest.TestCase):
    def test_readonly_manual_only(self):
        workflow = pathlib.Path(".github/workflows/salesforce-billing-preflight.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertIn("salesforce_controlled_refresh_budget", workflow)
        self.assertIn("secrets.APIFY_TOKEN", workflow)
        self.assertNotIn("pipeline.daily_refresh --", workflow)
        self.assertNotIn("call_actor", workflow)
        self.assertNotIn("wp-json", workflow)
        self.assertNotIn("git push", workflow)
