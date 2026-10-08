import unittest

from tracker.business_product_delivery_security import classify_market_role, classify_raw, taxonomy


class MarketTaxonomyTest(unittest.TestCase):
    def test_exactly_22_unique_families(self):
        families = taxonomy()["role_families"]
        self.assertEqual(len(families), 22)
        self.assertEqual(len({f["name"] for f in families}), 22)
        self.assertEqual(sum(f["track"] == "SECURITY" for f in families), 7)

    def test_all_security_roles(self):
        expected = {
            "Information Security Analyst": "Information Security Analysis",
            "Cyber Security Analyst": "Information Security Analysis",
            "SOC Analyst": "Security Operations / SOC",
            "Security Architect": "Security Architecture",
            "Cyber Security Consultant": "Security Consulting & Advisory",
            "Security Risk Manager": "Security Risk & Third-Party Risk",
            "TPRM Analyst": "Security Risk & Third-Party Risk",
            "Third Party Risk Manager": "Security Risk & Third-Party Risk",
            "Information Security Manager": "Security Management",
            "IT Security Analyst": "IT Security",
            "IT Security Manager": "IT Security",
            "Security Advisor": "Security Consulting & Advisory",
        }
        for title, family in expected.items():
            with self.subTest(title=title):
                result = classify_market_role(title, "NIST, ISO 27001 and cyber security controls")
                self.assertTrue(result["included"])
                self.assertEqual(result["role_family"], family)

    def test_original_roles(self):
        titles = {
            "Senior Business Analyst": "Business Analysis",
            "Data Analyst": "Data Analysis",
            "Power BI Analyst": "Business Intelligence",
            "Senior Delivery Manager": "Delivery Management",
            "Product Owner": "Product Ownership",
            "Senior Product Manager": "Product Management",
            "Scrum Master": "Agile / Scrum",
            "Project Manager": "Project Management",
            "Business Change Manager": "Business Change & Transformation",
            "Programme Manager": "Programme & Portfolio Management",
            "Business Process Analyst": "Business Process & Operational Analysis",
            "Agile Coach": "Agile Leadership",
            "Head of Product": "Product Strategy & Operations",
            "Service Designer": "Service Management & Design",
            "Data Governance Manager": "Data & Analytics Management",
        }
        for title, expected in titles.items():
            with self.subTest(title=title):
                result = classify_market_role(title)
                self.assertTrue(result["included"])
                self.assertEqual(result["role_family"], expected)

    def test_exclusions(self):
        for title in ("Physical Security Manager", "Security Guard", "Door Supervisor",
                      "Network Engineer", "Data Scientist", "Cyber Security Sales Executive"):
            with self.subTest(title=title):
                self.assertFalse(classify_market_role(title, "some cyber security experience")["included"])

    def test_ambiguous_requires_security_context(self):
        self.assertFalse(classify_market_role("Security Architect")["included"])
        self.assertTrue(classify_market_role("Security Architect", "Cloud security, NIST and ISO 27001")["included"])
        self.assertFalse(classify_market_role("Security Advisor", "Retail premises safety")["included"])

    def test_title_not_description_only(self):
        self.assertFalse(classify_raw({"title": "Warehouse Operative", "description": "Uses Power BI and cyber security reporting"})["included"])

    def test_boundary(self):
        self.assertFalse(classify_market_role("Assistant Project Management Officer")["included"])
        self.assertFalse(classify_market_role("Assistant to the Product Manager")["included"])


if __name__ == "__main__":
    unittest.main()
