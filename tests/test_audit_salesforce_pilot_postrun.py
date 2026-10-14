import unittest
from scripts.audit_salesforce_pilot_postrun import normalize_url, inspect_sources, billing, DATASETS

class AuditSafetyTests(unittest.TestCase):
    def test_totaljobs_url_repair_only(self):
        self.assertEqual(
            normalize_url("https://www.totaljobs.com/https://www.totaljobs.com/job/salesforce-dev/x"),
            "https://www.totaljobs.com/job/salesforce-dev/x")
        self.assertIsNone(normalize_url("https://evil.example/job/1"))
        self.assertIsNone(normalize_url("https://www.totaljobs.com/https://evil.example/x"))

    def test_no_publication_and_dedup(self):
        datasets = {}
        for _, did, count in DATASETS:
            datasets[did] = [
                {"title":"Salesforce Developer","company":"Example Ltd",
                 "postedAt":"2026-10-14T10:00:00Z",
                 "url":"https://www.reed.co.uk/jobs/salesforce-developer/123"} for _ in range(count)
            ]
        report, rows = inspect_sources(datasets)
        self.assertEqual(report["raw_rows"],102)
        self.assertFalse(report["publication_allowed"])
        self.assertEqual(report["verified_open"],0)
        self.assertEqual(report["duplicate_excess_rows"],101)
        self.assertTrue(all(x["status"]=="DUPLICATE_REVIEW" for x in rows))

    def test_billing_is_not_invoiced_run_cost(self):
        data={"data":{"limits":{"maxMonthlyUsageUsd":19},
                      "current":{"monthlyUsageUsd":8.05}}}
        result=billing(data)
        self.assertEqual(result["headroom_after_reserve_usd"],2.95)
        self.assertFalse(result["per_run_invoiced_charges_verified"])
