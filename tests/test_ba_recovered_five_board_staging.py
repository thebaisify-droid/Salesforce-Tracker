import json
import unittest
from copy import deepcopy
from pathlib import Path
from scripts.validate_ba_recovered_five_board_staging import verify
P=Path(__file__).resolve().parents[1]/"business-analysis-tracker/evidence/ba-five-source-recovered-staging-20261015.json"
class RecoveredFiveBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=json.loads(P.read_text(encoding="utf8"))
    def test_combined_staging_is_complete_but_unpublished(self):
        r=verify(self.data)
        self.assertTrue(r["valid_for_further_staging"],r["issues"])
        self.assertEqual(r["matching_source_advertisements"],57)
        self.assertFalse(r["may_publish"])
        self.assertEqual(self.data["excluded_total"],7)
        self.assertEqual(self.data["source_result_counts"]["JobServe"],24)
    def test_billing_exception_and_source_loss_fail_closed(self):
        d=deepcopy(self.data)
        d["source_retrieval_events"]["JobServe"]["limit_discrepancy_pending_review"]=False
        self.assertFalse(verify(d)["valid_for_further_staging"])
        d=deepcopy(self.data)
        d["records"]=[r for r in d["records"] if r["source"]!="JobServe"]
        self.assertFalse(verify(d)["valid_for_further_staging"])
    def test_no_forced_merge_and_preserve_original_links(self):
        p=self.data["potential_duplicate_pairs"]
        self.assertGreaterEqual(len(p),2)
        self.assertTrue(all(x["status"]=="POSSIBLE_ONLY" for x in p))
        self.assertEqual(len({r["id"] for r in self.data["records"]}),57)
        self.assertTrue(all(r["url"].startswith("https://") for r in self.data["records"]))
if __name__=="__main__": unittest.main()
