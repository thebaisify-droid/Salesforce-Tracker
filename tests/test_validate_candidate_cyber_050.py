import json
import unittest
from pathlib import Path
from scripts.validate_candidate_cyber_050 import validate
class CyberPilotProposalTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path("config/candidate_cyber_050_proposal.json").read_text())
    def test_valid_but_not_authorised(self):
        x=validate(self.p)
        self.assertTrue(x["offline_plan_valid"])
        self.assertFalse(x["execution_ready"])
        self.assertFalse(x["acquisition_authorised"])
        self.assertEqual(len(x["blocked_by"]),4)
    def test_refuse_paid_or_scheduled(self):
        self.p["approved_spend_usd"]=.5
        self.p["actor_runs_allowed"]=2
        self.p["scheduled"]=True
        self.assertFalse(validate(self.p)["offline_plan_valid"])
    def test_refuse_higher_cap(self):
        self.p["source_runs"][0]["max_total_charge_usd"]=0.5
        self.assertFalse(validate(self.p)["offline_plan_valid"])
if __name__=="__main__":unittest.main()
