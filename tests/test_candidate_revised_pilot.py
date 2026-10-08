import unittest
from unittest.mock import patch
from scripts import run_candidate_pilot_v2 as pilot
class RevisedPilotTests(unittest.TestCase):
    def test_revised_caps_and_limit(self):
        self.assertEqual(pilot.CAPS,{"CV-Library":.30,"Totaljobs":.20,"Indeed UK":.15,"JobServe":.15})
        self.assertAlmostEqual(sum(pilot.CAPS.values()),.80)
        self.assertEqual(pilot.LIMIT,10)
        self.assertEqual(pilot.SAFE_RESERVE_FOR_EXISTING_TRACKER,8)
    def test_old_authorisation_invalid(self):
        with patch.object(pilot,"request_json") as get:
            with self.assertRaises(ValueError):
                pilot.run(token="fake",execute=True,approval="RUN_CAPPED_PILOT",output="unused.json")
            get.assert_not_called()
    def test_new_approval_requires_explicit_execute(self):
        with patch.object(pilot,"request_json") as get:
            with self.assertRaises(ValueError):
                pilot.run(token="fake",execute=False,approval="AUTHORISE_REVISED_080_PILOT",output="unused.json")
            get.assert_not_called()
if __name__=="__main__":unittest.main()
