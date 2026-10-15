import json
import unittest
from copy import deepcopy
from pathlib import Path
from scripts.ba_controlled_refresh import validate
from scripts.ba_wordpress_delivery_package import preflight, pack
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"business-analysis-tracker/config/automated_refresh_pipeline.json"
CANDIDATE=ROOT/"business-analysis-tracker/evidence/ba-five-source-publication-candidate-20261015.json"
class BARefreshPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text(encoding="utf8"))
        cls.data=json.loads(CANDIDATE.read_text(encoding="utf8"))
    def test_user_approved_recurring_caps_are_active(self):
        p=validate(self.cfg)
        self.assertTrue(p["valid"])
        self.assertTrue(p["enabled"])
        self.assertTrue(self.cfg["recurring_budget_approved"])
        self.assertEqual(self.cfg["monthly_ba_allowance_usd"],11)
        self.assertTrue(self.cfg["wordpress_delivery_enabled"])
        self.assertEqual(p["max_total_charge_usd"],1.2)
        self.assertEqual(p["actor_runs_launched"],0)
    def test_bad_budget_fails(self):
        v=deepcopy(self.cfg)
        v["monthly_limit_usd"]=30
        with self.assertRaises(ValueError):validate(v)
        v=deepcopy(self.cfg)
        v["automatic_retries"]=1
        with self.assertRaises(ValueError):validate(v)
    def test_historical_release_cannot_implicitly_publish(self):
        result=preflight(self.data)
        self.assertFalse(result["valid_for_wordpress_delivery"])
        self.assertIn("FRESH_BATCH_RECEIPTS_NOT_PROVIDED",result["issues"])
    def test_valid_receipts_generate_package_but_not_publish(self):
        names=["CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"]
        receipts=[{"source":name,"attempted":True,"status":"SUCCEEDED"} for name in names]
        report=preflight(self.data,receipts)
        self.assertTrue(report["valid_for_wordpress_delivery"],report["issues"])
        out=pack(self.data,receipts)
        self.assertFalse(out["delivery_approved"])
        self.assertEqual(out["rows"],57)
        self.assertEqual(out["table_fragment"].count('class="ba-v2-record"'),57)
        self.assertEqual(out["embedded_json_fragment"].count('"source_run_id"'),57)
    def test_missing_board_stops_delivery(self):
        receipts=[{"source":x,"attempted":True,"status":"SUCCEEDED"} for x in ["CV-Library","Totaljobs","Reed UK","Indeed UK"]]
        self.assertFalse(preflight(self.data,receipts)["valid_for_wordpress_delivery"])
if __name__=="__main__":unittest.main()
