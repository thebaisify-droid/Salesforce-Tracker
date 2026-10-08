import unittest
from scripts.validate_candidate_pilot import validate

BASE={"core_sources":["CV-Library","Totaljobs","Indeed UK","JobServe"],
      "enabled":False,"paid_acquisition_enabled":False,"production_publication_enabled":False,
      "scheduled_runs":[],"actor_runs_to_launch":0,"additional_spend_approved_usd":0,
      "shared_account_monthly_limit_usd":19,
      "proposed_per_source_max_usd":{"CV-Library":.10,"Totaljobs":.10,"Indeed UK":.15,"JobServe":.15},
      "proposed_total_max_usd":.50}
class PilotSafetyTests(unittest.TestCase):
    def test_inactive_proposal_valid(self):
        r=validate(BASE)
        self.assertTrue(r["passed"])
        self.assertFalse(r["pilot_authorised"])
    def test_refuses_activation(self):
        for key,value in [("enabled",True),("paid_acquisition_enabled",True),
                          ("actor_runs_to_launch",1),("additional_spend_approved_usd",.1),
                          ("scheduled_runs",["daily"])]:
            with self.subTest(key=key):
                p={**BASE,key:value}
                self.assertFalse(validate(p)["passed"])
    def test_cannot_expand_monthly_ceiling(self):
        self.assertFalse(validate({**BASE,"shared_account_monthly_limit_usd":30})["passed"])
    def test_total_must_match_per_source_caps(self):
        self.assertFalse(validate({**BASE,"proposed_total_max_usd":.30})["passed"])
if __name__=="__main__":unittest.main()
