import unittest
from scripts.cyber_apify_readonly_preflight import assess

def fixture(minimum=0.1, usage=6.94):
    limits = {"data":{"limits":{"maxMonthlyUsageUsd":19},
                      "current":{"monthlyUsageUsd":usage}}}
    monthly = {"data":{"totalUsageCreditsUsdAfterVolumeDiscount":usage}}
    actors = {}
    for name, actor_id in [("Indeed UK","BkcKc9frZp43LeRM7"),
                           ("JobServe","iEeTOwSjZDvAshw7Y")]:
        actors[name] = {"data":{"id":actor_id,"pricingInfos":[{
            "pricingModel":"PAY_PER_EVENT","startedAt":"2026-09-01T00:00:00Z",
            "minimalMaxTotalChargeUsd":minimum}]}}
    return limits, monthly, actors

class PreflightTests(unittest.TestCase):
    def test_verified_inputs_pass_without_authorising_paid_calls(self):
        r = assess(*fixture())
        self.assertTrue(r["read_only_checks_pass"])
        self.assertFalse(r["paid_execution_authorised"])
        self.assertEqual(r["paid_runs_started"], 0)
        self.assertEqual(r["unreserved_headroom_usd"], 4.06)
    def test_insufficient_reserve_blocks(self):
        r = assess(*fixture(usage=11.0))
        self.assertIn("protected_salesforce_reserve_insufficient",r["blocked_reasons"])
    def test_actor_minimum_above_cap_blocks(self):
        self.assertFalse(assess(*fixture(minimum=0.4))["read_only_checks_pass"])
    def test_missing_actor_floor_blocks(self):
        l,m,a = fixture()
        del a["Indeed UK"]["data"]["pricingInfos"][0]["minimalMaxTotalChargeUsd"]
        self.assertFalse(assess(l,m,a)["read_only_checks_pass"])

if __name__=="__main__": unittest.main()
