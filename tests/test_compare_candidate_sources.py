import unittest
from scripts.compare_candidate_sources import analyse

class SourceQualityTests(unittest.TestCase):
    def test_core_order_and_no_false_acquisition(self):
        rows={"CV-Library":[{"title":"Data Analyst","url":"https://example.org/a","company":"X","posted_at":"2026-10-08"}],
              "Indeed UK":[{"title":"Data Analyst","url":"https://example.org/a?utm_source=indeed"},
                           {"title":"SOC Analyst","url":"https://example.org/b"}],
              "JobServe":[{"title":"Cyber Security Analyst","url":"https://example.org/c"}],
              "Reed":[{"title":"Security Guard","url":"https://example.org/d"}]}
        r=analyse(rows)
        self.assertEqual([x["source"] for x in r["sources"]],
                         ["CV-Library","Totaljobs","Indeed UK","JobServe","Reed"])
        self.assertEqual(r["sources"][2]["relevant_unique_urls"],2)
        self.assertEqual(r["sources"][2]["incremental_unique_urls_in_order"],1)
        self.assertEqual(r["sources"][4]["relevant_unique_urls"],0)
        self.assertFalse(r["acquisition_enabled"])
        self.assertFalse(r["publication_approved"])
    def test_malformed_source_fails(self):
        with self.assertRaises(ValueError):
            analyse({"JobServe":{"records":[]}})

if __name__=="__main__":
    unittest.main()
