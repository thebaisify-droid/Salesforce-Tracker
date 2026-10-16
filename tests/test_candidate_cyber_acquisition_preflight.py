import copy
import json
import unittest
from pathlib import Path
from scripts.validate_candidate_cyber_acquisition_preflight import validate


class CandidateCyberAcquisitionPreflightTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(Path("config/candidate_cyber_acquisition_preflight.example.json").read_text())

    def test_proposal_is_valid_but_never_authorises_spend(self):
        actual = validate(self.spec)
        self.assertTrue(actual["proposal_valid"], actual["issues"])
        self.assertFalse(actual["safe_to_start_actors"])
        self.assertFalse(actual["paid_acquisition_authorised"])
        self.assertFalse(actual["publication_approved"])
        self.assertEqual(actual["pilot_cost_ceiling_usd"], "0.20")

    def test_enabling_runs_and_schedules_is_rejected(self):
        s = copy.deepcopy(self.spec)
        s.update(enabled=True, actor_runs_allowed=2, scheduled_runs=["daily"])
        self.assertFalse(validate(s)["proposal_valid"])

    def test_budget_and_reserve_cannot_be_relaxed(self):
        s = copy.deepcopy(self.spec)
        s["shared_account_limit_usd"] = 30
        s["protected_salesforce_reserve_usd"] = 0
        s["approved_spend_usd"] = 0.2
        self.assertFalse(validate(s)["proposal_valid"])

    def test_actor_mismatch_and_unsafe_run_cap_rejected(self):
        s = copy.deepcopy(self.spec)
        s["source_searches"][0]["actor_id"] = "wrong"
        s["source_searches"][1]["run_options"]["maxTotalChargeUsd"] = 0.5
        self.assertFalse(validate(s)["proposal_valid"])

    def test_unlimited_results_or_unsupported_input_rejected(self):
        s = copy.deepcopy(self.spec)
        s["source_searches"][0]["input"]["maxResults"] = 0
        s["source_searches"][1]["input"]["includeDescription"] = True
        self.assertFalse(validate(s)["proposal_valid"])

    def test_source_duplicates_rejected(self):
        s = copy.deepcopy(self.spec)
        s["source_searches"][1] = copy.deepcopy(s["source_searches"][0])
        self.assertFalse(validate(s)["proposal_valid"])

    def test_cannot_forge_fresh_usage_confirmation_in_static_spec(self):
        s = copy.deepcopy(self.spec)
        s["current_apify_usage_verified"] = True
        s["account_limit_independently_confirmed"] = True
        s["unreserved_remaining_balance_usd"] = 12.00
        self.assertFalse(validate(s)["proposal_valid"])

    def test_negative_or_non_numeric_costs_fail_closed(self):
        s = copy.deepcopy(self.spec)
        s["source_searches"][0]["run_options"]["maxTotalChargeUsd"] = -0.1
        self.assertFalse(validate(s)["proposal_valid"])
        s = copy.deepcopy(self.spec)
        s["pilot_max_total_charge_usd"] = "not-a-number"
        self.assertFalse(validate(s)["proposal_valid"])
