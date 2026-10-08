import unittest
from scripts.validate_candidate_market import evaluate

class CandidateAssuranceTests(unittest.TestCase):
    def test_perfect_labelling(self):
        fixtures=[{"title":"SOC Analyst","expected_included":True,"expected_family":"Security Operations / SOC"},
                  {"title":"Data Analyst","expected_included":True,"expected_family":"Data Analysis"},
                  {"title":"Security Guard","expected_included":False}]
        report=evaluate(fixtures)
        self.assertTrue(report["passed"])
        self.assertEqual(report["precision"],1)
        self.assertEqual(report["recall"],1)
        self.assertFalse(report["real_world_accuracy_validated"])
        self.assertFalse(report["publication_approved"])
    def test_false_positive_fails(self):
        report=evaluate([{"title":"Product Manager","expected_included":False}],minimum_precision=.9)
        self.assertFalse(report["passed"])
        self.assertEqual(report["counts"]["fp"],1)
    def test_false_negative_fails(self):
        report=evaluate([{"title":"Cloud Security Engineer","expected_included":True,
                          "expected_family":"IT Security"}])
        self.assertFalse(report["passed"])
        self.assertEqual(report["counts"]["fn"],1)
    def test_bad_fixture_fails_closed(self):
        with self.assertRaises(ValueError):
            evaluate([{"title":"SOC Analyst","expected_included":True,"expected_family":"Invented"}])

if __name__=="__main__":
    unittest.main()
