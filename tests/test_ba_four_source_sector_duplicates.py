"""Offline checks for BA sector evidence and duplicate discipline."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from scripts.enrich_ba_four_successful_sources import enrich
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"business-analysis-tracker/evidence/ba-four-successful-boards-20261015-qa.json"
class FourBoardEnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=json.loads(SOURCE.read_text(encoding="utf8"))
    def test_evidence_and_no_publication(self):
        data=enrich(self.baseline)
        qa=data["data_quality"]
        self.assertEqual(qa["sector_with_specific_advert_evidence"],6)
        self.assertEqual(qa["sector_unknown"],27)
        self.assertEqual(qa["sector_requires_review"],1)
        self.assertEqual(qa["possible_cross_board_duplicate_pairs"],1)
        self.assertEqual(qa["confirmed_cross_board_duplicate_pairs"],0)
        self.assertFalse(data["publication_approved"])
        self.assertEqual(len(data["records"]),33)
        self.assertEqual(sum(bool(r["possible_duplicate_ids"]) for r in data["records"]),2)
        self.assertTrue(all(r["source_run_id"] for r in data["records"]))
        r={x["id"]:x for x in data["records"]}
        self.assertEqual(r["pilot-reeduk-22"]["end_client_sector"],"Financial Services")
        self.assertEqual(r["pilot-totaljobs-13"]["advertiser_sector"],"Financial Services")
        self.assertEqual(r["pilot-reeduk-26"]["sector_display"],"Not specified")
        self.assertTrue(r["pilot-reeduk-26"]["sector_review_required"])
    def test_evidence_cannot_detach_from_source(self):
        bad=deepcopy(self.baseline)
        for x in bad["records"]:
            if x["id"]=="pilot-reeduk-22":
                x["description_summary"]="Description unavailable."
        with self.assertRaises(ValueError):
            enrich(bad)
    def test_cross_board_candidate_not_merged(self):
        data=enrich(self.baseline)
        ids={r["id"] for r in data["records"]}
        self.assertTrue({"pilot-cvlibrary-8","pilot-totaljobs-16"}.issubset(ids))
        self.assertEqual(len(ids),33)
if __name__=="__main__":
    unittest.main()
