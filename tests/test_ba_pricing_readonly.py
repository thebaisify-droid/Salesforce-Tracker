"""No-charge pricing preflight requires live account limits and five Actor metadata responses."""
import json,unittest
from scripts.ba_controlled_refresh import CONFIG
from scripts.ba_pricing_readonly import check

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
