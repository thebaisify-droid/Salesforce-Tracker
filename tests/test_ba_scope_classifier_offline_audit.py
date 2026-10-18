"""Read-only safeguards for role classifier candidate."""
import unittest
from scripts.ba_scope_classifier_offline_audit import assess,audit
class TestReviewOnlyCandidate(unittest.TestCase):
    def test_all_adjudications_are_considered(self):
        r=audit()
        import json
        print('BA_CLASSIFIER_AUDIT',json.dumps(r,sort_keys=True))
        self.assertEqual(r["total"],161)
        self.assertEqual(sum(r["metrics"].values()),161)
        self.assertEqual(r["paid_actors"],0)
        self.assertEqual(r["wordpress_requests"],0)
    def test_new_patterns_never_automatically_admit(self):
        for title in ("Head of Technology - SIP / IT","Enterprise Architect",
                      "Information Security Manager","Digital Analyst - Tech, Risk & Governance"):
            outcome=assess(title)
            self.assertIn(outcome["status"],("AUTO_INCLUDE","REVIEW"))
            if outcome["basis"]=="PROPOSED_REVIEW_ONLY":
                self.assertEqual(outcome["status"],"REVIEW")
    def test_ambiguous_titles_require_review(self):
        for title in ("Sales Manager","Pensions Technical Manager","Lead Engineer",
                      "Implementation Manager"):
            self.assertNotEqual(assess(title)["basis"],"PROPOSED_AUTO")
if __name__=="__main__":
    unittest.main()
