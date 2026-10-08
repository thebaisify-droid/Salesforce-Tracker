import unittest
from scripts.audit_second_cv_failure import audit,classify
class SecondFailureAuditTests(unittest.TestCase):
 def test_recognises_charge_limit(self):
  item={"id":"abc","startedAt":"2026-10-08T16:35:23Z"}
  details={"abc":{"data":{"status":"ABORTED","finishedAt":"2026-10-08T16:37:10Z","usageTotalUsd":.3,"options":{"maxTotalChargeUsd":.3},"statusMessage":"Maximum charge limit exceeded token SECRET"}}}
  result=audit([item],details)
  self.assertEqual(result["matching_runs"][0]["reason_signals"],["MAX_TOTAL_CHARGE"])
  self.assertNotIn("SECRET",str(result))
 def test_unmatched_timestamp(self):
  self.assertEqual(audit([{"id":"old","startedAt":"2026-10-08T15:32:00Z"}],{})["count"],0)
 def test_generic_abort_not_assumed_manual(self):
  self.assertEqual(classify("Run aborted"),[])
