import unittest
from scripts.inspect_cv_library_abort_reason import evaluate,RUN
class AbortReasonTests(unittest.TestCase):
 def test_explicit_cap(self):
  x=evaluate({"data":{"id":RUN,"status":"ABORTED","statusMessage":"Maximum charge limit reached; private-key=abc"}})
  self.assertEqual(x["unambiguous_status_reason"],"MAX_TOTAL_CHARGE")
  self.assertNotIn("private-key",str(x))
 def test_generic_abort_does_not_mean_user(self):
  x=evaluate({"data":{"id":RUN,"status":"ABORTED","statusMessage":"Actor run aborted"}})
  self.assertIsNone(x["unambiguous_status_reason"])
  self.assertFalse(x["attribution_confirmed"])
