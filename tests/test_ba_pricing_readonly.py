"""No-charge pricing preflight requires live account limits and five Actor metadata responses."""
import json,unittest
from scripts.ba_controlled_refresh import CONFIG
from scripts.ba_pricing_readonly import check, validate_cost_models

class BAReadOnlyPriceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.config=json.loads(CONFIG.read_text(encoding="utf8"))
    def test_all_five_checked_without_post(self):
        checked=[]
        def get(path,token):
            checked.append(path)
            if path=="users/me/limits":
                return {"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":8.9}}
            return {"pricingInfos":[{"pricingModel":"PRICE_PER_DATASET_ITEM",
                       "pricePerUnitUsd":0.003,"unitName":"item"}]}
        result=check(self.config,"token",reader=get)
        self.assertEqual(result["account_limit_usd"],19)
        self.assertEqual(result["available_after_salesforce_reserve_usd"],2.1)
        self.assertEqual(len(result["actor_pricing"]),5)
        self.assertEqual(len(checked),6)
        self.assertEqual(result["actor_runs_started"],0)
        self.assertEqual(result["wordpress_requests"],0)
    def test_price_safety_rejects_uncapped_and_unknown_sources(self):
        template={"account_limit_usd":19,"actor_pricing":[
          {"source":x["name"],"pricing_model":"PRICE_PER_DATASET_ITEM",
           "price_per_unit_usd":0.01} for x in self.config["sources"]]}
        result=validate_cost_models(template,self.config)
        self.assertTrue(result["pricing_guard_passed"],result["issues"])
        template["actor_pricing"][2]["price_per_unit_usd"]=0.5
        self.assertFalse(validate_cost_models(template,self.config)["pricing_guard_passed"])
        template["actor_pricing"][2]["pricing_model"]=None
        self.assertFalse(validate_cost_models(template,self.config)["pricing_guard_passed"])
        template["actor_pricing"][2]["pricing_model"]="PAY_PER_EVENT"
        self.assertTrue(validate_cost_models(template,self.config)["pricing_guard_passed"])

    def test_actor_minimum_and_compute_charges_are_bounded(self):
        report={"account_limit_usd":19,"actor_pricing":[
            {"source":x["name"],"pricing_model":"PAY_PER_EVENT",
             "minimal_max_total_charge_usd":0.05,
             "platform_usage_paid_by_user":False} for x in self.config["sources"]]}
        self.assertTrue(validate_cost_models(report,self.config)["pricing_guard_passed"])
        report["actor_pricing"][-1]["minimal_max_total_charge_usd"]=0.60
        failure=validate_cost_models(report,self.config)
        self.assertFalse(failure["pricing_guard_passed"])
        self.assertIn("JobServe:ACTOR_MINIMUM_EXCEEDS_CAP",failure["issues"])
        report["actor_pricing"][-1]["minimal_max_total_charge_usd"]=0.05
        report["actor_pricing"][-1]["platform_usage_paid_by_user"]=True
        self.assertFalse(validate_cost_models(report,self.config)["pricing_guard_passed"])

    def test_changed_account_limit_fails_closed(self):
        def get(path,token):
            return {"limits":{"maxMonthlyUsageUsd":30},"current":{"monthlyUsageUsd":8}}
        with self.assertRaises(RuntimeError):
            check(self.config,"token",reader=get)
    def test_missing_token_fails_closed(self):
        with self.assertRaises(RuntimeError):
            check(self.config,"")
if __name__=="__main__":
    unittest.main()
