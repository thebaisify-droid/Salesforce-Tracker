import unittest
from scripts.audit_failed_candidate_pilot import summarise
class FailedPilotAuditTests(unittest.TestCase):
    def test_window_and_no_false_attribution(self):
        r=summarise({"data":{"items":[
          {"id":"run1","startedAt":"2026-10-08T15:32:34Z","status":"FAILED","usageTotalUsd":0.1},
          {"id":"run2","startedAt":"2026-10-08T12:00:00Z","status":"SUCCEEDED"}]}})
        self.assertEqual(r["run_count"],1)
        self.assertEqual(r["matching_runs"][0]["usage_total_usd"],.1)
        self.assertFalse(r["actual_billing_attributed"])
        self.assertEqual(r["actor_runs_started"],0)
    def test_missing_items_fails_closed(self):
        with self.assertRaises(ValueError):summarise({})
if __name__=="__main__":unittest.main()
