import unittest
from unittest.mock import patch
from scripts import ba_jobserve_api_once as recovery

class JobServeApiOnceTests(unittest.TestCase):
    def test_exact_budget_and_reserve(self):
        ok={"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":10.0}}
        self.assertEqual(recovery.billing(ok)["maximum_request_usd"],0.5)
        for usage in (10.51,18.99):
            with self.assertRaises(RuntimeError):
                recovery.billing({"limits":{"maxMonthlyUsageUsd":19},"current":{"monthlyUsageUsd":usage}})
        with self.assertRaises(RuntimeError):
            recovery.billing({"limits":{"maxMonthlyUsageUsd":30},"current":{"monthlyUsageUsd":10}})
    def test_only_ba_inputs_and_one_off_guard(self):
        self.assertEqual(recovery.input_record()["keywords"],["business analyst"])
        self.assertEqual(recovery.input_record()["maxResults"],20)
        self.assertEqual(recovery.CAP_USD,0.50)
        with patch.dict("os.environ",{"BA_JOBSERVE_APPROVAL":"", "GITHUB_RUN_ATTEMPT":"1"}):
            with self.assertRaises(SystemExit):
                recovery.main()
        with patch.dict("os.environ",{"BA_JOBSERVE_APPROVAL":recovery.APPROVAL,
                                       "GITHUB_RUN_ATTEMPT":"2","GITHUB_EVENT_NAME":"push",
                                       "GITHUB_REF":"refs/heads/main"}):
            with self.assertRaises(SystemExit):
                recovery.main()
if __name__=="__main__":
    unittest.main()
