"""Offline tests: no Apify spending, REST publication or dispatch."""
import unittest
from datetime import datetime, timezone, timedelta
from scripts.shared_phase4_readiness import assess, account_readiness


class Phase4Readiness(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 21, 16, 30, tzinfo=timezone.utc)

    def test_planned_22_family_slots_are_not_verified_vacancies(self):
        report = assess(now=self.now)
        self.assertEqual(report["status"], "BLOCKED_NO_LIVE_ACTIVATION")
        self.assertEqual(report["ba_rotation"]["defined_families"], 22)
        self.assertEqual(report["ba_rotation"]["unique_search_opportunities_in_first_five_slots"], 22)
        self.assertFalse(report["ba_rotation"]["actual_22_family_vacancy_coverage_evidenced"])
        self.assertFalse(report["paid_acquisition_approved"])
        self.assertFalse(report["wordpress_publication_approved"])
        self.assertEqual(report["verified_avoided_charge_usd"], 0)
        self.assertEqual(report["paid_actors_started"], 0)
        self.assertEqual(report["wordpress_requests"], 0)

    def test_actual_25_usd_account_observation_blocks(self):
        value = {"account_limit_usd": 25,
                 "account_usage_usd": 10.866026027112321,
                 "observed_at": "2026-10-20T07:46:01Z"}
        result = account_readiness(value, now=self.now)
        self.assertEqual(result["reason"], "ACCOUNT_LIMIT_MISMATCH_NOT_19")
        self.assertIn(result["reason"], assess(now=self.now, account=value)["blockers"])

    def test_fresh_19_dollar_json_alone_is_not_authenticated(self):
        data = {"account_limit_usd": 19, "account_usage_usd": 5,
                "observed_at": self.now.isoformat()}
        self.assertEqual(account_readiness(data, now=self.now)["reason"],
                         "SUPPLIED_JSON_CANNOT_AUTHENTICATE_ACCOUNT")

    def test_invalid_stale_future_and_missing_billing_fails_closed(self):
        for value in (None,
                      {"account_limit_usd": 19, "account_usage_usd": -1, "observed_at": self.now.isoformat()},
                      {"account_limit_usd": 19, "account_usage_usd": 3,
                       "observed_at": (self.now - timedelta(days=1)).isoformat()},
                      {"account_limit_usd": 19, "account_usage_usd": 3,
                       "observed_at": (self.now + timedelta(minutes=1)).isoformat()},
                      {"account_limit_usd": 19, "account_usage_usd": 3, "observed_at": "bad"}):
            with self.subTest(value=value):
                self.assertFalse(account_readiness(value, now=self.now)["verified"])

    def test_two_independent_receiver_contracts(self):
        receivers = assess(now=self.now)["receivers"]
        self.assertEqual(receivers["salesforce"]["path"],
                         "/wp-json/salesforce-tracker/v1/snapshot")
        self.assertEqual(receivers["business_analysis"]["rest_route"],
                         "rest_route=/business-analysis-tracker/v1/snapshot")
        self.assertFalse(receivers["authenticated_ba_delivery_proven_now"])


if __name__ == "__main__":
    unittest.main()
