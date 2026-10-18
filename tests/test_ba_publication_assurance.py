"""Offline BA publication assurance tests; no WordPress/Apify traffic."""
from __future__ import annotations
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from scripts.ba_publication_assurance import validate_publication

NOW = datetime(2026, 10, 18, 11, 30, tzinfo=timezone.utc)
SOURCES = ("CV-Library", "Totaljobs", "Reed UK", "Indeed UK", "JobServe")


def snapshot():
    src = [{"source": name, "status": "SUCCEEDED", "attempted": True,
            "run_id": "run"+str(i), "dataset_id": "data"+str(i)}
           for i, name in enumerate(SOURCES)]
    rows = []
    for i, receipt in enumerate(src):
        url = "https://example.org/job/"+str(i)
        rows.append({"id": "id"+str(i), "title": "Business Analyst",
                     "role_family": "Business Analysis", "source": receipt["source"],
                     "job_source": receipt["source"],
                     "source_run_id": receipt["run_id"], "dataset_id": receipt["dataset_id"],
                     "url": url, "original_advert_url": url, "source_observed_only": True,
                     "observed_at": "2026-10-18T08:00:00Z",
                     "posted_date": "2026-10-17", "sector": "Not specified"})
    return {"schema": "ba-live-snapshot/v1",
            "refresh": {"status": "success",
                        "source_observed_not_employer_confirmed": True},
            "quality": {"passed": True, "independently_confirmed_open": False,
                        "matched_advertisements": len(rows)},
            "sources": src, "records": rows}


class BAPublicationAssuranceTests(unittest.TestCase):
    def test_valid_and_historical_post_without_discarding(self):
        x = snapshot()
        x["records"][0]["posted_date"] = "2023-05-23"
        x["records"][1]["posted_date"] = None
        result = validate_publication(x, NOW)
        self.assertEqual(result["records"], 5)
        self.assertEqual(result["historical_post_dates_over_90_days"], 1)
        self.assertEqual(result["missing_post_dates"], 1)
        self.assertEqual(result["sector_not_evidenced"], 5)
        self.assertEqual(result["wordpress_requests"], 0)
        self.assertEqual(result["actors_started"], 0)

    def test_fail_closed_for_malformed_critical_fields(self):
        cases = [
            ("id", None), ("url", "http://example.org/job"),
            ("source_run_id", "other"), ("dataset_id", "other"),
            ("source_observed_only", False), ("role_family", ""),
            ("observed_at", "2026-09-01T08:00:00Z"),
            ("observed_at", "2026-10-19T08:00:00Z"),
            ("observed_at", "yesterday"),
            ("posted_date", "2026-10-20"), ("posted_date", "2026-13-20"),
        ]
        for key, value in cases:
            with self.subTest(field=key, value=value):
                x = snapshot()
                x["records"][0][key] = value
                with self.assertRaises(ValueError):
                    validate_publication(x, NOW)

    def test_duplicate_identity_and_corrupt_qa_rejected(self):
        x = snapshot()
        x["records"][1]["source"] = x["records"][0]["source"]
        x["records"][1]["job_source"] = x["records"][0]["source"]
        x["records"][1]["source_run_id"] = x["records"][0]["source_run_id"]
        x["records"][1]["dataset_id"] = x["records"][0]["dataset_id"]
        x["records"][1]["url"] = x["records"][0]["url"]
        x["records"][1]["original_advert_url"] = x["records"][0]["url"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_publication(x, NOW)
        x = snapshot()
        x["sources"].pop()
        with self.assertRaisesRegex(ValueError, "five"):
            validate_publication(x, NOW)
        for field, value in [("passed", False), ("matched_advertisements", 4),
                             ("independently_confirmed_open", True)]:
            with self.subTest(field=field):
                x = snapshot()
                x["quality"][field] = value
                with self.assertRaises(ValueError):
                    validate_publication(x, NOW)

    def test_same_original_link_on_different_sources_is_not_automatically_collapsed(self):
        x = snapshot()
        x["records"][0]["url"] = x["records"][1]["url"]
        x["records"][0]["original_advert_url"] = x["records"][1]["url"]
        outcome = validate_publication(x, NOW)
        self.assertEqual(outcome["distinct_source_adverts"], 5)

if __name__ == "__main__":
    unittest.main()
