"""Offline regression checks for two employer-backed target-family research leads."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from tracker.business_product_delivery_security import classify_market_role, taxonomy

PATH = Path("docs/evidence/candidate_employer_backed_security_gaps_2026-10-09.json")

class EmployerBackedSecurityGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))
        cls.leads = cls.data["leads"]

    def test_exact_source_refs_unique_and_no_publication(self):
        self.assertEqual(len(self.leads), 2)
        self.assertEqual(len({x["lead_id"] for x in self.leads}), 2)
        self.assertEqual(len({(x["employer_name"],x["employer_reference"])
                              for x in self.leads}), 2)
        self.assertFalse(self.data["publication_approved"])
        self.assertFalse(self.data["verified_representative_coverage"])
        self.assertEqual(self.data["paid_apify_runs_started"], 0)
        self.assertEqual(self.data["new_apify_spend_authorised_usd"], 0)
        for row in self.leads:
            self.assertFalse(row["publication_ready"])
            self.assertFalse(row["human_role_label_approved"])
            self.assertFalse(row["vacancy_live_independently_confirmed"])
            self.assertFalse(row["application_flow_independently_tested"])
            self.assertTrue(row["proposed_family_requires_human_review"])

    def test_domains_and_provenance_not_overstated(self):
        expected = {"sony-pictures-JR114830":
                    ("www.sonypicturesjobs.com","EMPLOYER_CAREERS_PAGE"),
                    "maritime-coastguard-482482":
                    ("www.jobsgopublic.com","PUBLIC_SECTOR_SYNDICATED_ADVERT")}
        for row in self.leads:
            parsed = urlsplit(row["evidence_url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual((parsed.hostname,row["source_type"]),
                             expected[row["lead_id"]])
            self.assertFalse(parsed.username or parsed.password)

    def test_source_titles_match_two_target_families_but_still_require_review(self):
        families = {f["name"] for f in taxonomy()["role_families"]}
        for row in self.leads:
            with self.subTest(id=row["lead_id"]):
                self.assertIn(row["proposed_family"], families)
                decision = classify_market_role(row["original_title"],
                                                row["source_claim_context"])
                self.assertTrue(decision["included"])
                self.assertEqual(decision["track"], "SECURITY")
                self.assertEqual(decision["role_family"], row["proposed_family"])
                self.assertTrue(decision["review_required"])

    def test_generic_vendor_risk_is_not_assumed_to_be_cyber(self):
        for title in ("Third Party Risk Analyst", "Third-Party Risk Manager",
                      "Risk Analyst (Third Party Risk)"):
            with self.subTest(title=title):
                r = classify_market_role(title, "Procurement, financial vendor credit risk and contract spend")
                self.assertFalse(r["included"])
                self.assertEqual(r["reason"], "ambiguous_security_context")
                self.assertTrue(r["review_required"])
        r = classify_market_role("Third Party Risk Analyst",
                                "Information security supplier control assessment against ISO 27001")
        self.assertTrue(r["included"])
        self.assertEqual(r["role_family"],"Security Risk & Third-Party Risk")
        self.assertTrue(r["review_required"])

    def test_off_scope_titles_cannot_enter_security_family(self):
        for title in ("Risk Analyst", "Quantitative Risk Analyst",
                      "Business Analyst, Defence & Security",
                      "Police Officer", "Senior Workday Analyst"):
            with self.subTest(title=title):
                r=classify_market_role(title,"Generic business transformation and accounting")
                self.assertFalse(r.get("included") and r.get("track")=="SECURITY")

if __name__ == "__main__":
    unittest.main()
