"""Final 161-record user adjudication: 124 exact keeps and 37 exact exclusions.

Offline-only assertions. User scope is not employer-opening verification.
No Apify operations, no WordPress delivery and no new charges.
"""
import json
import unittest
from collections import Counter

from scripts.ba_20261016_124_scope_preflight import candidate
from scripts.ba_stage_five_source_data import (
    FINAL_SCOPE_DECISIONS, user_excluded_adverts, link, stage, MAPPING,
    promotional_training_lead,
)
from scripts.ba_quality_audit_20261016 import EVIDENCE
from tracker.business_product_delivery_security import classify_market_role


class Final161ScopeDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger=json.loads(FINAL_SCOPE_DECISIONS.read_text(encoding="utf8"))
        cls.evidence=json.loads(EVIDENCE.read_text(encoding="utf8"))
        cls.excluded=user_excluded_adverts()
        cls.report,cls.snapshot=candidate(return_snapshot=True)

    def test_exact_161_decisions_and_reviewer_39_keep(self):
        rows=self.ledger["decisions"]
        self.assertEqual(len(rows),161)
        self.assertEqual(Counter(r["decision"] for r in rows),
                         {"KEEP":124,"EXCLUDE":37})
        self.assertEqual(len(self.excluded),37)
        self.assertFalse(self.ledger["no_employer_opening_verification"] is False)
        self.assertTrue(self.ledger["rejection_is_advert_url_specific"])
        self.assertEqual(self.ledger["existing_approved_39_count"],39)
        self.assertEqual(len({(r["source"],r["original_advert_url"]) for r in rows}),161)
        self.assertEqual(self.report["combined_in_scope"],124)
        self.assertEqual(self.report["newly_in_scope"],37)
        self.assertEqual(self.report["remaining_not_kept"],37)

    def test_exact_whitelist_and_blacklist_reconcile_to_five_source_data(self):
        from_source=set()
        for source in self.evidence["sources"]:
            for raw in source["records"]:
                normalized=link(raw,source["name"])
                self.assertIsNotNone(normalized)
                from_source.add((source["name"],normalized))
        approved={(r["job_source"],r["original_advert_url"])
                  for r in self.snapshot["records"]}
        all_ledger={(r["source"],r["original_advert_url"])
                    for r in self.ledger["decisions"]}
        keep={(r["source"],r["original_advert_url"])
              for r in self.ledger["decisions"] if r["decision"]=="KEEP"}
        self.assertEqual(from_source,all_ledger)
        self.assertEqual(keep,approved)
        self.assertFalse(keep & self.excluded)
        self.assertEqual(from_source-keep,self.excluded)

    def test_stage_must_never_reaccept_the_explicit_37(self):
        mapping=json.loads(MAPPING.read_text(encoding="utf8"))
        result=stage({"schema":"ba-five-source-completed-batch/v1",
                      "sources":self.evidence["sources"]},mapping)
        self.assertEqual(result["total_matching_advertisements"],87)
        self.assertEqual(result["rejected"]["user_explicitly_excluded_advert"],37)
        self.assertTrue(all((r["job_source"],r["original_advert_url"])
                            not in self.excluded for r in result["records"]))
        self.assertEqual(self.report["actor_runs_started"],0)
        self.assertEqual(self.report["wordpress_requests"],0)

    def test_does_not_exclude_whole_titles_or_role_families(self):
        self.assertNotIn(("Reed UK","https://www.reed.co.uk/jobs/business-analyst/new-safe-advert"),
                         self.excluded)
        self.assertTrue(classify_market_role("Business Analyst")["included"])
        self.assertFalse(promotional_training_lead(
            "Junior Data Analyst","Genuine full-time paid role; mentoring provided"))

if __name__=="__main__":
    unittest.main()
