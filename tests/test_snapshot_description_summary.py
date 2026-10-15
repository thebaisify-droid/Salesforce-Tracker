from __future__ import annotations
import unittest
from tracker.store import _description_summary

class SnapshotDescriptionSummaryTests(unittest.TestCase):
    def test_headings_are_extracted_from_source_not_fabricated(self):
        source = ("<h3>Responsibilities:</h3><ul><li>Lead architecture workshops</li>"
                  "<li>Design secure integrations</li></ul>"
                  "<h3>Requirements:</h3><p>Proven Salesforce architect experience</p>"
                  "<p>Strong API design background</p>")
        result = _description_summary(source, ["Commerce Cloud", "Order Management"])
        self.assertIn("Lead architecture workshops", result["responsibilities"])
        self.assertIn("Proven Salesforce architect experience", result["requirements"])
        self.assertEqual(result["tools"], ["Commerce Cloud", "Order Management"])
        self.assertIsNone(result["advert_excerpt"])

    def test_missing_description_does_not_invent_job_duties(self):
        result = _description_summary(None, ["Apex", "Agentforce"])
        self.assertIsNone(result["responsibilities"])
        self.assertIsNone(result["requirements"])
        self.assertIsNone(result["advert_excerpt"])
        self.assertEqual(result["tools"], ["Apex", "Agentforce"])

    def test_unstructured_advert_remains_attributed_excerpt(self):
        result = _description_summary("<p>Work alongside platform specialists and teams on CRM projects.</p>", [])
        self.assertIsNone(result["responsibilities"])
        self.assertIsNone(result["requirements"])
        self.assertIn("Work alongside", result["advert_excerpt"])

    def test_long_description_is_bounded_and_html_removed(self):
        source = "<script>alert(1)</script><h2>Responsibilities</h2><p>" + ("Design solutions. " * 100) + "</p>"
        result = _description_summary(source, [])
        self.assertNotIn("alert", str(result))
        self.assertLessEqual(len(result["responsibilities"]), 213)

if __name__ == "__main__":
    unittest.main()
