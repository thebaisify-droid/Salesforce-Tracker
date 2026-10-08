import unittest
from unittest.mock import patch
from scripts import run_candidate_pilot as pilot

class AbortedPilotSafetyTests(unittest.TestCase):
    def test_pilot_disabled_even_with_previous_approval(self):
        with patch.object(pilot,"request_json") as request:
            with self.assertRaisesRegex(RuntimeError,"Pilot disabled"):
                pilot.run(token="dummy",execute=True,approval="RUN_CAPPED_PILOT",output="unused.json")
            request.assert_not_called()
    def test_original_charge_cap_not_silently_increased(self):
        self.assertEqual(pilot.CAPS["CV-Library"],0.10)
        self.assertFalse(pilot.PAID_PILOT_ENABLED)

if __name__=="__main__": unittest.main()
