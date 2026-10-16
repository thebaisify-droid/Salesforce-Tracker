"""Narrow, auditable UK market title aliases and training-ad safeguards."""
from __future__ import annotations
import unittest
from scripts.ba_stage_five_source_data import promotional_training_lead
from tracker.business_product_delivery_security import classify_market_role

class MarketRelevanceRegression(unittest.TestCase):
    def test_bi_developers_managers_and_hybrid_roles_are_not_lost(self):
        titles=[
            "Business Intelligence Developer - SQL, ETL, Power BI, DAX",
            "Business Intelligence Manager",
            "Business Intelligence Developer (Tableau/T-SQL)",
            "Business Intelligence/Commercial Modelling Analyst",
            "BI & Data Analyst",
            "Power BI Developer",
            "Senior BI Developer",
        ]
        for title in titles:
            with self.subTest(title=title):
                x=classify_market_role(title,"Power BI, reporting, SQL, analytics")
                self.assertTrue(x["included"],x)
                self.assertEqual(x["role_family"],"Business Intelligence",x)

    def test_real_cyber_abbreviation_in_totaljobs_source(self):
        x=classify_market_role("Cyber Sec Analyst - Network Intrusion & Capability Development",
                               "Defensive cyber operations and network security")
        self.assertTrue(x["included"])
        self.assertEqual(x["role_family"],"Information Security Analysis")

    def test_security_consultant_requires_independent_cyber_context(self):
        weak=classify_market_role("Security Consultant","General customer service")
        self.assertFalse(weak["included"])
        self.assertTrue(weak["review_required"])
        good=classify_market_role("Senior Technical Security Consultant",
                                  "Cloud security, NIST and penetration testing")
        self.assertTrue(good["included"])
        self.assertEqual(good["role_family"],"Security Consulting & Advisory")

    def test_training_placement_schemes_are_not_employer_vacancies(self):
        self.assertTrue(promotional_training_lead(
            "Junior Ethical Hacker Placement Programme - no experience needed",
            "Self-funded training programme leading to a guaranteed job placement"))
        self.assertTrue(promotional_training_lead(
            "Trainee Cyber Security Analyst - No Experience Needed",
            "A training provider offers a paid career programme, then placements"))
        self.assertTrue(promotional_training_lead(
            "Analyst Training Course", "Self-funded upskilling programme"))
        self.assertFalse(promotional_training_lead(
            "Junior Data Analyst","Graduate position with on-the-job training"))
        self.assertFalse(promotional_training_lead(
            "Cyber Security Analyst", "Paid full-time role, mentoring provided"))
        self.assertFalse(promotional_training_lead(
            "Information Security Analyst - Entry Level",
            "Open to candidates with no experience; full-time salaried role"))

if __name__=="__main__":
    unittest.main()
