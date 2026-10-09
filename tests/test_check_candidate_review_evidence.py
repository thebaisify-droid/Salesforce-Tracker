import unittest
from scripts.check_candidate_review_evidence import assess
class EvidenceCompletenessTests(unittest.TestCase):
    def test_blank_handoff_is_not_approval(self):
        from scripts.export_candidate_beta_review import export_review
        import json
        from pathlib import Path
        snapshot=json.loads(Path("candidate-beta/data/pilot-snapshot.json").read_text())
        report=assess(export_review(snapshot))
        self.assertEqual(report["review_rows"],30)
        self.assertEqual(report["documented_complete_rows"],0)
        self.assertFalse(report["publication_approved"])
        self.assertEqual(report["gaps"]["missing_independent_evidence_url"],30)
    def test_complete_self_report_still_cannot_publish(self):
        from scripts.check_candidate_review_evidence import REQUIRED
        row={field:"yes" for field in REQUIRED}
        row.update(id="1",independent_evidence_url="https://example.org/evidence",reviewer="human",reviewed_at="2026-10-09")
        report=assess([row])
        self.assertEqual(report["documented_complete_rows"],1)
        self.assertFalse(report["publication_approved"])
if __name__=="__main__":
    unittest.main()
