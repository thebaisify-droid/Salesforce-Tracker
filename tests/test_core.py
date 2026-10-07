import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.daily_refresh import due_now, inspect_record_artifact, preflight, render_command
from collectors.common import _apify_named_ref, _filter_window
from tracker.classify import classify, versions
from tracker.normalize import normalize
from tracker.store import Store

ROOT = Path(__file__).resolve().parents[1]


class TrackerTests(unittest.TestCase):
    def test_versions_are_pinned(self):
        self.assertEqual(versions(), ("1.3", "2.2"))

    def test_source_artifact_validation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source.json"
            path.write_text(json.dumps([{"id": 1}, {"id": 2}]))
            self.assertEqual(inspect_record_artifact(path), (2, True, None))

    def test_render_command_quotes_paths(self):
        self.assertIn("'/tmp/a b.json'", render_command("tool --output {output}", {"output": "/tmp/a b.json"}))

    def test_london_dst_schedule_guard(self):
        due, _ = due_now(
            {"timezone": "Europe/London", "scheduled_local_time": "07:15"},
            datetime(2026, 10, 7, 6, 15, tzinfo=timezone.utc),
        )
        self.assertTrue(due)

    def test_agency_training_sector_classification(self):
        result = classify(
            "Salesforce Systems Trainer (Cyber Security Consultancy)",
            "Ernest Gordon Recruitment Limited",
            "Our client is a technology consultancy specialising in cybersecurity. Deliver Salesforce training across Sales Cloud and Experience Cloud.",
        )
        self.assertEqual(result["advertiser_type"], "RECRUITMENT_AGENCY")
        self.assertEqual(result["role_family"], "Training / Enablement")
        self.assertEqual(result["end_client_sector"], "Technology Services")
        self.assertEqual(result["sector_basis"], "END_CLIENT_DESCRIPTION_SECTOR")
        self.assertEqual(result["sector_review_required"], 1)
        self.assertIn("Sales Cloud", result["role_specialism"])
        self.assertIn("Experience Cloud", result["role_specialism"])

    def test_tracking_parameters_do_not_break_deduplication(self):
        a = normalize(
            {"id":"1","title":"Salesforce Business Analyst","company":"Example","url":"https://example.com/job/1?utm_source=x"},
            "s1",
        )
        b = normalize(
            {"id":"2","title":"Salesforce Business Analyst","company":"Example","url":"https://example.com/job/1?utm_medium=y"},
            "s2",
        )
        self.assertEqual(a["dedupe_key"], b["dedupe_key"])

    def test_apify_console_task_ref_converts_to_api_ref(self):
        self.assertEqual(
            _apify_named_ref("develop_ify/cv-library-scraper-task"),
            "develop_ify~cv-library-scraper-task",
        )
        self.assertEqual(
            _apify_named_ref("develop_ify~cv-library-scraper-task"),
            "develop_ify~cv-library-scraper-task",
        )

    def test_date_only_boundary_is_preserved(self):
        rows = [
            {"publishedAt": "2026-10-04", "id": "boundary"},
            {"publishedAt": "2026-10-03", "id": "old"},
        ]
        filtered = _filter_window(
            rows,
            "publishedAt",
            "2026-10-04T10:45:00Z",
            "2026-10-07T10:45:00Z",
        )
        self.assertEqual([row["id"] for row in filtered], ["boundary"])

    def test_adzuna_shape_normalizes(self):
        record = normalize(
            {
                "id": "adz-1",
                "title": "Salesforce Administrator",
                "company": {"display_name": "Example Ltd"},
                "location": {"display_name": "London"},
                "description": "Salesforce Service Cloud administration",
                "redirect_url": "https://example.com/jobs/adz-1",
                "created": "2026-10-07T08:00:00Z",
                "salary_min": 50000,
                "salary_max": 60000,
            },
            "source_2",
        )
        self.assertEqual(record["advertiser"], "Example Ltd")
        self.assertEqual(record["location"], "London")
        self.assertEqual(record["job_url"], "https://example.com/jobs/adz-1")
        self.assertEqual(record["posted_at"], "2026-10-07T08:00:00Z")

    def test_lightcast_shape_normalizes(self):
        record = normalize(
            {
                "id": "lc-1",
                "title_raw": "Salesforce Developer",
                "company_name": "Example Bank",
                "city_name": "Manchester",
                "body": "A banking role building Apex and Lightning Web Components.",
                "url": "https://example.com/jobs/lc-1",
                "posted": "2026-10-07T07:30:00Z",
                "employment_type_name": "Full-time",
            },
            "source_1",
        )
        self.assertEqual(record["display_title"], "Salesforce Developer")
        self.assertEqual(record["advertiser"], "Example Bank")
        self.assertEqual(record["location"], "Manchester")
        self.assertEqual(record["employment_type"], "Full-time")
        self.assertIn("Platform / Apex / LWC", record["role_specialism"])

    def test_apify_linkedin_shape_normalizes(self):
        record = normalize(
            {
                "id": "li-1",
                "title": "Senior Salesforce Functional Consultant",
                "companyName": "Example Consulting",
                "location": "Birmingham, United Kingdom",
                "description": "Sales Cloud and Service Cloud consulting.",
                "jobUrl": "https://www.linkedin.com/jobs/view/li-1",
                "publishedAt": "2026-10-07",
                "contractType": "Contract",
                "salaryMin": 550,
                "salaryMax": 650,
                "salaryCurrency": "GBP",
            },
            "source_3",
        )
        self.assertEqual(record["advertiser"], "Example Consulting")
        self.assertEqual(record["contract_type"], "Contract")
        self.assertEqual(record["salary_min"], 550.0)
        self.assertEqual(record["salary_currency"], "GBP")

    def test_store_insert_unchanged_update(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "tracker.db"
            base = {
                "id":"1",
                "title":"Salesforce Business Analyst",
                "company":"Bank Plc",
                "description":"Banking transformation using Sales Cloud",
                "url":"https://example.com/1",
            }
            with Store(db) as store:
                record = normalize(base, "s1")
                self.assertEqual(store.upsert(record), "inserted")
                self.assertEqual(store.upsert(record), "unchanged")
                changed = normalize({**base, "title":"Senior Salesforce Business Analyst"}, "s1")
                self.assertEqual(store.upsert(changed), "updated")

    def test_process_incremental_writes_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            raw = temp / "raw"
            raw.mkdir()
            (raw / "source_1.json").write_text(json.dumps([
                {"id":"1","title":"Salesforce Developer","company":"Acme","url":"https://example.com/1"},
                {"id":"2","title":"Salesforce Administrator","company":"Acme","url":"https://example.com/2"},
            ]))
            metrics = temp / "metrics.json"
            db = temp / "tracker.db"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.process_incremental",
                    "--input-dir", str(raw),
                    "--run-id", "test-run",
                    "--metrics", str(metrics),
                    "--database", str(db),
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(metrics.read_text())
            self.assertEqual(payload["inserted_rows"], 2)
            self.assertEqual(payload["master_data_version"], "1.3")
            self.assertEqual(payload["role_taxonomy_version"], "2.2")

    def test_project_preflight_blocks_unconfigured_sources(self):
        result = preflight(ROOT / "config" / "pipeline.json")
        self.assertFalse(result["ok"])
        self.assertEqual(sum("live provider is not configured" in error for error in result["errors"]), 3)


if __name__ == "__main__":
    unittest.main()
