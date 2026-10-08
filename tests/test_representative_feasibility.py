import unittest
from scripts.validate_representative_feasibility import inspect
class ValidationFeasibilityTests(unittest.TestCase):
 def setUp(self):
  self.plan={"families":[{"family":str(i)} for i in range(22)],"proposed_validation_max_usd":1.50,"per_run_cap_usd":.15,"minimum_human_reviewed_records":100,"paid_runs_enabled":False,"pilot_spend_approved_usd":0}
 def test_budget_does_not_cover_22_separate_queries(self):
  r=inspect(self.plan)
  self.assertEqual(r["max_runs_at_declared_cap"],10)
  self.assertIn("budget_cannot_cover_individual_family_queries",r["reasons"])
  self.assertFalse(r["paid_execution_authorised"])
 def test_old_account_snapshot_does_not_satisfy_freshness(self):
  r=inspect(self.plan,actor_evidence={"source_schemas_verified":True,"account_charging_verified":True})
  self.assertIn("fresh_account_usage_required",r["reasons"])
 def test_no_release_in_any_case(self):
  r=inspect(self.plan,account_usage={"monthly_limit_usd":19,"usage_usd":6.63},actor_evidence={"validated_multi_family_batches":True,"source_schemas_verified":True,"account_charging_verified":True})
  self.assertFalse(r["production_publication_authorised"])
