import json,unittest
from pathlib import Path
class ValidationPlanTests(unittest.TestCase):
 def test_budget_guard_and_inactive(self):
  x=json.loads(Path("config/candidate_representative_validation_plan.json").read_text())
  self.assertFalse(x["paid_runs_enabled"])
  self.assertEqual(x["pilot_spend_approved_usd"],0)
  self.assertEqual(x["account_limit_usd"],19)
  self.assertGreaterEqual(x["salesforce_reserve_usd"],8)
  self.assertNotIn("CV-Library",x["required_sources"])
  self.assertEqual(len({f["family"] for f in x["families"]}),22)
  self.assertGreaterEqual(x["minimum_human_reviewed_records"],100)
