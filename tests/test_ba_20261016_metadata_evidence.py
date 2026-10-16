"""No-cost sector and work-mode evidence tests for drafted BA metadata expansion."""
from __future__ import annotations
import json
import unittest

from scripts.ba_stage_five_source_data import working,sector_catalog,MAPPING
from scripts.ba_20261016_124_scope_preflight import candidate

class BAProposedMetadataEvidenceTests(unittest.TestCase):
    def test_only_explicit_working_language_is_applied(self):
        self.assertEqual(working({"description":"London (Hybrid) 3 days in the office"}),"Hybrid")
        self.assertEqual(working({"description":"Remote working throughout the UK"}),"Remote")
        self.assertEqual(working({"description":"Fully on-site, weekdays"}),"On-site")
        self.assertEqual(working({"description":"Architect hybrid cloud networking"}),"Not specified")
        self.assertEqual(working({"description":"2 days a week onsite; other arrangements unknown"}),"Not specified")
        self.assertEqual(working({"description":"Led a hybrid-cloud migration, no working pattern provided"}),"Not specified")
        self.assertEqual(working({"description":"Hybrid, three days in office","remote":True}),"Remote")
        self.assertEqual(working({}),"Not specified")

    def test_official_advertiser_mapping_never_infers_recruiters_clients(self):
        d=json.loads(MAPPING.read_text(encoding="utf8"))
        index=sector_catalog(d)
        self.assertGreaterEqual(len(index),18)
        for name,sector in (
            ("department for transport","Public Sector"),
            ("bristol city council","Public Sector"),
            ("warwick district council","Public Sector"),
            ("oxford health nhs foundation trust","Healthcare & Life Sciences"),
            ("cisco","Technology Services"),
            ("siemens","Manufacturing & Engineering"),
            ("capital one uk","Financial Services"),
            ("deutsche bank","Financial Services"),
            ("janus henderson","Financial Services"),
            ("bdo uk","Professional Services"),
            ("evri","Transport & Logistics"),
        ):
            with self.subTest(name=name):
                self.assertEqual(index[name]["sector"],sector)
                self.assertTrue(index[name]["evidence_url"].startswith("https://"))
        for recruiter in ("hays specialist recruitment","lorien","michael page technology"):
            self.assertNotIn(recruiter,index)

    def test_reviewed_124_has_evidence_without_changing_record_scope(self):
        report=candidate()
        self.assertEqual(report["combined_in_scope"],124)
        self.assertEqual(report["remaining_not_kept"],37)
        self.assertGreaterEqual(report["working_known"],30)
        self.assertGreaterEqual(report["sector_evidenced"],13)
        self.assertFalse(report["publication_approved"])
        self.assertEqual(report["actor_runs_started"],0)
        self.assertEqual(report["wordpress_requests"],0)
        print("STAGED_BA_METADATA "+json.dumps({
            "sector_evidenced":report["sector_evidenced"],
            "working_known":report["working_known"],
            "scope_total":report["combined_in_scope"],
            "actor_runs_started":0,
            "wordpress_requests":0},sort_keys=True))

if __name__=="__main__":
    unittest.main()
