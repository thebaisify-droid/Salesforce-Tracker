"""A five-source BA pilot must remain guarded until billing and explicit approval."""
import json
import unittest
from pathlib import Path
from scripts.ba_five_source_activation_preflight import preflight
ROOT=Path(__file__).resolve().parents[1]/"business-analysis-tracker/config"

class TestFiveSourceActivationPreflight(unittest.TestCase):
    def setUp(self):
        self.contract=json.loads((ROOT/"five_source_refresh.json").read_text())
        self.inputs=json.loads((ROOT/"five_source_search_inputs.json").read_text())
    def test_valid_offline_inputs_but_no_paid_approval(self):
        r=preflight(self.contract,self.inputs)
        self.assertTrue(r["config_valid"],r["issues"])
        self.assertTrue(r["all_five_inputs_prepared"])
        self.assertFalse(r["paid_activation_ready"])
        self.assertEqual(r["actor_runs_started"],0)
        self.assertIn("actual_monthly_apify_usage_read",r["missing_activation_evidence"])
    def test_cannot_drop_fifth_source(self):
        self.inputs["inputs"]=self.inputs["inputs"][:4]
        self.assertFalse(preflight(self.contract,self.inputs)["config_valid"])
    def test_prevent_salesforce_query_and_overbudget(self):
        self.inputs["inputs"][0]["input"]["query"]="salesforce business analyst"
        self.assertFalse(preflight(self.contract,self.inputs)["config_valid"])
        self.inputs["inputs"][0]["input"]["query"]="business analyst"
        self.inputs["inputs"][0]["input"]["maxResults"]=1000
        self.assertFalse(preflight(self.contract,self.inputs)["config_valid"])

if __name__=="__main__":
    unittest.main()
