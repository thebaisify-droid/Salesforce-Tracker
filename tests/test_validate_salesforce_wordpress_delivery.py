import json
import unittest
from datetime import datetime, timezone
from scripts.validate_salesforce_wordpress_delivery import inspect


class DeliveryPreflightTests(unittest.TestCase):
    now = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)

    def payload(self):
        return {"schema": "salesforce-hiring-dashboard/v1",
                "pipeline": {"quality_passed": True},
                "vacancies": [{"title": "Salesforce Developer"}],
                "active_vacancies": 1,
                "refresh": {"status": "success",
                            "finished_at": "2026-10-14T11:00:00Z"}}

    def check(self, data):
        return inspect(json.dumps(data).encode(), now=self.now)

    def test_valid_but_never_approves_publication(self):
        report = self.check(self.payload())
        self.assertTrue(report["locally_validated"])
        self.assertFalse(report["wordpress_delivery_authorised"])
        self.assertFalse(report["publication_performed"])
        self.assertEqual(report["apify_actors_started"], 0)

    def test_stale_is_rejected(self):
        p = self.payload()
        p["refresh"]["finished_at"] = "2026-10-10T06:41:39Z"
        with self.assertRaises(ValueError):
            self.check(p)

    def test_bad_quality_and_counts_are_rejected(self):
        p = self.payload()
        p["pipeline"]["quality_passed"] = False
        with self.assertRaises(ValueError):
            self.check(p)
        p = self.payload()
        p["active_vacancies"] = 2
        with self.assertRaises(ValueError):
            self.check(p)

    def test_failed_refresh_is_rejected(self):
        p = self.payload()
        p["refresh"]["status"] = "failed"
        with self.assertRaises(ValueError):
            self.check(p)

    def test_missing_timezone_rejected(self):
        p = self.payload()
        p["refresh"]["finished_at"] = "2026-10-14T11:00:00"
        with self.assertRaises(ValueError):
            self.check(p)
