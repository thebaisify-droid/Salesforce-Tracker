import unittest
from scripts.validate_three_source_pilot import validate
from scripts import run_candidate_pilot_v2
BASE={"sources":[{"source":"Totaljobs","cap_usd":.2,"max_results":10},{"source":"Indeed UK","cap_usd":.15,"max_results":10},{"source":"JobServe","cap_usd":.15,"max_results":10}],"paid_execution_enabled":False,"allowed_actor_runs":0,"publication_enabled":False,"account_monthly_ceiling_usd":19,"minimum_protected_salesforce_headroom_usd":8,"maximum_total_usd":.5}
class ThreeSourceSafetyTests(unittest.TestCase):
 def test_proposal_bounded_but_unapproved(self):
  r=validate(BASE);self.assertTrue(r["valid"]);self.assertFalse(r["authorised"])
 def test_reject_cv_library(self):
  p={**BASE,"sources":BASE["sources"]+[{"source":"CV-Library","cap_usd":.3,"max_results":10}]}
  self.assertFalse(validate(p)["valid"])
 def test_reject_spending_or_budget_relaxation(self):
  self.assertFalse(validate({**BASE,"paid_execution_enabled":True})["valid"])
  self.assertFalse(validate({**BASE,"maximum_total_usd":.8})["valid"])
  self.assertFalse(validate({**BASE,"minimum_protected_salesforce_headroom_usd":2})["valid"])
 def test_legacy_pilot_disabled(self):
  self.assertFalse(run_candidate_pilot_v2.PAID_PILOT_ENABLED)
