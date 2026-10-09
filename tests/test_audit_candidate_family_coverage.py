import json
import unittest
from pathlib import Path
from scripts.audit_candidate_family_coverage import assess
class CandidateCoverageTests(unittest.TestCase):
    def test_historical_sample_does_not_count_as_verified_coverage(self):
        data=json.loads(Path("candidate-beta/data/pilot-snapshot.json").read_text())
        taxonomy=json.loads(Path("config/business_product_delivery_security_taxonomy_v1.0.json").read_text())
        report=assess(data,taxonomy)
        self.assertEqual(report["taxonomy_families"],22)
        self.assertEqual(report["provisionally_represented"],5)
        self.assertEqual(report["unrepresented"],17)
        self.assertEqual(report["records_without_provisional_family"],23)
        self.assertEqual(sum(x["independently_verified_records"] for x in report["families"]),0)
        self.assertFalse(report["publication_approved"])
    def test_unmapped_provisional_family_is_flagged(self):
        taxonomy={"role_families":[{"name":str(i),"track":"T"} for i in range(22)]}
        report=assess({"records":[{"provisional_family":"other"}]},taxonomy)
        self.assertEqual(report["unmapped_provisional_families"],["other"])
if __name__=="__main__":
    unittest.main()
