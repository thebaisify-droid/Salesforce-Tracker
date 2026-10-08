import json
import unittest
from pathlib import Path
from scripts.validate_candidate_saved_tasks import check

class SavedTaskEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.doc=json.loads(Path("config/candidate_saved_task_evidence.example.json").read_text(encoding="utf-8"))
    def test_unverified_is_safe_but_blocked(self):
        result=check(self.doc)
        self.assertTrue(result["safe_specification"])
        self.assertFalse(result["task_overrides_verified"])
        self.assertFalse(result["paid_acquisition_authorised"])
    def test_unsubstantiated_claim_fails(self):
        self.doc["task_checks"][0]["non_salesforce_search_verified"]=True
        self.assertFalse(check(self.doc)["safe_specification"])
    def test_paid_calls_never_allowed(self):
        self.doc["paid_calls_permitted"]=True
        self.assertFalse(check(self.doc)["safe_specification"])

if __name__=="__main__":unittest.main()
