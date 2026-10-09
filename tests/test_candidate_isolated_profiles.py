import json
import unittest
from pathlib import Path
from scripts.validate_candidate_isolated_profiles import validate

class IsolatedSearchProfileTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads(Path("config/candidate_isolated_search_profiles.example.json").read_text(encoding="utf-8"))
    def test_inactive_profiles_pass(self):
        result=validate(self.p)
        self.assertTrue(result["safe_proposal"])
        self.assertFalse(result["ready_for_paid_run"])
    def test_existing_saved_tasks_must_remain_immutable(self):
        self.p["production_tasks_immutable"]=False
        self.assertFalse(validate(self.p)["safe_proposal"])
    def test_reject_unsubstantiated_schema_confirmation(self):
        self.p["source_profiles"][1]["actor_input_schema_verified"]=True
        self.assertFalse(validate(self.p)["safe_proposal"])
    def test_reject_unbounded_search(self):
        self.p["source_profiles"][0]["proposed_searches"][0]["maxResults"]=1000
        self.assertFalse(validate(self.p)["safe_proposal"])

if __name__=="__main__":unittest.main()
