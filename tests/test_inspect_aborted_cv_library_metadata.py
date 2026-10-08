import unittest
from scripts.inspect_aborted_cv_library_metadata import RUN_ID, summarise

class RunMetadataTests(unittest.TestCase):
    def test_readonly_summary(self):
        d={"data":{"id":RUN_ID,"status":"ABORTED","usageTotalUsd":0.1006,
                   "statusMessage":"private unexported error",
                   "options":{"maxTotalChargeUsd":0.10}}}
        report=summarise(d)
        self.assertEqual(report["status"],"ABORTED")
        self.assertTrue(report["read_only"])
        self.assertNotIn("private unexported error",str(report))
        self.assertFalse(report["cause_confirmed"])
    def test_wrong_run(self):
        with self.assertRaises(ValueError):
            summarise({"data":{"id":"wrong"}})
