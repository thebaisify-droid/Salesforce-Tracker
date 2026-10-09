import json
import unittest
from pathlib import Path
from scripts.validate_candidate_search_plan import check

class CandidateSearchDryRunTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads(Path("config/candidate_search_dry_run.example.json").read_text(encoding="utf-8"))
    def test_inactive_valid(self):
        r=check(self.plan)
        self.assertTrue(r["passed"])
        self.assertFalse(r["acquisition_authorised"])
    def test_no_expensive_run(self):
        p={**self.plan,"actor_runs_allowed":1}
        self.assertFalse(check(p)["passed"])
    def test_saved_task_overrides_unverified(self):
        p=json.loads(json.dumps(self.plan))
        next(x for x in p["source_inputs"] if x["source"]=="CV-Library")["example_input"]={"query":"product owner"}
        self.assertFalse(check(p)["passed"])
    def test_country_and_per_source_caps(self):
        p=json.loads(json.dumps(self.plan))
        s=next(x for x in p["source_inputs"] if x["source"]=="Indeed UK")
        s["example_input"]["country"]="us"
        self.assertFalse(check(p)["passed"])
        s["example_input"]["country"]="uk"
        s["max_total_charge_usd"]=1.0
        self.assertFalse(check(p)["passed"])
if __name__=="__main__": unittest.main()
