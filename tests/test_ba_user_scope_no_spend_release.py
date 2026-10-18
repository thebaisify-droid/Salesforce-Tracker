"""Approved 16 October BA role-scope decisions and metadata evidence only.

This release does not enable paid acquisition, change receiver code or publish.
"""
from collections import Counter
import json
import unittest
from scripts.ba_stage_five_source_data import (
    user_excluded_adverts, FINAL_SCOPE_DECISIONS, working, stage, MAPPING
)

class BAReviewedSafeRelease(unittest.TestCase):
    def test_exact_final_user_scope_decisions(self):
        d=json.loads(FINAL_SCOPE_DECISIONS.read_text(encoding="utf8"))
        self.assertEqual(len(d["decisions"]),161)
        self.assertEqual(Counter(x["decision"] for x in d["decisions"]),
                         {"KEEP":124,"EXCLUDE":37})
        self.assertEqual(len(user_excluded_adverts()),37)
        self.assertEqual(len({(x["source"],x["original_advert_url"]) for x in d["decisions"]}),161)
        self.assertTrue(d["never_block_by_title_alone"])
    def test_work_mode_evidence(self):
        self.assertEqual(working({"description":"Hybrid working, 2 days in office"}),"Hybrid")
        self.assertEqual(working({"description":"Hybrid cloud architecture"}),"Not specified")
        self.assertEqual(working({"description":"remote working available"}),"Remote")
        self.assertEqual(working({"description":"office attendance twice weekly"}),"Not specified")
        self.assertEqual(working({"description":"Fully on-site"}),"On-site")
    def test_official_advertiser_sectors(self):
        from scripts.ba_stage_five_source_data import sector_catalog
        mapping=json.loads(MAPPING.read_text(encoding="utf8"))
        data=sector_catalog(mapping)
        self.assertGreaterEqual(len(data),18)
        self.assertEqual(data["bristol city council"]["sector"],"Public Sector")
        self.assertEqual(data["evri"]["sector"],"Transport & Logistics")
        self.assertNotIn("hays recruitment",data)

if __name__=="__main__":
    unittest.main()
