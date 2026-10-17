"""No-network tests for JobServe's documented whole-page result overshoot."""
import unittest
from scripts.ba_controlled_refresh import verified_dataset_count

class TestJobServeOvershoot(unittest.TestCase):
    def test_jobserve_46_returned_on_request_for_30_is_allowed(self):
        self.assertEqual(verified_dataset_count({"itemCount": 46}, 30, "JobServe"), 46)

    def test_other_sources_remain_strict(self):
        with self.assertRaises(ValueError):
            verified_dataset_count({"itemCount": 46}, 30, "Indeed UK")

    def test_large_or_invalid_jobserve_result_fails_closed(self):
        for count in (101, -1, None, "46"):
            with self.subTest(count=count), self.assertRaises(ValueError):
                verified_dataset_count({"itemCount": count}, 30, "JobServe")

if __name__ == "__main__":
    unittest.main()
