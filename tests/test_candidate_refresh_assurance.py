import json
import unittest
from datetime import date
from pathlib import Path

from scripts.candidate_refresh_assurance import (
    assess_refresh_quality, posting_day, _possible_duplicate_key,
)


class CandidateRefreshAssuranceTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 14)

    def _job(self, title="Senior Business Analyst", source="JobServe",
             posted="2026-10-10", url="https://example.org/job/1",
             company="Alpha Recruitment Ltd", location="London"):
        return dict(title=title, source=source, posted_at=posted, url=url,
                    company=company, location=location)

    def test_freshness_cutoff_missing_and_future_are_not_fresh(self):
        records = [
            self._job(posted="2026-10-07", url="https://example.org/1"),
            self._job(posted="2026-10-06", url="https://example.org/2"),
            self._job(posted=None, url="https://example.org/3"),
            self._job(posted="2026-10-15", url="https://example.org/4"),
        ]
        report = assess_refresh_quality(records, as_of=self.today)
        self.assertEqual(report["classified_rows"], 4)
        self.assertEqual(report["classified_fresh"], 1)
        self.assertEqual(report["classified_stale"], 1)
        self.assertEqual(report["classified_missing_date"], 1)
        self.assertEqual(report["classified_future_date"], 1)
        self.assertFalse(report["publication_approved"])
        self.assertFalse(report["ready_for_publication"])

    def test_only_cross_source_same_title_employer_location_is_flagged(self):
        records = [
            self._job(url="https://one.example.org/job/1", source="JobServe"),
            self._job(url="https://two.example.org/jobs/2", source="Indeed UK",
                      title="SENIOR BUSINESS ANALYST", company="Alpha-Recruitment Ltd",
                      location="London"),
            self._job(url="https://three.example.org/jobs/3", source="Indeed UK",
                      company="Different Employer", location="London"),
            self._job(url="https://four.example.org/jobs/4", source="Reed",
                      company=None, location="London"),
        ]
        report = assess_refresh_quality(records, as_of=self.today)
        self.assertEqual(report["possible_title_employer_location_cross_source_groups"], 1)
        self.assertEqual(report["exact_url_cross_source_groups"], 0)
        self.assertIn("possible_cross_source_duplicates_require_review",
                      report["release_blockers"])
        self.assertFalse(report["auto_apply_expiry_events"])

    def test_same_url_cross_board_flagged_without_auto_deleting(self):
        records = [self._job(source="JobServe"),
                   self._job(source="Reed")]
        report = assess_refresh_quality(records, as_of=self.today)
        self.assertEqual(report["classified_rows"], 2)
        self.assertEqual(report["exact_url_repeated_rows"], 1)
        self.assertEqual(report["exact_url_cross_source_groups"], 1)

    def test_wrong_source_and_excluded_titles_never_misrepresent_fresh(self):
        records = [self._job(source="Unknown"),
                   self._job(title="Security Guard", url="https://example.org/2"),
                   self._job(title="SOC Analyst", source="JobServe",
                             posted="2026-10-10", url="http://example.org/3")]
        report = assess_refresh_quality(records, as_of=self.today)
        self.assertEqual(report["classified_rows"], 0)
        self.assertEqual(report["invalid_or_unknown_source_rows"], 2)

    def test_date_parser_supports_existing_apify_shapes(self):
        self.assertEqual(posting_day("Thursday, 8 October 2026"), date(2026, 10, 8))
        self.assertEqual(posting_day("2026-10-10T06:41:01.176Z"), date(2026, 10, 10))
        self.assertIsNone(posting_day("not a date"))

    def test_fail_closed_even_when_all_jobs_are_recent(self):
        report = assess_refresh_quality([self._job()], as_of=self.today)
        self.assertEqual(report["classified_fresh"], 1)
        self.assertFalse(report["publication_approved"])
        self.assertFalse(report["acquisition_enabled"])
        self.assertIn("independent_live_vacancy_verification_missing",
                      report["release_blockers"])

    def test_inert_search_profiles_cover_exactly_22_families(self):
        config = json.loads(Path("config/candidate_refresh_search_profiles.example.json").read_text())
        self.assertFalse(config["enabled"])
        self.assertFalse(config["paid_acquisition_enabled"])
        self.assertFalse(config["publication_enabled"])
        self.assertEqual(config["actor_runs_allowed"], 0)
        self.assertEqual(config["approved_spend_usd"], 0)
        self.assertEqual(len(config["role_search_examples"]), 22)
        self.assertEqual(len({f["family"] for f in config["role_search_examples"]}), 22)
        self.assertEqual(sum(f["track"] == "SECURITY" for f in config["role_search_examples"]), 7)
        self.assertTrue(all(not source["actor_input_validated"] for source in config["sources"]))
