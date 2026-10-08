import unittest
from scripts.classify_cv_library_abort import classify,RUN
class AbortTest(unittest.TestCase):
 def test_charge_signal_and_redaction(self):
  r=classify({"data":{"id":RUN,"status":"ABORTED","statusMessage":"Maximum charge exceeded secret@private.test"}},"")
  self.assertEqual(r["diagnosis_signal"],"charge_cap")
  self.assertNotIn("secret@private.test",str(r))
  self.assertFalse(r["raw_log_included"])
 def test_ambiguity(self):
  r=classify({"data":{"id":RUN,"status":"ABORTED"}},"invalid input; maxTotalChargeUsd")
  self.assertEqual(r["diagnosis_signal"],"ambiguous_or_no_explicit_signal")
