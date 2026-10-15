import json
import unittest
from copy import deepcopy
from scripts.validate_ba_publication_candidate import PATH,validate
class TestBAPublicationCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(PATH.read_text(encoding="utf8"))
    def test_preflight(self):
        v=validate(self.data)
        self.assertTrue(v["staging_integrity_valid"],v["issues"])
        self.assertFalse(v["publication_authorized"])
        self.assertEqual(self.data["unique_display_clusters_provisional"],55)
        self.assertEqual(len(self.data["records"]),57)
    def test_unproven_billing_must_not_be_claimed(self):
        v=deepcopy(self.data)
        v["jobserve_charge_usd"]=0.5
        self.assertFalse(validate(v)["staging_integrity_valid"])
    def test_original_advert_links_retained(self):
        v=deepcopy(self.data)
        v["records"][0]["original_advert_url"]=""
        self.assertFalse(validate(v)["staging_integrity_valid"])
if __name__=="__main__":unittest.main()
