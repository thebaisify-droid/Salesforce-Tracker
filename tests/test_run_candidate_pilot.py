import unittest
from scripts.run_candidate_pilot import CAPS, task_override, remaining_headroom, run
class PilotTests(unittest.TestCase):
    def test_cap_total(self): self.assertAlmostEqual(sum(CAPS.values()),.50)
    def test_limit(self):
        self.assertAlmostEqual(remaining_headroom({"data":{"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":6.02}}}),12.98)
        with self.assertRaises(ValueError):remaining_headroom({"data":{"limits":{"maxMonthlyUsageUsd":30},"current":{"monthlyUsageUsd":0}}})
    def test_no_approval_no_requests(self):
        with self.assertRaises(ValueError):run(token="dummy",execute=False,approval="",output="/tmp/nonexistent.json")
    def test_saved_task_override_without_mutation(self):
        original={"query":"Salesforce","maxResults":75}
        result=task_override("CV-Library",original)
        self.assertEqual(original["query"],"Salesforce")
        self.assertEqual(result["query"],"business analyst")
        self.assertEqual(result["maxResults"],15)
        self.assertEqual(task_override("Totaljobs",{"keywords":"Salesforce","mode":"jobs","maxListings":100})["keywords"],"business analyst")
    def test_missing_required_mode_rejected(self):
        with self.assertRaises(ValueError):task_override("Totaljobs",{"keywords":"Salesforce"})
if __name__=="__main__":unittest.main()
