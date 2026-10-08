import unittest
from scripts.validate_task_inspection_report import validate

class InspectionReportSafetyTests(unittest.TestCase):
    def test_minimal_report_passes(self):
        report={"actor_runs_started":0,"task_updates":0,"paid_acquisition_approved":False,
                "tasks":[{"source":"CV-Library","raw_input_included":False,"input_field_names":["query"]},
                         {"source":"Totaljobs","raw_input_included":False,"input_field_names":["keyword"]}]}
        self.assertTrue(validate(report)["passed"])
        report["tasks"][0]["input_field_names"].append("apiToken")
        self.assertFalse(validate(report)["passed"])
    def test_denies_raw_input(self):
        r={"actor_runs_started":0,"task_updates":0,"paid_acquisition_approved":False,
           "tasks":[{"source":"CV-Library","raw_input_included":True},
                    {"source":"Totaljobs","raw_input_included":False}]}
        self.assertFalse(validate(r)["passed"])
if __name__=="__main__": unittest.main()
