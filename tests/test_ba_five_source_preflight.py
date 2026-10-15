"""Business Analysis actor input preflight: no paid calls or external requests."""
from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.ba_five_source_preflight import check_account, validate_plan

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "business-analysis-tracker" / "config"


class TestBAFiveSourcePreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((P / "actor_search_plan.json").read_text(encoding="utf-8"))
        cls.contract = json.loads((P / "five_source_refresh.json").read_text(encoding="utf-8"))

    def test_exactly_five_distinct_sources_and_zero_spend(self):
        report = validate_plan(self.plan, self.contract)
        self.assertTrue(report["valid"], report["problems"])
        self.assertEqual(report["advertisements_requested_maximum"], 50)
        self.assertEqual(len(report["actors"]), 5)
        self.assertFalse(report["paid_acquisition_enabled"])
        self.assertEqual(report["actor_runs_started"], 0)

    def test_salesforce_query_or_source_swap_rejected(self):
        altered = deepcopy(self.plan)
        altered["source_profiles"][0]["input"]["query"] = "Salesforce"
        self.assertFalse(validate_plan(altered, self.contract)["valid"])
        altered = deepcopy(self.plan)
        altered["source_profiles"][0]["actor"] = "wildorigins/indeed-jobs"
        self.assertFalse(validate_plan(altered, self.contract)["valid"])

    def test_unexpected_field_uncapped_and_enabled_are_rejected(self):
        altered = deepcopy(self.plan)
        altered["source_profiles"][0]["input"]["maxResults"] = 0
        self.assertFalse(validate_plan(altered, self.contract)["valid"])
        altered = deepcopy(self.plan)
        altered["source_profiles"][0]["input"]["webhookUrl"] = "https://example.com"
        self.assertFalse(validate_plan(altered, self.contract)["valid"])
        altered = deepcopy(self.plan)
        altered["execution_enabled"] = True
        self.assertFalse(validate_plan(altered, self.contract)["valid"])

    def test_account_headroom_and_reserve(self):
        payload = {"data": {"limits": {"maxMonthlyUsageUsd": 19},
                            "current": {"monthlyUsageUsd": 6.8}}}
        result = check_account(payload, proposed_cap_usd=.9)
        self.assertEqual(result["account_remaining_usd"], 12.2)
        self.assertEqual(result["remaining_after_salesforce_reserve_usd"], 4.2)
        self.assertTrue(result["sufficient_for_proposed_cap"])
        payload["data"]["current"]["monthlyUsageUsd"] = 10.8
        self.assertFalse(check_account(payload, proposed_cap_usd=.9)["sufficient_for_proposed_cap"])
        payload["data"]["limits"]["maxMonthlyUsageUsd"] = 30
        with self.assertRaises(ValueError):
            check_account(payload)
        with self.assertRaises(ValueError):
            check_account({"data": {}})


if __name__ == "__main__":
    unittest.main()
