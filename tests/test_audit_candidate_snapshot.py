import json
import unittest
from pathlib import Path
from scripts.audit_candidate_snapshot import audit

class CandidateSnapshotAuditTests(unittest.TestCase):
    def test_historical_sample_reports_no_go(self):
        snapshot=json.loads(Path("candidate-beta/data/pilot-snapshot.json").read_text())
        report=audit(snapshot)
        self.assertEqual(report["release_status"],"NO_GO")
        self.assertEqual(report["records"],30)
        self.assertEqual(report["publication_ready_records"],0)
        self.assertEqual(report["records_without_provisional_family"],23)
        self.assertEqual(sum(report["provisional_family_counts"].values()),7)
        self.assertEqual(len(report["provisional_family_counts"]),5)
        self.assertEqual(report["unique_urls"],30)
        self.assertIn("representative_coverage_not_verified",report["reasons"])
    def test_unexpected_publication_flag_fails_closed(self):
        snapshot={"records":[{"id":"a","url":"https://example.test","source":"A","verification":"SOURCE_ONLY_UNVERIFIED","provisional_family":None,"publication_ready":True}],
                  "publication_approved":True,"verified_representative_coverage":False}
        result=audit(snapshot)
        self.assertIn("unexpected_publication_ready_record",result["reasons"])
        self.assertIn("snapshot_publication_flag_unsafe",result["reasons"])

if __name__=="__main__":
    unittest.main()
