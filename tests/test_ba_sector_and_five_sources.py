"""BA advertiser-sector assurance and mandatory five-source refresh contract tests."""
import json
import unittest
from pathlib import Path

from scripts.enrich_ba_advertiser_sector import enrich
from scripts.validate_ba_five_source_contract import validate_config, validate_run_receipts

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "business-analysis-tracker"


class TestSectorAndFiveSourceRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((BASE / "data/preview-snapshot.json").read_text(encoding="utf-8"))
        cls.mapping = json.loads((BASE / "config/sector-evidence.json").read_text(encoding="utf-8"))
        cls.five = json.loads((BASE / "config/five_source_refresh.json").read_text(encoding="utf-8"))

    def test_sectors_are_advertiser_only_and_evidence_backed(self):
        report = enrich(self.snapshot, self.mapping)
        qa = report["sector_data_quality"]
        self.assertEqual(qa["total_records"], 36)
        self.assertEqual(qa["advertiser_missing"], 18)
        self.assertEqual(qa["sector_resolved_with_external_organisation_evidence"], 12)
        self.assertEqual(qa["sector_not_specified"], 24)
        self.assertEqual(qa["end_client_sector_resolved"], 0)
        for row in report["records"]:
            self.assertEqual(row["end_client_sector"], "Not specified")
            self.assertEqual(row["sector_display_scope"], "ADVERTISER_SECTOR_NOT_END_CLIENT")
            if row["sector"] != "Not specified":
                self.assertTrue(row["sector_evidence_url"].startswith("https://"))
                self.assertNotEqual(row["sector_basis"], "UNKNOWN_NO_EVIDENCE")
            else:
                self.assertIsNone(row["sector_evidence_url"])
        qa_training = [r for r in report["records"] if r["advertiser"] == "QA Ltd"]
        self.assertEqual(len(qa_training), 2)
        self.assertTrue(all(r["sector"] == "Not specified" for r in qa_training))

    def test_does_not_accept_bad_enrichment_evidence(self):
        invalid = dict(self.mapping)
        invalid["scope"] = "INFER_JOB_TITLE"
        with self.assertRaises(ValueError):
            enrich(self.snapshot, invalid)

    def test_five_source_contract_is_safe_and_disabled(self):
        r = validate_config(self.five)
        self.assertTrue(r["valid"], r["issues"])
        self.assertEqual(r["source_count"], 5)
        self.assertFalse(r["paid_runs_enabled"])

    def test_missing_source_blocks_fresh_publication(self):
        names = ["CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe"]
        records = [{"source": n, "status": "SUCCEEDED", "attempted": True} for n in names]
        self.assertTrue(validate_run_receipts(records, qa_passed=True)["publish_fresh_five_source_snapshot"])
        failed = [dict(r) for r in records]
        failed[-1]["status"] = "FAILED"
        check = validate_run_receipts(failed, qa_passed=True)
        self.assertFalse(check["publish_fresh_five_source_snapshot"])
        self.assertTrue(check["preserve_prior_snapshot"])
        self.assertFalse(validate_run_receipts(records[:4], qa_passed=True)["publish_fresh_five_source_snapshot"])
        self.assertFalse(validate_run_receipts(records, qa_passed=False)["publish_fresh_five_source_snapshot"])


if __name__ == "__main__":
    unittest.main()
