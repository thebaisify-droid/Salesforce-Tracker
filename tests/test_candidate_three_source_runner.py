import unittest
from unittest.mock import patch
from scripts import run_candidate_three_source_pilot as pilot
class ThreeSourcePilotTests(unittest.TestCase):
 def test_scope_and_caps(self):
  self.assertEqual(pilot.CAPS,{"Totaljobs":0.20,"Indeed UK":0.15,"JobServe":0.15})
  self.assertAlmostEqual(sum(pilot.CAPS.values()),0.50)
  self.assertNotIn("CV-Library",pilot.CAPS)
  self.assertEqual(pilot.LIMIT,10)
  self.assertEqual(pilot.SAFE_RESERVE_FOR_EXISTING_TRACKER,8)
 def test_refuses_previous_approval(self):
  with patch.object(pilot,"request_json") as request:
   with self.assertRaises(ValueError):
    pilot.run(token="test",execute=True,approval="AUTHORISE_REVISED_080_PILOT",output="no.json")
   request.assert_not_called()
 def test_requires_execute(self):
  with patch.object(pilot,"request_json") as request:
   with self.assertRaises(ValueError):
    pilot.run(token="test",execute=False,approval="AUTHORISE_THREE_SOURCE_050_PILOT",output="no.json")
   request.assert_not_called()
if __name__=="__main__":unittest.main()
