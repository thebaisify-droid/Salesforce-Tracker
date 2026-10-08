import unittest
from unittest.mock import patch
from scripts.apify_budget_readonly_preflight import API, inspect, summarise

def data(limit,usage):
    return {"data":{"limits":{"maxMonthlyUsageUsd":limit},
                    "current":{"monthlyUsageUsd":usage}}}

class ApifyReadOnlyBudgetTests(unittest.TestCase):
    def test_within_limit_does_not_authorise_pilot(self):
        r=summarise(data(19,10))
        self.assertTrue(r["account_headroom_sufficient"])
        self.assertFalse(r["pilot_authorised"])
        self.assertEqual(r["actor_runs_started"],0)
    def test_rejects_higher_cap_or_low_headroom(self):
        self.assertFalse(summarise(data(30,2))["account_headroom_sufficient"])
        self.assertFalse(summarise(data(19,18.8))["account_headroom_sufficient"])
    def test_missing_data_fails_closed(self):
        with self.assertRaises(ValueError):
            summarise({"data":{}})
    def test_read_only_http(self):
        with patch("scripts.apify_budget_readonly_preflight.urlopen") as opener:
            resp=opener.return_value.__enter__.return_value
            with patch("scripts.apify_budget_readonly_preflight.json.load",return_value=data(19,2)):
                self.assertTrue(inspect("mock-only")["account_headroom_sufficient"])
        request=opener.call_args.args[0]
        self.assertEqual(request.get_method(),"GET")
        self.assertEqual(request.full_url,API)
if __name__=="__main__": unittest.main()
