"""IR35 data quality regression: full Apify payload must beat short excerpts.

No Apify run, pricing requests, WordPress writes or network traffic.
"""
from __future__ import annotations
import unittest
from scripts.ba_stage_five_source_data import (
    explicit_ir35_status, excerpt_with_ir35, cleaned_excerpt
)


class TestBAFullTextIR35(unittest.TestCase):
    def test_jobserve_outside_ir35_after_260_characters(self):
        # Reproduces shape and wording of completed JobServe dataset row hGfqg.
        row = {
            "title": "Process Business Analyst - London Market Insurance",
            "url": "https://www.jobserve.com/gb/en/hGfqg",
            "description": "Process Business Analyst - London Market Insurance. "
                           + "Underwriting process documentation and analysis. " * 15
                           + "This is an Outside IR35 Contract opportunity with an initial 6-month term.",
            "rate": None, "salary": None, "jobType": "Contract",
        }
        excerpt = cleaned_excerpt(row)
        self.assertLessEqual(len(excerpt), 260)
        self.assertNotIn("Outside IR35", excerpt)
        self.assertEqual(explicit_ir35_status(row), "Outside IR35")
        status, summary = excerpt_with_ir35(row, excerpt)
        self.assertEqual(status, "Outside IR35")
        self.assertTrue(summary.startswith("IR35: Outside IR35. "))
        self.assertLessEqual(len(summary), 260)
        self.assertIsNone(row["rate"])
        self.assertIsNone(row["salary"])

    def test_inside_ir35_and_existing_excerpt_are_not_duplicated(self):
        row = {"description": "£450 per day. Inside IR35. Contract."}
        self.assertEqual(explicit_ir35_status(row), "Inside IR35")
        status, summary = excerpt_with_ir35(row, cleaned_excerpt(row))
        self.assertEqual(status, "Inside IR35")
        self.assertEqual(summary, cleaned_excerpt(row))

    def test_ambiguous_ir35_only_and_opposite_wording_do_not_infer(self):
        for text in ("Knowledge of IR35", "Contract through umbrella",
                     "Inside IR35 or Outside IR35 depending on assessment"):
            with self.subTest(text=text):
                row = {"description": text}
                self.assertEqual(explicit_ir35_status(row), "Not stated")
                status, summary = excerpt_with_ir35(row, cleaned_excerpt(row))
                self.assertEqual(status, "Not stated")
                self.assertEqual(summary, cleaned_excerpt(row))

    def test_html_only_full_description_supported(self):
        row = {"descriptionHtml": "<p>Engagement: <strong>Outside IR35</strong></p>"}
        self.assertEqual(explicit_ir35_status(row), "Outside IR35")

    def test_not_stated_without_source_evidence(self):
        row = {"description": "Process Business Analyst working with stakeholders."}
        self.assertEqual(explicit_ir35_status(row), "Not stated")
        self.assertEqual(excerpt_with_ir35(row, cleaned_excerpt(row))[0], "Not stated")


if __name__ == "__main__":
    unittest.main()
