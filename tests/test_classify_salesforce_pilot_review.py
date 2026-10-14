import unittest
from scripts.classify_salesforce_pilot_review import category, shortlist

class PilotReviewTests(unittest.TestCase):
    def test_core_title(self):
        self.assertEqual(category({"title":"Salesforce Solution Architect"}),
                         "CORE_CANDIDATE")
    def test_employer_salesforce_not_sufficient(self):
        self.assertEqual(category({"title":"Regional Vice President",
                                   "employer":"Salesforce",
                                   "text_salesforce_signal":False}),
                         "IRRELEVANT_OR_INSUFFICIENT_EVIDENCE")
    def test_ambiguous_crm_needs_review(self):
        self.assertEqual(category({"title":"CRM Business Analyst",
                                   "text_salesforce_signal":True}),
                         "ADJACENT_REVIEW")
    def test_never_publish_and_duplicate_flag(self):
        rows=[{"title":"Salesforce Engineer","employer":"Example Ltd",
               "source":"Reed UK","url":"https://www.reed.co.uk/job/1"},
              {"title":"Salesforce Engineer","employer":"Example Limited",
               "source":"JobServe","url":"https://www.jobserve.com/job/2"}]
        report, output=shortlist(rows)
        self.assertFalse(report["publication_allowed"])
        self.assertEqual(report["verified_open_count"],0)
        self.assertTrue(all(not x["publication_allowed"] for x in output))
        self.assertTrue(all(x["availability"]=="NOT_VERIFIED_OPEN" for x in output))
        self.assertEqual(report["core_nonduplicate_linked_candidates"],0)
