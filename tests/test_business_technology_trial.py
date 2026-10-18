"""No-network checks for the 22-family and $25 acquisition budget."""
import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from scripts.ba_controlled_refresh import CONFIG, validate, run
from scripts.ba_acquisition_planner import role_queries, coverage_for_slots, select_slot
from scripts.ba_pricing_readonly import validate_cost_models

class TestBusinessTechnologyTrial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(CONFIG.read_text(encoding="utf8"))

    def test_no_blanket_ten_limit(self):
        self.assertTrue(validate(self.cfg)["valid"])
        self.assertTrue(all(10 < row["max_items"] <= 50 for row in self.cfg["sources"]))
        self.assertAlmostEqual(sum(row["max_charge_usd"] for row in self.cfg["sources"]), 1.2)
        self.assertEqual(self.cfg["monthly_ba_allowance_usd"],11)
        self.assertEqual(self.cfg["monthly_limit_usd"],19)
        self.assertEqual(self.cfg["salesforce_reserve_usd"],8)
        self.assertLessEqual(self.cfg["max_scheduled_runs_per_month"]*self.cfg["max_total_charge_usd"],11)

    def test_all_taxonomy_families_covered_across_five_slots(self):
        self.assertEqual(len(role_queries()),22)
        self.assertEqual(len(coverage_for_slots(5)),22)
        prices={"account_limit_usd":19,"actor_pricing":[
            {"source":row["name"],"pricing_model":"PRICE_PER_DATASET_ITEM",
             "price_per_unit_usd":0.005} for row in self.cfg["sources"]]}
        seen=set()
        for slot in range(1,6):
            plan=select_slot(self.cfg,slot,prices)
            names=[row["query_family"] for row in plan["sources"]]
            self.assertEqual(len(set(names)),5)
            seen.update(names)
            self.assertTrue(validate_cost_models(prices,plan)["pricing_guard_passed"])
        self.assertEqual(len(seen),22)

    def test_calendar_month_progression_rotates_source_assignments(self):
        prices={"actor_pricing":[{"source":row["name"],
            "pricing_model":"PAY_PER_EVENT"} for row in self.cfg["sources"]]}
        first=select_slot(self.cfg,1,prices,cycle_index=0)
        later=select_slot(self.cfg,1,prices,cycle_index=1)
        self.assertNotEqual([row["query_family"] for row in first["sources"]],
                            [row["query_family"] for row in later["sources"]])

    def test_per_item_price_reduces_records_instead_of_exceeding_cap(self):
        prices={"actor_pricing":[{"source":row["name"],
            "pricing_model":"PRICE_PER_DATASET_ITEM","price_per_unit_usd":0.02}
            for row in self.cfg["sources"]]}
        plan=select_slot(self.cfg,1,prices)
        for source in plan["sources"]:
            self.assertGreaterEqual(source["max_items"],1)
            self.assertLessEqual(source["max_items"]*0.02,source["max_charge_usd"]+1e-9)
            self.assertLessEqual(source["max_items"],30)
        prices["actor_pricing"][0]["price_per_unit_usd"]=5.0
        with self.assertRaisesRegex(ValueError,"no result fits"):
            select_slot(self.cfg,1,prices)

    def test_rolling_snapshot_gate_prevents_any_paid_run(self):
        # Emergency fail-closed setting must still prohibit an Actor launch.
        cfg=deepcopy(self.cfg)
        cfg["rolling_coverage_enabled"]=False
        attempts=[]
        def getter(*args,**kwargs):
            attempts.append(args)
            raise AssertionError("Network should never be invoked")
        with patch.dict("os.environ", {"BA_PAID_REFRESH_APPROVAL":"EXPLICIT_BA_REFRESH_APPROVED"}):
            with self.assertRaisesRegex(RuntimeError,"BA acquisition disabled"):
                run(cfg,"dummy",getter=getter)
        self.assertEqual(attempts,[])

    def test_trial_activation_keeps_limits_exact(self):
        self.assertTrue(self.cfg["rolling_coverage_enabled"])
        self.assertEqual(self.cfg["monthly_limit_usd"],19)
        self.assertEqual(self.cfg["salesforce_reserve_usd"],8)
        self.assertEqual(self.cfg["monthly_ba_allowance_usd"],11)
        self.assertAlmostEqual(self.cfg["max_total_charge_usd"],1.20)
        self.assertEqual(self.cfg["automatic_retries"],0)
        self.assertFalse(self.cfg["wordpress_delivery_enabled"])

    def test_raise_limits_above_authorisation_is_rejected(self):
        cfg=deepcopy(self.cfg)
        cfg["max_total_charge_usd"]=5
        with self.assertRaises(ValueError):
            validate(cfg)
        cfg=deepcopy(self.cfg)
        cfg["sources"][0]["max_items"]=10000
        with self.assertRaises(ValueError):
            validate(cfg)

if __name__=="__main__":
    unittest.main()
