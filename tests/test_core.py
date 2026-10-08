import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from collectors.common import _apify_named_ref, _filter_window
from pipeline.daily_refresh import due_now, inspect_record_artifact, preflight, render_command
from tracker.classify import classify, versions
from tracker.dashboard import merge_with_baseline
from tracker.normalize import normalize
from tracker.relevance import salesforce_relevance
from tracker.store import Store
from scripts.state_snapshot import build_manifest, safe_extract, verify_manifest
from scripts.restore_github_state import select_latest_artifact
from scripts.migrate_baseline import migrate

ROOT = Path(__file__).resolve().parents[1]


class TrackerTests(unittest.TestCase):
    def test_versions_are_pinned(self):
        self.assertEqual(versions(), ("1.4", "2.2"))

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

    def test_apify_console_task_ref_converts_to_api_ref(self):
        self.assertEqual(_apify_named_ref("develop_ify/cv-library-scraper-task"), "develop_ify~cv-library-scraper-task")
        self.assertEqual(_apify_named_ref("develop_ify~cv-library-scraper-task"), "develop_ify~cv-library-scraper-task")

    def test_date_only_boundary_is_preserved(self):
        rows = [{"datePosted": "2026-10-04", "id": "boundary"}, {"datePosted": "2026-10-03", "id": "old"}]
        filtered = _filter_window(rows, "datePosted", "2026-10-04T10:45:00Z", "2026-10-07T10:45:00Z")
        self.assertEqual([row["id"] for row in filtered], ["boundary"])

    def test_known_agency_and_sector_word_boundaries(self):
        morson = classify(
            "Salesforce Developer",
            "Morson Edge",
            "Salesforce Financial Services Cloud role in banking.",
        )
        self.assertEqual(morson["advertiser_type"], "RECRUITMENT_AGENCY")
        self.assertEqual(morson["sector_basis"], "END_CLIENT_DESCRIPTION_SECTOR")
        proactive = classify(
            "Salesforce Technical Architect",
            "Proactive Appointments",
            "Proactive Appointments Limited operates as an employment agency and employment business. Ongoing platform transformation.",
        )
        self.assertEqual(proactive["advertiser_type"], "RECRUITMENT_AGENCY")
        self.assertIsNone(proactive["end_client_sector"])

    def test_salesforce_relevance_accepts_platform_role(self):
        relevant, _ = salesforce_relevance({
            "title": "IT Business Analyst",
            "description": "Experience of Salesforce Sales Cloud and Financial Services Cloud is required.",
        })
        self.assertTrue(relevant)

    def test_salesforce_relevance_rejects_generic_sales_roles(self):
        samples = [
            {"title":"Head of Sales","description":"Own pipeline health and progression through Salesforce CRM."},
            {"title":"Field Sales Executive","description":"Use Salesforce CRM for prospecting and customer records. Salesforce experience preferred."},
            {"title":"Sales, Finance & Marketing Administrator","description":"Update customer records in Salesforce and other internal systems. Salesforce experience helpful."},
            {"title":"IT Program Manager","description":"Programme includes CRM applications such as Salesforce CRM and other enterprise tools."},
            {"title":"Senior Director Enterprise AI & Automation","company":"Worldpay Group Plc","description":"Desirable familiarity with Salesforce, Agentforce, copilots, AI agents, machine learning and enterprise SaaS platforms."},
        ]
        for sample in samples:
            relevant, reason = salesforce_relevance(sample)
            self.assertFalse(relevant, (sample["title"], reason))

    def test_salesforce_relevance_accepts_direct_salesforce_employer(self):
        relevant, reason = salesforce_relevance({
            "title":"Engagement Delivery Director",
            "company":"Salesforce",
            "description":"Customer Success leadership role.",
        })
        self.assertTrue(relevant)
        self.assertEqual(reason, "salesforce_direct_employer")

    def test_salesforce_relevance_rejects_incidental_crm_mention(self):
        relevant, _ = salesforce_relevance({
            "title": "Sales Account Manager",
            "description": "Experience with CRM platforms such as Salesforce, HubSpot or Zoho would be beneficial.",
        })
        self.assertFalse(relevant)

    def test_cv_library_shape_normalizes(self):
        record = normalize({
            "jobId": "cv-1",
            "title": "Salesforce Business Analyst",
            "company": "Example Recruitment",
            "location": "London",
            "descriptionText": "Salesforce Sales Cloud business analysis.",
            "canonicalUrl": "https://www.cv-library.co.uk/job/123/",
            "postedAt": "2026-10-07T08:00:00Z",
            "salaryMin": 550,
            "salaryMax": 650,
            "salaryCurrency": "GBP",
            "salaryPeriod": "day",
            "contractType": "Contract",
        }, "source_1")
        self.assertEqual(record["job_url"], "https://www.cv-library.co.uk/job/123")
        self.assertEqual(record["posted_at"], "2026-10-07T08:00:00Z")
        self.assertEqual(record["salary_period"], "day")

    def test_totaljobs_shape_normalizes(self):
        record = normalize({
            "jobId": 108085473,
            "title": "Salesforce Developer (Financial Services)",
            "employer": {"name": "Morson Edge"},
            "location": {"text": "Tower Hill, City of London (EC3)"},
            "descriptionText": "Salesforce development using Apex and Lightning.",
            "jobUrl": "https://www.totaljobs.com/job/example",
            "datePosted": "2026-10-06T10:19:25.333Z",
            "salary": {"rawText": "£600 - 700 per day + 12 months", "min": 12, "max": 700, "currency": "GBP", "period": "day"},
            "employmentType": ["CONTRACTOR"],
        }, "source_2")
        self.assertEqual(record["advertiser"], "Morson Edge")
        self.assertEqual(record["location"], "Tower Hill, City of London (EC3)")
        self.assertEqual(record["posted_at"], "2026-10-06T10:19:25.333Z")
        self.assertEqual(record["salary_min"], 600.0)
        self.assertEqual(record["salary_max"], 700.0)
        self.assertEqual(record["salary_period"], "day")
        self.assertEqual(record["employment_type"], "CONTRACTOR")

    def test_indeed_uk_shape_normalizes(self):
        record = normalize({
            "jobId": "abc123",
            "title": "Salesforce Administrator",
            "company": "Example Ltd",
            "location": "Manchester",
            "jobTypes": ["Full-time", "Permanent"],
            "salaryMin": 50000,
            "salaryMax": 60000,
            "salaryCurrency": "GBP",
            "salaryPeriod": "year",
            "postedAt": "2026-10-08T00:00:00.000Z",
            "snippet": "Administer Sales Cloud and Salesforce Flow.",
            "url": "https://uk.indeed.com/viewjob?jk=abc123"
        }, "source_4")
        self.assertEqual(record["external_id"], "abc123")
        self.assertEqual(record["employment_type"], "Full-time, Permanent")
        self.assertEqual(record["posted_at"], "2026-10-08T00:00:00.000Z")
        self.assertEqual(record["salary_min"], 50000.0)
        self.assertEqual(record["salary_period"], "year")

    def test_jobserve_shape_normalizes(self):
        record = normalize({
            "id": "JS-123",
            "title": "Salesforce Technical Architect",
            "company_name": "Example Recruitment",
            "location": "London",
            "job_type": "Contract",
            "salary_min": 650,
            "salary_max": 750,
            "salary_currency": "GBP",
            "salary_period": "day",
            "posted_at": "2026-10-08T00:00:00Z",
            "description_full": "Salesforce architecture across Service Cloud and Experience Cloud.",
            "job_url": "https://www.jobserve.com/gb/en/JobLanding.aspx?jid=JS-123"
        }, "source_5")
        self.assertEqual(record["external_id"], "JS-123")
        self.assertEqual(record["advertiser"], "Example Recruitment")
        self.assertEqual(record["contract_type"], "Contract")
        self.assertEqual(record["salary_min"], 650.0)
        self.assertEqual(record["posted_at"], "2026-10-08T00:00:00Z")

    def test_reed_shape_normalizes(self):
        record = normalize({
            "jobId": 57407294,
            "title": "Salesforce Developer",
            "employer": "Foresters Financial",
            "location": "BR29BF",
            "description": "Salesforce development role.",
            "url": "https://www.reed.co.uk/jobs/salesforce-developer/57407294",
            "datePosted": "2026-09-30T00:00:00.000Z",
            "salaryFrom": 60000,
            "salaryTo": 60000,
            "salaryCurrency": "GBP",
            "salaryPeriod": "Annual",
            "jobType": "Permanent",
            "isFullTime": True,
        }, "source_3")
        self.assertEqual(record["advertiser"], "Foresters Financial")
        self.assertEqual(record["posted_at"], "2026-09-30T00:00:00.000Z")
        self.assertEqual(record["contract_type"], "Permanent")
        self.assertEqual(record["employment_type"], "Full-time")
        self.assertEqual(record["salary_period"], "Annual")

    def test_tracking_parameters_do_not_break_deduplication(self):
        a = normalize({"id":"1","title":"Salesforce Business Analyst","company":"Example","url":"https://example.com/job/1?utm_source=x"}, "s1")
        b = normalize({"id":"2","title":"Salesforce Business Analyst","company":"Example","url":"https://example.com/job/1?utm_medium=y"}, "s2")
        self.assertEqual(a["dedupe_key"], b["dedupe_key"])

    def test_dashboard_normalizes_live_taxonomy_for_continuity(self):
        baseline = json.loads((ROOT / "config" / "baseline_2026-10-06.json").read_text())
        live = {
            "vacancies": [
                {
                    "id": 200,
                    "title": "Engagement Delivery Director",
                    "advertiser": "Salesforce",
                    "advertiser_type": "DIRECT_EMPLOYER",
                    "role_family": "Programme / Project Delivery",
                    "seniority": "Lead",
                    "specialisms": [],
                    "end_client_name": None,
                    "sector": "Education & Nonprofit",
                    "location": "London",
                    "employment_type": "FULL_TIME",
                    "contract_type": None,
                    "salary": {"min": None, "max": None, "currency": "GBP", "period": None},
                    "url": "https://example.com/new-salesforce-delivery",
                    "posted_at": "2026-10-07T20:00:00Z",
                    "first_seen_at": "2026-10-08T04:00:00Z",
                    "last_seen_at": "2026-10-08T04:00:00Z",
                    "review": {"role": False, "sector": True},
                    "sources": [{"key":"source_2","label":"Totaljobs","url":"https://example.com/new-salesforce-delivery"}],
                }
            ]
        }
        merged = merge_with_baseline(live, baseline)
        new = next(v for v in merged["vacancies"] if v.get("url") == "https://example.com/new-salesforce-delivery")
        self.assertEqual(new["role_family"], "Delivery / Programme")
        self.assertEqual(new["sector"], "Technology Services")
        self.assertFalse(new["review"]["sector"])
        labels = {row["label"] for row in merged["by_role_family"]}
        self.assertNotIn("Programme / Project Delivery", labels)

    def test_dashboard_baseline_restores_45_without_duplicate_live_rows(self):
        baseline = json.loads((ROOT / "config" / "baseline_2026-10-06.json").read_text())
        self.assertEqual(len(baseline["rows"]), 45)
        live = {
            "vacancies": [
                {
                    "id": 101,
                    "title": "Salesforce Developer (Financial Services)",
                    "advertiser": "Morson Edge",
                    "advertiser_type": "RECRUITMENT_AGENCY",
                    "role_family": "Engineering / Development",
                    "seniority": "Standard",
                    "specialisms": ["Platform / Apex / LWC"],
                    "end_client_name": None,
                    "sector": "Financial Services",
                    "location": "Tower Hill, City of London (EC3), E1W 1WY",
                    "employment_type": "CONTRACTOR",
                    "contract_type": "Contract",
                    "salary": {"min": 600, "max": 700, "currency": "GBP", "period": "day"},
                    "url": "https://www.totaljobs.com/job/salesforce-developer-financial-services/morson-edge-job108085473",
                    "posted_at": "2026-10-06T10:19:25.333Z",
                    "first_seen_at": "2026-10-07T11:31:45Z",
                    "last_seen_at": "2026-10-07T11:31:45Z",
                    "review": {"role": False, "sector": True},
                    "sources": [{"key": "source_2", "label": "Totaljobs", "url": "https://www.totaljobs.com/job/salesforce-developer-financial-services/morson-edge-job108085473"}],
                }
            ]
        }
        merged = merge_with_baseline(live, baseline)
        self.assertEqual(merged["active_vacancies"], 45)
        relevance = {row["label"]: row["value"] for row in merged["by_relevance"]}
        self.assertEqual(relevance["CORE"], 29)
        self.assertEqual(relevance["ADJACENT"], 16)
        self.assertEqual(merged["baseline"]["post_baseline_new"], 0)

    def test_dashboard_snapshot_is_public_safe(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "tracker.db"
            raw = {
                "jobId": "108085473",
                "title": "Salesforce Developer (Financial Services)",
                "employer": {"name": "Morson Edge"},
                "location": {"text": "London"},
                "descriptionText": "Salesforce development using Apex. Contact recruiter@example.com.",
                "jobUrl": "https://www.totaljobs.com/job/example",
                "datePosted": "2026-10-06T10:19:25.333Z",
                "salary": {"rawText": "£600 - 700 per day", "currency": "GBP", "period": "day"},
            }
            with Store(db) as store:
                store.begin_run("dashboard-test", "1.4", "2.2")
                store.upsert(normalize(raw, "source_2"))
                store.finish_run("dashboard-test", "success", {"inserted_rows": 1})
                snapshot = store.dashboard_snapshot()
            self.assertEqual(snapshot["active_vacancies"], 1)
            self.assertEqual(snapshot["by_source"][0]["label"], "Totaljobs")
            vacancy = snapshot["vacancies"][0]
            self.assertEqual(vacancy["title"], "Salesforce Developer (Financial Services)")
            self.assertEqual(vacancy["sources"][0]["label"], "Totaljobs")
            self.assertEqual(vacancy["salary"]["period"], "day")
            self.assertNotIn("description", vacancy)
            self.assertNotIn("raw_json", vacancy)

    def test_store_cross_board_deduplicates_identical_job_content(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "tracker.db"
            desc = "Our client is bringing Salesforce in house from a third party consultancy. " * 20
            a = normalize({
                "id":"cv-1","title":"Salesforce Developer","company":"Michael Page",
                "description":desc,"url":"https://www.cv-library.co.uk/job/111"
            }, "source_1")
            b = normalize({
                "id":"reed-1","title":"Salesforce Developer","company":"Michael Page Technology",
                "description":desc,"url":"https://www.reed.co.uk/jobs/salesforce-developer/222"
            }, "source_3")
            with Store(db) as store:
                self.assertEqual(store.upsert(a), "inserted")
                self.assertEqual(store.upsert(b), "unchanged")
                count = store.conn.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
                links = store.conn.execute("SELECT COUNT(*) FROM vacancy_sources").fetchone()[0]
            self.assertEqual(count, 1)
            self.assertEqual(links, 2)

    def test_store_insert_unchanged_update(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "tracker.db"
            base = {"id":"1","title":"Salesforce Business Analyst","company":"Bank Plc","description":"Banking transformation using Sales Cloud","url":"https://example.com/1"}
            with Store(db) as store:
                record = normalize(base, "s1")
                self.assertEqual(store.upsert(record), "inserted")
                self.assertEqual(store.upsert(record), "unchanged")
                changed = normalize({**base, "title":"Senior Salesforce Business Analyst"}, "s1")
                self.assertEqual(store.upsert(changed), "updated")

    def test_process_incremental_filters_irrelevant_rows(self):
        with tempfile.TemporaryDirectory() as d:
            temp = Path(d)
            raw = temp / "raw"
            raw.mkdir()
            (raw / "source_1.json").write_text(json.dumps([
                {"id":"1","title":"Salesforce Developer","company":"Acme","url":"https://example.com/1"},
                {"id":"2","title":"Sales Account Manager","company":"Acme","description":"Salesforce is one of several CRMs we use.","url":"https://example.com/2"},
            ]))
            metrics = temp / "metrics.json"
            db = temp / "tracker.db"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(ROOT)
            proc = subprocess.run(
                [sys.executable, "-m", "scripts.process_incremental", "--input-dir", str(raw), "--run-id", "test-run", "--metrics", str(metrics), "--database", str(db)],
                cwd=ROOT, env=env, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(metrics.read_text())
            self.assertEqual(payload["inserted_rows"], 1)
            self.assertEqual(payload["irrelevant_rows"], 1)
            self.assertEqual(payload["master_data_version"], "1.4")
            self.assertEqual(payload["role_taxonomy_version"], "2.2")

    def test_baseline_migration_inserts_45_then_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "tracker.db"
            baseline = ROOT / "config" / "baseline_2026-10-06.json"
            first = migrate(db, baseline)
            self.assertTrue(first["passed"], first)
            self.assertEqual(first["database_after"], 45)
            self.assertEqual(first["inserted_missing_baseline"], 45)
            second = migrate(db, baseline)
            self.assertTrue(second["passed"], second)
            self.assertEqual(second["database_after"], 45)
            self.assertEqual(second["inserted_missing_baseline"], 0)
            self.assertEqual(second["matched_existing"], 45)

    def test_state_manifest_verifies_sqlite_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            db = root / "data" / "salesforce_tracker.db"
            with Store(db):
                pass
            (root / "state").mkdir(parents=True, exist_ok=True)
            (root / "state" / "latest_success.json").write_text(json.dumps({"status": "success"}))
            manifest = build_manifest(root, "data/salesforce_tracker.db")
            manifest_path = root / "state" / "state_manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            result = verify_manifest(root, manifest_path)
            self.assertTrue(result["verified"])
            self.assertEqual(result["database"]["integrity_check"], "ok")

    def test_restore_selects_latest_main_branch_artifact(self):
        payload = {
            "artifacts": [
                {"id": 1, "name": "tracker-state", "expired": False, "created_at": "2026-10-01T00:00:00Z", "workflow_run": {"head_branch": "main"}},
                {"id": 2, "name": "tracker-state", "expired": False, "created_at": "2026-10-02T00:00:00Z", "workflow_run": {"head_branch": "feature"}},
                {"id": 3, "name": "tracker-state", "expired": False, "created_at": "2026-10-03T00:00:00Z", "workflow_run": {"head_branch": "main"}},
                {"id": 4, "name": "tracker-state", "expired": True, "created_at": "2026-10-04T00:00:00Z", "workflow_run": {"head_branch": "main"}},
            ]
        }
        artifact = select_latest_artifact(payload, "tracker-state", "main")
        self.assertEqual(artifact["id"], 3)

    def test_state_snapshot_rejects_path_traversal(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "bad")
            with self.assertRaises(RuntimeError):
                safe_extract(archive, root / "restore")

    def test_project_preflight_accepts_validated_sources(self):
        result = preflight(ROOT / "config" / "pipeline.json")
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["enabled_sources"], 5)
        self.assertEqual(result["min_sources_succeeded"], 3)


if __name__ == "__main__":
    unittest.main()
