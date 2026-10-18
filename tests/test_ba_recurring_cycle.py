"""BA scheduled publication and spend safety (no external calls)."""
import json
import os
import unittest
from copy import deepcopy
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from unittest.mock import patch

from scripts.ba_controlled_refresh import CONFIG, validate as validate_config
from scripts.ba_recurring_cycle import scheduled_slot, build_live_document, main, SUMMER_CRON, WINTER_CRON

class TestBARecurringCycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads(CONFIG.read_text(encoding="utf8"))

    def test_approved_config_never_launches_from_manual_or_untrusted_event(self):
        meta=validate_config(self.cfg)
        self.assertTrue(meta["valid"])
        self.assertFalse(meta["enabled"])
        self.assertFalse(self.cfg["recurring_budget_approved"])
        self.assertFalse(self.cfg["pricing_guard_verified"])
        self.assertFalse(self.cfg["wordpress_delivery_enabled"])
        with patch.dict(os.environ,{"BA_PAID_REFRESH_APPROVAL":"EXPLICIT_BA_REFRESH_APPROVED","GITHUB_EVENT_NAME":"workflow_dispatch","GITHUB_RUN_ATTEMPT":"1"},clear=True), \
             patch("sys.argv",["ba_recurring_cycle","--execute","--scheduled"]):
            with self.assertRaises(SystemExit):
                main()

    def test_summer_and_winter_local_time(self):
        summer=datetime(2026,10,16,6,35,tzinfo=timezone.utc)  # Fri 07:35 BST
        winter=datetime(2026,11,6,7,35,tzinfo=timezone.utc)   # Fri 07:35 GMT
        self.assertTrue(scheduled_slot(summer)["due"])
        self.assertTrue(scheduled_slot(winter)["due"])
        self.assertFalse(scheduled_slot(datetime(2026,10,16,7,35,tzinfo=timezone.utc))["due"])
        self.assertFalse(scheduled_slot(datetime(2026,10,17,6,35,tzinfo=timezone.utc))["due"])

    def test_delayed_summer_runner_uses_only_the_correct_summer_cron(self):
        # Friday 16 Oct: 06:35 UTC = 07:35 BST. GitHub started 34m late.
        good=datetime(2026,10,16,7,9,11,tzinfo=timezone.utc)
        summer=scheduled_slot(good, cron=SUMMER_CRON)
        self.assertTrue(summer["due"],summer)
        self.assertEqual(summer["reason"],"APPROVED_LOCAL_0735_CRON")
        self.assertEqual(summer["month_slots"],5)
        self.assertEqual(summer["scheduled_uk"],"2026-10-16T07:35:00+01:00")
        self.assertGreater(summer["runner_delay_minutes"],34)
        # The second cron (07:35 UTC = 08:35 BST) ran at 08:09 UTC.
        # It must never buy the same dataset, regardless of its start delay.
        wrong=scheduled_slot(datetime(2026,10,16,8,9,11,tzinfo=timezone.utc),
                             cron=WINTER_CRON)
        self.assertFalse(wrong["due"],wrong)
        self.assertEqual(wrong["reason"],"WRONG_DST_CRON_OR_MISSING_TRIGGER")

    def test_delayed_winter_runner_uses_only_the_correct_winter_cron(self):
        good=scheduled_slot(datetime(2026,11,6,8,9,tzinfo=timezone.utc),
                            cron=WINTER_CRON)
        self.assertTrue(good["due"],good)
        self.assertEqual(good["scheduled_uk"],"2026-11-06T07:35:00+00:00")
        other=scheduled_slot(datetime(2026,11,6,7,20,tzinfo=timezone.utc),
                             cron=SUMMER_CRON)
        self.assertFalse(other["due"])

    def test_cron_guard_rejects_missing_early_very_late_and_other_weekday(self):
        for moment,cron in (
            (datetime(2026,10,16,7,9,tzinfo=timezone.utc),""),
            (datetime(2026,10,16,7,9,tzinfo=timezone.utc),"35 5 * * 2,5"),
            (datetime(2026,10,16,6,30,tzinfo=timezone.utc),SUMMER_CRON),
            (datetime(2026,10,16,9,6,tzinfo=timezone.utc),SUMMER_CRON),
            (datetime(2026,10,17,7,9,tzinfo=timezone.utc),SUMMER_CRON),
        ):
            with self.subTest(moment=moment,cron=cron):
                self.assertFalse(scheduled_slot(moment,cron=cron)["due"])

    def test_paid_schedule_env_required_before_pricing_or_actor_requests(self):
        # A GITHUB_EVENT_NAME of schedule without the trusted cron is NOT enough.
        with patch.dict(os.environ,{
                 "GITHUB_EVENT_NAME":"schedule","GITHUB_RUN_ATTEMPT":"1",
                 "BA_PAID_REFRESH_APPROVAL":"EXPLICIT_BA_REFRESH_APPROVED",
                 "BA_SCHEDULE_CRON":""},clear=True), \
             patch("sys.argv",["ba_recurring_cycle","--execute","--scheduled"]):
            with patch("scripts.ba_pricing_readonly.check", side_effect=AssertionError("No GET expected")):
                # Depending on current clock, missing cron always skips instead
                # of reaching Apify's pricing/Actor endpoints.
                with self.assertRaises(SystemExit): main()

    def test_monthly_slot_count_never_exceeds_nine(self):
        # At most nine Tue/Fri pairs can occur in a calendar month.
        from calendar import monthrange
        for year in (2026,2027):
            for month in range(1,13):
                slots=[day for day in range(1,monthrange(year,month)[1]+1)
                       if date(year,month,day).weekday() in (1,4)]
                self.assertLessEqual(len(slots),9)
                y,m,d=year,month,slots[-1]
                dt=datetime(y,m,d,7,35,tzinfo=ZoneInfo("Europe/London"))
                self.assertTrue(scheduled_slot(dt)["due"])
                self.assertLessEqual(scheduled_slot(dt)["month_slots"],9)

    def test_snapshot_adapts_current_run_provenance_not_historic(self):
        sources=["CV-Library","Totaljobs","Reed UK","Indeed UK","JobServe"]
        time="2026-10-15T15:52:00Z"
        rows=[{"id":"id"+str(i),"title":"Business Analyst",
               "role_family":"Business Analysis",
               "source":src,"source_run_id":"run"+str(i),
               "dataset_id":"dataset"+str(i),
               "url":"https://www.jobserve.com/gb/en/example"+str(i)}
              for i,src in enumerate(sources)]
        batch={"sources":[{"name":src,"status":"SUCCEEDED","attempted":True,
                          "run_id":"run"+str(i),"dataset_id":"dataset"+str(i),
                          "observed_at":time} for i,src in enumerate(sources)]}
        qa={"status":"DRY_RUN_PASS_NOT_PUBLISHED",
            "candidate":{"records":rows,"publication_approved":False},
            "rejected":{}}
        # WordPress preflight only relies on all five sources, provenance, and HTTPS URLs.
        now=datetime(2026,10,15,16,0,tzinfo=timezone.utc)
        result=build_live_document(batch,qa,now)
        self.assertEqual(result["schema"],"ba-live-snapshot/v1")
        self.assertEqual(len(result["records"]),5)
        self.assertEqual(len(result["sources"]),5)
        self.assertEqual(result["refresh"]["type"],"CONTROLLED_FIVE_SOURCE_REFRESH")
        self.assertFalse(result["quality"]["independently_confirmed_open"])
        self.assertEqual(result["records"][0]["job_source"],"CV-Library")
        wrong=deepcopy(qa)
        wrong["candidate"]["records"][0]["source_run_id"]="other-run"
        with self.assertRaisesRegex(ValueError,"provenance"):
            build_live_document(batch,wrong,now)

    def test_incomplete_source_blocks_publication(self):
        sources=["CV-Library","Totaljobs","Reed UK","Indeed UK"]
        bad={"sources":[{"name":x,"status":"SUCCEEDED","attempted":True,
                         "run_id":"r","dataset_id":"d","observed_at":"2026-10-15T15:00:00Z"}
                        for x in sources]}
        with self.assertRaises(ValueError):
            build_live_document(bad,{"status":"DRY_RUN_PASS_NOT_PUBLISHED","candidate":{"records":[]}},datetime(2026,10,15,16,tzinfo=timezone.utc))

if __name__=="__main__":
    unittest.main()
