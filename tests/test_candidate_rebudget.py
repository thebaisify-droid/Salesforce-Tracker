import unittest
from scripts.validate_candidate_rebudget import validate

BASE={"paid_acquisition_enabled":False,"additional_spend_approved_usd":0,
"proposed_caps_usd":{"CV-Library":.30,"Totaljobs":.20,"Indeed UK":.15,"JobServe":.15},
"proposed_total_usd":.80,"shared_monthly_account_limit_usd":19,
"protected_salesforce_headroom_usd":8,"maximum_results_per_source":10}
class RebudgetTests(unittest.TestCase):
 def test_proposal_valid_but_never_authorised(self):
  r=validate(BASE)
  self.assertTrue(r["proposal_valid"])
  self.assertFalse(r["pilot_authorised"])
  self.assertFalse(r["paid_requests_allowed"])
 def test_original_failed_cv_cap_blocked(self):
  p={**BASE,"proposed_caps_usd":{**BASE["proposed_caps_usd"],"CV-Library":.10},"proposed_total_usd":.60}
  self.assertFalse(validate(p)["proposal_valid"])
 def test_cannot_increase_ceiling_or_reduce_protection(self):
  self.assertFalse(validate({**BASE,"shared_monthly_account_limit_usd":30})["proposal_valid"])
  self.assertFalse(validate({**BASE,"protected_salesforce_headroom_usd":2})["proposal_valid"])
 def test_no_spend_authorisation(self):
  self.assertFalse(validate({**BASE,"additional_spend_approved_usd":.80})["proposal_valid"])
if __name__=="__main__":unittest.main()
